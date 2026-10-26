"""Persistent token admission and cancellation. No network or model calls.

Reservations are conservative allowances, not provider-enforced token caps.
Reported usage can arrive after a turn has already exceeded its allowance.
"""
from contextlib import closing, contextmanager
from copy import deepcopy
import os
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .core import ROOT, Blocked, json_read, stable
from .money import dollars, estimate, micros, price_for, validate_price, validate_cost_receipt

POLICY_PATH = ROOT / 'execution/agent-budgets.json'
POOLS = ('codex', 'openrouter')


def validate(policy):
    if isinstance(policy, dict) and type(policy.get('schema')) is int and policy['schema'] == 2:
        if (set(policy) != {'schema', 'unit', 'pools', 'prices'} or policy['unit'] != 'usd'
                or not isinstance(policy['pools'], dict) or set(policy['pools']) != set(POOLS)
                or not isinstance(policy['prices'], dict)):
            raise Blocked('Invalid USD budget policy')
        for settings in policy['pools'].values():
            if not isinstance(settings, dict) or set(settings) != {'limit_usd', 'invocation_allowance_usd'}:
                raise Blocked('Explicit USD limit and invocation allowance required')
            limit, allowance = micros(settings['limit_usd']), micros(settings['invocation_allowance_usd'])
            if allowance <= 0 or (limit > 0 and allowance > limit): raise Blocked('Invalid USD allowance')
        for key, price in policy['prices'].items():
            if not any(key.startswith(pool + ':') and len(key) > len(pool) + 1 for pool in POOLS):
                raise Blocked('Price must identify an approved pool and exact model')
            validate_price(price)
        return policy
    if (not isinstance(policy, dict) or set(policy) != {'schema', 'unit', 'pools'}
            or type(policy['schema']) is not int or policy['schema'] != 1
            or policy['unit'] != 'input_plus_output_tokens'
            or not isinstance(policy['pools'], dict) or set(policy['pools']) != set(POOLS)):
        raise Blocked('Invalid budget policy; explicit Codex and OpenRouter token pools required')
    for settings in policy['pools'].values():
        if (not isinstance(settings, dict)
                or set(settings) != {'limit_tokens', 'invocation_allowance_tokens'}
                or any(type(v) is not int or not 0 <= v <= 2**53 for v in settings.values())
                or settings['invocation_allowance_tokens'] == 0
                or (settings['limit_tokens'] > 0
                    and settings['invocation_allowance_tokens'] > settings['limit_tokens'])):
            raise Blocked('Invalid token limit or invocation allowance')
    return policy


def load():
    return validate(json_read(POLICY_PATH))


def pool_for(selection):
    provider = selection['provider_config']
    if provider['kind'] == 'builtin' and provider.get('provider_id') == 'openai':
        return 'codex'
    if provider['kind'] == 'responses' and provider.get('base_url') == 'https://openrouter.ai/api/v1':
        return 'openrouter'
    raise Blocked('Provider has no approved budget pool; arbitrary routers need explicit accounting support')


def accounting_rows(db):
    rows=[dict(row) for row in db.execute('SELECT * FROM calls')]
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='adjustments'").fetchone():
        for row in rows:
            actual=db.execute('SELECT amount,correction FROM adjustments WHERE session=? ORDER BY sequence DESC LIMIT 1',(row['session'],)).fetchone()
            if actual:
                row['reconciled_spent']=actual['amount']
                row['verified_provider_spent']=actual['amount'] if json.loads(actual['correction'])['basis']=='verified_provider_receipt' else None
    return rows


def summarize(policy, rows, stop):
    pools = {}
    for name, settings in policy['pools'].items():
        own = [r for r in rows if r['pool'] == name]
        observed = sum(r['tokens'] for r in own)
        spent = sum(r['spent'] if policy['unit'] == 'usd' else r['tokens'] for r in own)
        effective=lambda r:r.get('reconciled_spent',r['spent']) if policy['unit']=='usd' else r['tokens']
        charged = sum(max(effective(r),r['spent'],r['allowance']) if r['state'] in
                      ('RESERVED', 'RUNNING', 'UNKNOWN') else effective(r) for r in own)
        limit, _ = limits(policy, name)
        amounts = ({'observed_estimated_usd': dollars(spent), 'charged_estimated_usd': dollars(sum(max(r['spent'],r['allowance']) if r['state'] in ('RESERVED','RUNNING','UNKNOWN') else r['spent'] for r in own)),
                    'charged_exposure_usd':dollars(charged),'accounted_usd':dollars(sum(effective(r) for r in own)),
                    'available_usd': dollars(max(0, limit - charged)),
                    'provider_reported_cost_usd':dollars(sum(r['verified_provider_spent'] for r in own)) if own and all(r.get('verified_provider_spent') is not None for r in own) else None}
                   if policy['unit'] == 'usd' else {'charged_tokens': charged, 'available_tokens': max(0, limit - charged)})
        pools[name] = {**settings, 'observed_tokens': observed, **amounts,
                      'unsettled_calls': sum(r['state'] in ('RESERVED', 'RUNNING', 'UNKNOWN') for r in own)}
    return {'unit': policy['unit'], 'stop_reason': stop, 'pools': pools,
            'scope': 'Project lifetime; retries and preset changes do not reset consumption',
            'billing': 'Configured estimates, separately approved verified/reconciled costs and admission exposure; not subscription quota or independent invoice verification' if policy['unit'] == 'usd' else 'Observed tokens, not currency or remaining account quota'}


def limits(policy, pool):
    settings = policy['pools'][pool]
    if policy['unit'] == 'usd': return micros(settings['limit_usd']), micros(settings['invocation_allowance_usd'])
    return settings['limit_tokens'], settings['invocation_allowance_tokens']


def check_unit(db, policy):
    has_meta = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='accounting'").fetchone()
    saved = db.execute('SELECT unit FROM accounting').fetchone()[0] if has_meta else 'input_plus_output_tokens'
    if saved != policy['unit'] and db.execute('SELECT 1 FROM calls LIMIT 1').fetchone():
        raise Blocked('Historical budget unit differs; explicit reconciliation/migration required, never reset spending')


def snapshot(path, policy):
    """Read-only CLI status; does not create a database or require credentials."""
    if not Path(path).exists():
        return {'status': 'NOT_STARTED', **summarize(policy, [], None)}
    from .history import verify_budget_adjustments
    verify_budget_adjustments(path)
    with closing(sqlite3.connect(Path(path).absolute().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN')
        check_unit(db, policy)
        rows = accounting_rows(db)
        stop = db.execute("SELECT reason FROM stops WHERE id=1").fetchone()
        return {'status': 'STOPPED' if stop else 'RECORDED',
                **summarize(policy, rows, stop[0] if stop else None)}


class Budgets:
    def __init__(self, path, policy, policy_path=None, *, approval_verifier=None):
        self.path, self.policy = Path(path), deepcopy(validate(policy))
        # Trusted integration dependency only; never selected by correction data.
        self.approval_verifier=approval_verifier
        self.policy_path, self.owner = policy_path, uuid.uuid4().hex
        from .history import verify_budget_adjustments
        if self.path.exists():verify_budget_adjustments(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Fail closed if accounting was removed while invocation evidence survives.
        if not self.path.exists() and (self.path.parent / 'usage.jsonl').exists():
            raise Blocked('Usage ledger exists without budget accounting; reconcile before execution')
        self.path.touch(mode=0o600, exist_ok=True)
        os.chmod(self.path, 0o600)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS calls (session TEXT PRIMARY KEY, pool TEXT NOT NULL, '
                       'task TEXT NOT NULL, role TEXT NOT NULL, kind TEXT NOT NULL, owner TEXT NOT NULL, '
                       'allowance INTEGER NOT NULL, tokens INTEGER NOT NULL, state TEXT NOT NULL, updated REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS stops (id INTEGER PRIMARY KEY CHECK(id=1), reason TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS adjustments (sequence INTEGER PRIMARY KEY AUTOINCREMENT, '
                       'receipt_id TEXT NOT NULL UNIQUE,session TEXT NOT NULL,amount INTEGER NOT NULL, '
                       'correction_sha256 TEXT NOT NULL,correction TEXT NOT NULL,approval TEXT NOT NULL, '
                       'decision_id TEXT NOT NULL UNIQUE,created REAL NOT NULL)')
            for operation in ('UPDATE','DELETE'):
                db.execute("CREATE TRIGGER IF NOT EXISTS adjustments_no_"+operation.lower()+" BEFORE "+operation+
                           " ON adjustments BEGIN SELECT RAISE(ABORT,'Accounting adjustments are append-only'); END")

            check_unit(db, self.policy)
            columns = {row[1] for row in db.execute('PRAGMA table_info(calls)')}
            for name, declaration in (('spent', 'INTEGER NOT NULL DEFAULT 0'), ('price', "TEXT NOT NULL DEFAULT '{}'")):
                if name not in columns: db.execute('ALTER TABLE calls ADD COLUMN ' + name + ' ' + declaration)
            if self.policy['unit'] == 'input_plus_output_tokens': db.execute('UPDATE calls SET spent=tokens')
            db.execute('CREATE TABLE IF NOT EXISTS accounting (unit TEXT NOT NULL)')
            if not db.execute('SELECT 1 FROM calls LIMIT 1').fetchone(): db.execute('DELETE FROM accounting')
            if not db.execute('SELECT 1 FROM accounting').fetchone(): db.execute('INSERT INTO accounting VALUES (?)', (self.policy['unit'],))
            if db.execute("SELECT 1 FROM calls WHERE state IN ('RESERVED','RUNNING','UNKNOWN') LIMIT 1").fetchone():
                self.stop(db, 'Unsettled prior invocation; explicit accounting reconciliation required')
            amount = 'spent' if self.policy['unit'] == 'usd' else 'tokens'
            for row in db.execute('SELECT pool,SUM(' + amount + ') AS spent FROM calls GROUP BY pool'):
                if row['spent'] > 0 and row['spent'] >= limits(self.policy, row['pool'])[0]:
                    self.stop(db, row['pool'] + ' historical consumption reaches configured limit')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def stop(db, reason):
        db.execute('INSERT OR IGNORE INTO stops VALUES (1,?)', (reason,))

    def check_stop(self):
        from .history import verify_budget_adjustments
        verify_budget_adjustments(self.path)
        if self.policy_path is not None and stable(validate(json_read(self.policy_path))) != stable(self.policy):
            with self.transaction() as db:
                self.stop(db, 'Budget policy changed during execution; stop and requalify')
        with self.transaction() as db:
            row = db.execute('SELECT reason FROM stops WHERE id=1').fetchone()
            if row:
                raise Blocked('Budget stopped: ' + row[0])

    def guard(self, selections=()):
        """Check before features/stages; actual calls acquire atomic reservations."""
        self.check_stop()
        state = snapshot(self.path, self.policy)
        for pool in {pool_for(s) for s in selections}:
            settings = state['pools'][pool]
            available = micros(settings['available_usd']) if self.policy['unit'] == 'usd' else settings['available_tokens']
            if available < limits(self.policy, pool)[1]:
                raise Blocked('Insufficient ' + pool + ' budget for a model invocation')
        if self.policy['unit'] == 'usd':
            for selection in selections: price_for(self.policy, pool_for(selection), selection['model'])

    @contextmanager
    def finalization(self):
        """Linearize DONE publication against committed stop writers, never hold over Git."""
        self.check_stop()
        with self.transaction() as db:
            from .history import verify_budget_adjustments
            verify_budget_adjustments(self.path)
            row = db.execute('SELECT reason FROM stops WHERE id=1').fetchone()
            if row:
                raise Blocked('Budget stopped before finalization: ' + row[0])
            yield

    def reserve(self, session, selection, task, role, kind):
        self.check_stop()
        if selection.get('required_bounds'):
            raise Blocked('Requested per-call bound unsupported by the unqualified adapter; allowance is not a hard cap')
        pool = pool_for(selection)
        price = price_for(self.policy, pool, selection['model']) if self.policy['unit'] == 'usd' else {}
        with self.transaction() as db:
            from .history import verify_budget_adjustments
            verify_budget_adjustments(self.path)
            if db.execute('SELECT 1 FROM stops').fetchone():
                raise Blocked('Budget stopped before reservation')
            rows = accounting_rows(db)
            settings = summarize(self.policy, rows, None)['pools'][pool]
            allowance = limits(self.policy, pool)[1]
            available = micros(settings['available_usd']) if self.policy['unit'] == 'usd' else settings['available_tokens']
            if available < allowance:
                raise Blocked('Insufficient ' + pool + ' budget; no model process started')
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                       (session, pool, task, role, kind, self.owner, allowance, 0, 'RESERVED', time.time(), 0, json.dumps(price)))
        return {'pool': pool, 'unit': self.policy['unit'], 'price_snapshot': price,
                **({'reservation_usd': dollars(allowance)} if price else {'reservation_tokens': allowance}),
                'policy_sha256': stable(self.policy)}

    def observe(self, session, metrics, final=False, not_started=False):
        """Persist each terminal-turn observation, even when it exceeds the reservation."""
        with self.transaction() as db:
            row = db.execute('SELECT * FROM calls WHERE session=?', (session,)).fetchone()
            if row is None or row['owner'] != self.owner or row['state'] in ('SETTLED', 'NOT_STARTED'):
                raise Blocked('Missing, foreign or settled budget reservation')
            tokens = metrics['known_input_tokens'] + metrics['known_output_tokens']
            spent = estimate(metrics, json.loads(row['price'])) if self.policy['unit'] == 'usd' else tokens
            complete = metrics['status'] == 'COMPLETE'
            if not_started:
                tokens, spent, state = 0, 0, 'NOT_STARTED'
            else:
                tokens = max(row['tokens'], tokens)
                spent = max(row['spent'], spent)
                state = ('SETTLED' if final else 'RUNNING') if complete else 'UNKNOWN'
                if not complete:
                    self.stop(db, 'Incomplete model usage; reservation retained for reconciliation')
                if spent >= row['allowance']:
                    self.stop(db, 'Invocation budget allowance reached: ' + session)
            db.execute('UPDATE calls SET tokens=?,spent=?,state=?,updated=? WHERE session=?',
                       (tokens, spent, state, time.time(), session))
            observed = db.execute('SELECT SUM(spent) FROM calls WHERE pool=?', (row['pool'],)).fetchone()[0]
            if observed >= limits(self.policy, row['pool'])[0] and not not_started:
                self.stop(db, row['pool'] + ' budget limit reached')
        return self.receipt(session)

    def reconcile_cost(self, correction, *, approval=None):
        """Internal fail-closed seam; no CLI/real approval authority is supplied here.

        The trusted host installs the verifier, independently of untrusted receipt
        data. Approved cost corrections never resolve unknown tokens or clear stop.
        """
        correction=deepcopy(validate_cost_receipt(correction))
        if self.policy['unit']!='usd' or not callable(self.approval_verifier):
            raise Blocked('Trusted USD accounting approval verifier required')
        from .history import History,verify_budget_adjustments
        verify_budget_adjustments(self.path)
        history=History(self.path.parent/'trace.sqlite')
        digest=stable(correction)
        verified=self.approval_verifier(deepcopy(approval),deepcopy(correction))
        if (not isinstance(verified,dict) or set(verified)!={'actor','decision_id','correction_sha256'}
                or any(not isinstance(value,str) or not value.strip() for value in verified.values())
                or verified['correction_sha256']!=digest):
            raise Blocked('Approval must bind exact correction digest and attributable decision')
        with self.transaction() as db:
            verify_budget_adjustments(self.path)
            row=db.execute('SELECT * FROM calls WHERE session=?',(correction['session'],)).fetchone()
            if row is None or row['pool']!=correction['pool'] or row['state']=='NOT_STARTED':
                raise Blocked('Correction session/pool has no potentially started invocation')
            prior=db.execute('SELECT * FROM adjustments WHERE receipt_id=?',(correction['receipt_id'],)).fetchone()
            if prior:
                if prior['correction_sha256']!=digest or json.loads(prior['approval'])!=verified:
                    raise Blocked('Conflicting receipt or approval reuse')
            else:
                if db.execute('SELECT 1 FROM adjustments WHERE decision_id=?',(verified['decision_id'],)).fetchone():
                    raise Blocked('Approval decision replayed for another correction')
                amount=micros(correction['amount_usd'])
                created=time.time()
                sequence=db.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM adjustments').fetchone()[0]
                projection={'sequence':sequence,'receipt_id':correction['receipt_id'],'session':correction['session'],'amount':amount,
                    'correction_sha256':digest,'correction':correction,'approval':verified,'decision_id':verified['decision_id'],'created':created}
                reference='model-preflight/accounting-'+digest+'.json'
                import hashlib
                artifact_hash=hashlib.sha256((json.dumps(projection,indent=2)+'\n').encode()).hexdigest()
                payload={'receipt_id':correction['receipt_id'],'budget_database':self.path.name,'correction_sha256':digest,
                    'artifact':reference,'artifact_sha256':artifact_hash,'projection_sha256':stable(projection)}
                context={'trace':'accounting:'+digest,'task':row['task'],'session':row['session'],'role':row['role']}
                intent=history.append('accounting.correction.intent',**context,payload=payload)
                history.write_artifact(reference,projection,trace=context['trace'],task=row['task'])
                db.execute('INSERT INTO adjustments(sequence,receipt_id,session,amount,correction_sha256,correction,approval,decision_id,created) VALUES (?,?,?,?,?,?,?,?,?)',
                    (sequence,correction['receipt_id'],correction['session'],amount,digest,json.dumps(correction,sort_keys=True),json.dumps(verified,sort_keys=True),verified['decision_id'],created))
                if amount>=row['allowance']:
                    self.stop(db,'Corrected invocation budget allowance reached: '+row['session'])
                state=summarize(self.policy,accounting_rows(db),None)['pools'][row['pool']]
                if micros(state['charged_exposure_usd'])>=limits(self.policy,row['pool'])[0]:
                    self.stop(db,row['pool']+' reconciled exposure reaches configured limit')
        if not prior:history.append('accounting.correction.completed',**context,payload={**payload,'intent_event_id':intent['event_id']})
        return self.receipt(correction['session'])

    def receipt(self, session):
        with self.transaction() as db:
            row = db.execute('SELECT * FROM calls WHERE session=?', (session,)).fetchone()
            stop = db.execute('SELECT reason FROM stops WHERE id=1').fetchone()
            adjustments=[]
            for item in db.execute('SELECT * FROM adjustments WHERE session=? ORDER BY sequence',(session,)):
                entry=dict(item);entry['correction']=json.loads(entry['correction']);entry['approval']=json.loads(entry['approval']);adjustments.append(entry)
            latest=adjustments[-1] if adjustments else None
            return {'reservation': dict(row) if row else None, 'stop_reason': stop[0] if stop else None,
                    'unit': self.policy['unit'], 'estimated_cost_usd': dollars(row['spent']) if row and self.policy['unit'] == 'usd' else None,
                    'provider_reported_cost_usd': dollars(latest['amount']) if latest and latest['correction']['basis']=='verified_provider_receipt' else None,
                    'reconciled_cost_usd':dollars(latest['amount']) if latest else None,'adjustments':adjustments,
                    'policy_sha256': stable(self.policy)}
