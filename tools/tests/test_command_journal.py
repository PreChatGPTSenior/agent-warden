"""Causal commands, using disposable offline state and fake providers only."""
import ast
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from execution import core, processes

class CommandJournalTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.env={'PATH':os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'}
        self.policy=core._command_policy
        policy=patch('execution.core._command_policy');policy.start();self.addCleanup(policy.stop)
    def scope(self):
        return core.command_scope(self.root/'.execution/commands',actor='coordinator',task='T0010-009',parent_action='fixture-batch',candidate='fixture-candidate')
    def rows(self):
        return [json.loads(p.read_text()) for p in sorted((self.root/'.execution/commands').glob('*.json'))]
    def test_command_routes_through_executor(self):
        with (self.scope() if hasattr(core,'command_scope') else contextlib.nullcontext()), patch('execution.processes.start',wraps=processes.start) as start:
            self.assertEqual('fixture\n',core.command([sys.executable,'-c','print("fixture")'],cwd=self.root,env=self.env))
            self.assertEqual(1,start.call_count)
    def test_setup_check_git_cleanup_are_journaled(self):
        import orchestrate
        import static_analysis
        from execution.environment import stop
        from execution.gates import monitored
        real_start=processes.start
        observed=[]
        def fake_start(argv,**kwargs):
            observed.append(argv)
            fixture=[sys.executable,'-c','print("fixture action")']
            kwargs['admission']=processes.admit_command(fixture,kwargs['cwd'],policy_id='offline-reviewed-fixture')
            return real_start(fixture,**kwargs)
        (self.root/'stone-shelter-ui').mkdir()
        # The cleanup client uses the owned stack identity and approved compose file.
        (self.root/'infra').mkdir();(self.root/'infra/compose.yaml').write_text('services: {}')
        stack={'project':'fixture-owned','env_file':str(self.root/'fixture.env'),'worktree':str(self.root)}
        with self.scope(),patch('execution.processes.start',side_effect=fake_start):
            orchestrate.prepare_dependencies(self.root,self.env)
            run=self.root/'monitor-run';run.mkdir()
            with patch('execution.gates.probe',return_value=[]):
                log=monitored(['python3','fixture-check.py'],self.root,dict(self.env,STONE_TEST_CANDIDATE='fixture-candidate',STONE_TEST_RUN_ID=run.name),{},
                    {'id':'T0010-009','environment':[]},run,'selected-check',timeout=5)
                self.assertEqual('fixture action\n',log.read_text())
            result=static_analysis.execute(['node','--version'],self.root,self.env)
            self.assertEqual(0,result.returncode)
            core.command(['git','merge','--ff-only','fixture'],cwd=self.root,env=self.env)
            stop(stack)
        self.assertEqual(['npm','npm','python3','node','git','docker'],[argv[0] for argv in observed])
        self.assertEqual(6,len(self.rows()))
        for row in self.rows():
            self.assertEqual(('coordinator','T0010-009','fixture-batch','fixture-candidate'),tuple(row[k] for k in ('actor','task','parent_action','candidate')))
            self.assertEqual(['intent','started','outcome'],[event['event'] for event in row['events']])
    def test_started_without_outcome_is_not_success(self):
        journal=processes.CommandJournal(self.root/'.execution/commands')
        journal.write('fixture',{'action_id':'fixture','side_effect':True,'events':[{'event':'intent'},{'event':'started'}]})
        with self.assertRaisesRegex(core.Blocked,'reconciliation'):
            with self.scope():core.command([sys.executable,'-c','print("never")'],cwd=self.root,env=self.env)
    def test_interrupted_git_requires_reconciliation(self):
        with self.scope():
            for argv in (['git','init','-b','main'],['git','config','user.name','Fixture'],
                         ['git','config','user.email','fixture@example.invalid']):
                core.command(argv,cwd=self.root,env=self.env)
            (self.root/'feature.txt').write_text('before')
            core.command(['git','add','feature.txt'],cwd=self.root,env=self.env)
            core.command(['git','commit','-m','fixture seed'],cwd=self.root,env=self.env)
            import maintenance
            self.assertEqual(40,len(maintenance._head(self.root)))
            self.assertTrue(list((self.root/'.cache/maintenance-planning/.execution/commands').glob('*.json')))
            tree=self.root/'other'
            core.command(['git','worktree','add','-b','candidate',str(tree),'HEAD'],cwd=self.root,env=self.env)
            (tree/'feature.txt').write_text('after')
            core.command(['git','add','feature.txt'],cwd=tree,env=self.env)
            core.command(['git','commit','-m','fixture change'],cwd=tree,env=self.env)
            original=processes.CommandJournal.write
            def interrupt(journal,action,record):
                if record['argv'][:2]==['git','merge'] and record['events'][-1]['event']=='outcome':
                    raise KeyboardInterrupt('fixture crash after Git effect')
                return original(journal,action,record)
            with patch.object(processes.CommandJournal,'write',interrupt),self.assertRaises(KeyboardInterrupt):
                core.command(['git','merge','--ff-only','candidate'],cwd=self.root,env=self.env)
            self.assertEqual('after',(self.root/'feature.txt').read_text())
            with patch('execution.processes.start') as start:
                with self.assertRaisesRegex(core.Blocked,'reconciliation'):
                    core.command(['git','merge','--ff-only','candidate'],cwd=self.root,env=self.env)
                start.assert_not_called()
        from execution.history import require_recovered
        with self.assertRaises(core.Blocked):require_recovered(self.root/'.execution')
    def test_model_lifecycle_uses_one_supervisor(self):
        import execution.agent_runtime as runtime
        from execution.history import History
        from execution.budgets import Budgets
        from execution.model_policy import load,resolve
        History(self.root/'.execution/trace.sqlite')
        selection=resolve(load([t['id'] for t in core.tasks()]),'gpt','T0002-002','developer')
        budget=Budgets(self.root/'.execution/budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens',
            'pools':{name:{'limit_tokens':1000,'invocation_allowance_tokens':100} for name in ('codex','openrouter')}})
        original=processes.launch
        def provider(argv,**kwargs):
            output=argv[argv.index('--output-last-message')+1]
            code=('import json,pathlib,sys; sys.stdin.read(); '
                  'pathlib.Path(sys.argv[1]).write_text(json.dumps({"status":"APPROVED","summary":"fake provider","findings":[],"evidence":[]})); '
                  'print(json.dumps({"type":"turn.started"}),flush=True); '
                  'print(json.dumps({"type":"turn.completed","usage":{"input_tokens":7,"output_tokens":3}}),flush=True)')
            return original([sys.executable,'-c',code,output],**kwargs)
        with patch.object(runtime,'ROOT',self.root),patch('execution.processes.launch',side_effect=provider) as launch:
            result,receipt,_,_=runtime.invoke(selection,'T0002-002','developer',self.root,self.root/'.execution/runs/fixture/developer',
                'fixture prompt',5,env=self.env,budget=budget,trace_context={'attempt_id':'fixture','candidate':'fixture-candidate'})
        self.assertEqual('APPROVED',result['status']);self.assertEqual(1,launch.call_count)
        usage=[json.loads(line) for line in (self.root/'.execution/usage.jsonl').read_text().splitlines()]
        self.assertEqual(1,len(usage));self.assertEqual(10,usage[0]['usage']['total_tokens'])
        self.assertEqual(1,len(self.rows()));self.assertEqual('EXITED',self.rows()[0]['events'][-1]['outcome']['status'])
        self.assertTrue(self.rows()[0]['output_artifacts'])
    def test_sanitized_causal_metadata(self):
        secret='fixture-private-password'
        with self.scope():
            self.assertEqual('[REDACTED]\n',core.command([sys.executable,'-c','print("'+secret+'")'],cwd=self.root,env=dict(self.env,API_TOKEN=secret)))
        contents=''.join(p.read_text() for p in (self.root/'.execution/commands').glob('*.json'))
        self.assertNotIn(secret,contents);self.assertIn('[REDACTED]',contents)
    def test_no_direct_subprocess_in_admitted_sites(self):
        for name in ('execution/core.py','execution/gates.py','execution/environment.py','execution/agent_runtime.py','orchestrate.py','static_analysis.py','sonar_application.py'):
            tree=ast.parse((core.ROOT/'tools'/name).read_text())
            offenders=[n.lineno for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess' and n.func.attr in ('run','Popen','call','check_call','check_output')]
            self.assertEqual([],offenders,name)
        for argv in (['python3',str(core.ROOT/'tools/runtime_gate.py')],['npm','run','check:runtime'],['docker','rm','unowned'],['sh','-c','echo detached']):
            with self.assertRaises(core.Blocked):self.policy(argv,self.root,'coordinator-tools')
        self.policy(['git','rev-parse','HEAD'],self.root,'coordinator-tools')
    def test_successful_action_has_correlated_outcome(self):
        with self.scope():core.command([sys.executable,'-c','print("outcome")'],cwd=self.root,env=self.env)
        row=self.rows()[0];result=row['events'][-1]
        self.assertEqual('EXITED',result['outcome']['status']);self.assertEqual(0,result['outcome']['returncode'])
        self.assertTrue(all(e['action_id']==row['action_id'] for e in row['events']))
        self.assertEqual('outcome\n',result['outcome']['stdout'])
        with self.assertRaisesRegex(core.Blocked,'scope'):
            core.command([sys.executable,'-c','print("unadmitted")'],cwd=self.root,env=self.env)

    def test_command_history_tampering_blocks_restart(self):
        from execution.history import require_recovered
        with self.scope():core.command([sys.executable,'-c','print("anchor")'],cwd=self.root,env=self.env)
        self.assertEqual('NO_UNRESOLVED_EXECUTION',require_recovered(self.root/'.execution')['status'])
        action=next((self.root/'.execution/commands').glob('*.json'))
        value=json.loads(action.read_text());value['candidate']='forged';action.write_text(json.dumps(value))
        with self.assertRaises(core.Blocked):require_recovered(self.root/'.execution')
    def test_command_namespace_is_safe(self):
        from execution.history import History
        with self.scope():core.command([sys.executable,'-c','print("safe")'],cwd=self.root,env=self.env)
        history=History(self.root/'.execution/trace.sqlite')
        with self.assertRaises(core.Blocked):history.write_artifact('commands/../escape.json',{})
        foreign=self.root/'foreign';foreign.mkdir()
        unsafe=self.root/'unsafe';unsafe.symlink_to(foreign,target_is_directory=True)
        with self.assertRaises((core.Blocked,ValueError)):
            processes.CommandJournal(unsafe)

    def test_started_write_failure_cleans_owned_process(self):
        original_write=processes.CommandJournal.write
        original_start=processes.start
        owned=[]
        def start(*args,**kwargs):
            handle=original_start(*args,**kwargs);owned.append(handle);return handle
        def fail(journal,action,record):
            if record['events'][-1]['event']=='started':raise OSError('fixture started persistence failure')
            return original_write(journal,action,record)
        try:
            with self.scope(),patch('execution.processes.start',side_effect=start),patch.object(processes.CommandJournal,'write',fail):
                with self.assertRaises((OSError,core.Blocked)):
                    core.command([sys.executable,'-c','import time; time.sleep(8)'],cwd=self.root,env=self.env,timeout=9)
            self.assertEqual(1,len(owned))
            self.assertIsNotNone(owned[0].supervisor.poll(),'Owned supervisor must be reaped before failure returns')
            self.assertIsNone(owned[0].supervisor.parent_lease_fd,'Owned lease must be closed on audit failure')
            self.assertNotEqual('EXITED',processes.read_outcome(owned[0].receipt)['status'])
        finally:
            for handle in owned:handle.close()

    def test_started_write_failure_preserves_unknown_budget(self):
        import io
        import execution.agent_runtime as runtime
        from execution.history import History
        from execution.budgets import Budgets
        from execution.model_policy import load,resolve
        from workflow_assurance_fixtures import fake_executor_start
        History(self.root/'.execution/trace.sqlite')
        selection=resolve(load([t['id'] for t in core.tasks()]),'gpt','T0002-002','developer')
        budget=Budgets(self.root/'.execution/budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens',
            'pools':{name:{'limit_tokens':1000,'invocation_allowance_tokens':100} for name in ('codex','openrouter')}})
        started=[]
        class FakeProcess:
            def __init__(inner,*args,**kwargs):
                started.append(True);inner.stdin=io.StringIO();inner.stdout=io.StringIO('');inner.stderr=io.StringIO('');inner.returncode=None
            def wait(inner,timeout=None):return inner.returncode
        original=processes.CommandJournal.write
        def fail(journal,action,record):
            if record['events'][-1]['event']=='started':raise OSError('fixture started persistence failure')
            return original(journal,action,record)
        with patch.object(runtime,'ROOT',self.root),patch('execution.processes.start',side_effect=fake_executor_start(FakeProcess)),patch.object(processes.CommandJournal,'write',fail):
            with self.assertRaises((OSError,core.Blocked)):
                runtime.invoke(selection,'T0002-002','developer',self.root,self.root/'.execution/runs/uncertain/developer',
                    'fixture',5,env=self.env,budget=budget,trace_context={'attempt_id':'uncertain','candidate':'fixture-candidate'})
        self.assertEqual([True],started)
        usage=[json.loads(line) for line in (self.root/'.execution/usage.jsonl').read_text().splitlines()]
        accounting=usage[0]['budget']
        self.assertEqual('UNKNOWN',accounting['reservation']['state'])
        self.assertEqual(100,accounting['reservation']['allowance'])
        self.assertIsNotNone(accounting['stop_reason'])
        self.assertIsNone(accounting['estimated_cost_usd'])
        # A refusal before a launcher is called remains a proven NOT_STARTED.
        other=self.root/'pre-spawn';other.mkdir()
        History(other/'.execution/trace.sqlite')
        before=Budgets(other/'.execution/budgets.sqlite',budget.policy)
        with patch.object(runtime,'ROOT',other),patch('execution.processes.start',side_effect=OSError('fixture pre-spawn refusal')) as launcher:
            with self.assertRaises(OSError):runtime.invoke(selection,'T0002-002','developer',other,other/'.execution/runs/pre/developer','fixture',5,env=self.env,budget=before)
            launcher.assert_called_once()
        pre=json.loads((other/'.execution/usage.jsonl').read_text())
        self.assertEqual('NOT_STARTED',pre['budget']['reservation']['state'])

    def test_reconciliation_rejects_symlink_before_read(self):
        journal=processes.CommandJournal(self.root/'.execution/commands')
        benign=self.root/'benign-external.json';benign.write_text('{}')
        alias=journal.root/'alias.json';alias.symlink_to(benign)
        read=Path.read_text;followed=[]
        def observe(path,*args,**kwargs):
            if path==alias:followed.append(True)
            return read(path,*args,**kwargs)
        with patch.object(Path,'read_text',observe):
            try:journal.require_reconciled()
            except (core.Blocked,ValueError):pass
        self.assertEqual([],followed,'Unsafe child alias must be rejected before its target is read')
        alias.unlink()
        (journal.root/'unindexed.json').write_text('{}')
        with self.assertRaises((core.Blocked,ValueError)):journal.require_reconciled()
        (journal.root/'unindexed.json').unlink()
        receipts=journal.root/'processes';receipts.mkdir()
        nested=receipts/'alias.json';nested.symlink_to(benign)
        with self.subTest(boundary='nested receipt alias'):
            with self.assertRaises((core.Blocked,ValueError)):journal.require_reconciled()
        nested.unlink()
        with self.scope():core.command([sys.executable,'-c','print("indexed")'],cwd=self.root,env=self.env)
        next(journal.root.glob('*.json')).unlink()
        with self.subTest(boundary='missing indexed command'):
            with self.assertRaises((core.Blocked,ValueError)):journal.require_reconciled()

    def test_policy_rejects_spoofed_binary_and_detach_variants(self):
        import shutil
        for argv in ([str(self.root/'git'),'diff'],['/unreviewed/git','diff'],
                     ['docker','run','--detach=true','fixture'],['docker','run','-dit','fixture'],
                     ['docker','run','--privileged=true','fixture'],['docker','run','-itd','fixture']):
            with self.subTest(argv=argv),self.assertRaises(core.Blocked):self.policy(argv,self.root,'coordinator-tools')
        # A real path with a spoofed basename is insufficient even when executable.
        fake=self.root/'git';fake.write_text('#!/bin/sh\nexit 0\n');fake.chmod(0o700)
        with self.assertRaises(core.Blocked):self.policy([str(fake),'diff'],self.root,'coordinator-tools')
        self.policy(['git','rev-parse','HEAD'],self.root,'coordinator-tools')
        self.policy([shutil.which('git'),'rev-parse','HEAD'],self.root,'coordinator-tools')

    def test_owned_live_action_allows_independent_command_but_restart_blocks(self):
        original=processes.start
        def start(argv,**kwargs):
            if argv[0]=='git':
                argv=[sys.executable,'-c','import time; time.sleep(5)']
                kwargs['admission']=processes.admit_command(argv,kwargs['cwd'],policy_id='offline-fixture')
            return original(argv,**kwargs)
        handle=None
        try:
            with self.scope(),patch('execution.processes.start',side_effect=start):
                handle=core.start_process(['git','merge','--ff-only','fixture'],cwd=self.root,env=self.env,timeout=6)
                self.assertIsNone(handle.supervisor.poll())
                self.assertEqual('independent\n',core.command([sys.executable,'-c','print("independent")'],cwd=self.root,env=self.env))
                # A restarted coordinator cannot inherit in-memory ownership.
                with patch.object(processes,'_OWNED_COMMANDS',{},create=True):
                    with self.assertRaisesRegex(core.Blocked,'reconciliation'):
                        core.command([sys.executable,'-c','print("restart must block")'],cwd=self.root,env=self.env)
        finally:
            if handle is not None:handle.close()

    def test_dead_or_foreign_supervisor_cannot_claim_live_exemption(self):
        from types import SimpleNamespace
        import time
        import uuid
        journal=processes.CommandJournal(self.root/'.execution/commands')
        action=uuid.uuid4().hex;execution=uuid.uuid4().hex;now=time.time()
        record={'schema':1,'action_id':action,'actor':'coordinator','task':'T0010-009','parent_action':'fixture',
            'candidate':'fixture','cwd':str(self.root),'policy':'coordinator-tools','side_effect':True,
            'events':[{'event':'intent','action_id':action,'at':now},
                      {'event':'started','action_id':action,'at':now,'execution_id':execution}]}
        receipt=journal.root/'processes'/(action+'.process.json');receipt.parent.mkdir()
        journal.write(action,record)
        for label,pid,code,status in (('dead',os.getpid(),-9,'STARTING'),
                ('foreign',os.getpid()+1,None,'STARTING'),('interrupted',os.getpid(),None,'INTERRUPTED')):
            processes.write_receipt(receipt,{'schema':1,'execution_id':execution,'status':status,
                'returncode':None,'started_at':now,'finished_at':now,'assurance':processes.ASSURANCE,'admission':{'fixture':'proof'}})
            read_fd,write_fd=os.pipe()
            try:
                handle=processes.ProcessHandle(receipt,execution,2,0,admission={'fixture':'proof'})
                handle.creator_pid=pid
                handle.supervisor=SimpleNamespace(parent_lease_fd=write_fd,poll=lambda:code)
                with self.subTest(state=label),patch.dict(processes._OWNED_COMMANDS,{(str(journal.root),action):handle}):
                    with self.assertRaises((core.Blocked,ValueError)):journal.require_reconciled()
            finally:
                os.close(read_fd);os.close(write_fd)

    def test_postlaunch_setup_failure_preserves_ownership_and_uncertainty(self):
        import io
        import threading
        for mode in ('stdin','drain-first','drain-second','cleanup-failure'):
            with self.subTest(mode=mode):
                folder=self.root/mode;folder.mkdir();receipt=folder/'process.json'
                calls={'terminate':0,'wait':0,'threads':0}
                class BadInput(io.StringIO):
                    failed=False
                    def close(inner):
                        if not inner.failed:
                            inner.failed=True
                            raise OSError('fixture stdin setup failure')
                        super().close()
                class Supervisor:
                    returncode=None
                    parent_lease_fd=None
                    stdin=BadInput() if mode in ('stdin','cleanup-failure') else io.StringIO()
                    stdout=io.StringIO('');stderr=io.StringIO('')
                    def poll(inner):return inner.returncode
                    def terminate(inner):calls['terminate']+=1;inner.returncode=-15
                    def wait(inner,timeout=None):
                        calls['wait']+=1
                        if mode=='cleanup-failure':raise OSError('fixture cleanup uncertainty')
                        return inner.returncode
                original=threading.Thread.start
                def start(thread):
                    calls['threads']+=1
                    if calls['threads']==(2 if mode=='drain-second' else 1):raise RuntimeError('fixture drain setup failure')
                    return original(thread)
                argv=[sys.executable,'-c','pass'];approval=processes.admit_command(argv,folder,policy_id='offline-fixture')
                with patch('execution.processes.launch',return_value=Supervisor()),patch.object(threading.Thread,'start',start):
                    try:processes.start(argv,cwd=folder,env=self.env,timeout=2,receipt=receipt,admission=approval)
                    except Exception as failure:
                        self.assertGreater(calls['terminate'],0,'Postlaunch setup failure must terminate its owned supervisor')
                        self.assertGreater(calls['wait'],0,'Postlaunch setup failure must reap or expose cleanup uncertainty')
                        self.assertTrue(getattr(failure,'may_have_started',False))
                        self.assertEqual(mode!='cleanup-failure',getattr(failure,'cleanup_completed',None))
                        self.assertIsNotNone(getattr(failure,'handle',None),'Uncertain cleanup retains the lifetime handle')
                    else:self.fail('Fixture must fail postlaunch setup')

    def test_output_publication_is_serialized_with_independent_admission(self):
        import io
        import threading
        from execution.history import History
        from execution.budgets import Budgets
        from execution.model_policy import load,resolve
        import execution.agent_runtime as runtime
        from workflow_assurance_fixtures import fake_executor_start
        History(self.root/'.execution/trace.sqlite')
        selection=resolve(load([task['id'] for task in core.tasks()]),'gpt','T0002-002','developer')
        budget=Budgets(self.root/'.execution/budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens',
            'pools':{pool:{'limit_tokens':1000,'invocation_allowance_tokens':100} for pool in ('codex','openrouter')}})
        class Provider:
            returncode=0
            def __init__(inner,argv,**kwargs):
                inner.stdin=io.StringIO();inner.stderr=io.StringIO('')
                inner.stdout=io.StringIO(json.dumps({'type':'turn.started'})+'\n'+json.dumps({'type':'turn.completed','usage':{'input_tokens':7,'output_tokens':3}})+'\n')
                Path(argv[argv.index('--output-last-message')+1]).write_text(json.dumps({'status':'APPROVED','summary':'fake','findings':[],'evidence':[]}))
            def wait(inner,timeout=None):return 0
        paused=threading.Event();release=threading.Event();independent_done=threading.Event();local=threading.local()
        errors=[];outputs=[];original_write=processes.CommandJournal.write;original_append=History.append
        def write(journal,action,record):
            local.outputs='output_artifacts' in record
            try:return original_write(journal,action,record)
            finally:local.outputs=False
        def append(history,event,**kwargs):
            result=original_append(history,event,**kwargs)
            if event=='artifact.staging' and getattr(local,'outputs',False):
                paused.set()
                if not release.wait(4):raise AssertionError('Bounded fixture publication release timed out')
            return result
        def model():
            try:runtime.invoke(selection,'T0002-002','developer',self.root,self.root/'.execution/runs/concurrent/developer','fixture',3,
                env=self.env,budget=budget,trace_context={'attempt_id':'concurrent','candidate':'fixture'})
            except BaseException as error:errors.append(error)
        def independent():
            try:
                with self.scope():outputs.append(core.command([sys.executable,'-c','print("independent")'],cwd=self.root,env=self.env))
            except BaseException as error:errors.append(error)
            finally:independent_done.set()
        worker=threading.Thread(target=model);other=threading.Thread(target=independent)
        try:
            with patch.object(runtime,'ROOT',self.root),patch('execution.processes.start',side_effect=fake_executor_start(Provider)),patch.object(processes.CommandJournal,'write',write),patch.object(History,'append',append):
                worker.start();self.assertTrue(paused.wait(3))
                other.start()
                self.assertFalse(independent_done.wait(.2),'Independent admission must wait for healthy atomic publication')
                release.set();worker.join(4);other.join(4)
                self.assertFalse(worker.is_alive());self.assertFalse(other.is_alive())
                self.assertEqual([],errors);self.assertEqual(['independent\n'],outputs)
        finally:
            release.set()
            if worker.ident is not None:worker.join(5)
            if other.ident is not None:other.join(5)

    def test_normal_finalization_does_not_block_independent_command(self):
        import threading
        handle=None;worker=None;release=threading.Event();verified=threading.Event();errors=[]
        try:
            with self.scope():handle=core.start_process([sys.executable,'--version'],cwd=self.root,env=self.env,timeout=3)
            original=handle.handle.wait
            def pause():
                result=original();verified.set()
                if not release.wait(4):raise AssertionError('Bounded finalization release timed out')
                return result
            def finish():
                try:handle.wait()
                except BaseException as error:errors.append(error)
            with patch.object(handle.handle,'wait',side_effect=pause):
                worker=threading.Thread(target=finish);worker.start();self.assertTrue(verified.wait(3))
                self.assertEqual(('EXITED',0),(handle.handle._result['status'],handle.handle._result['returncode']))
                self.assertIsNone(handle.supervisor.parent_lease_fd)
                with self.scope():self.assertIn('Python ',core.command([sys.executable,'--version'],cwd=self.root,env=self.env))
                release.set();worker.join(4)
                self.assertFalse(worker.is_alive());self.assertEqual([],errors)
            with self.scope():self.assertIn('Python ',core.command([sys.executable,'--version'],cwd=self.root,env=self.env))
        finally:
            release.set()
            if worker is not None:worker.join(5)
            if handle is not None:handle.close()

    def test_pending_finalization_rejects_interrupted_or_foreign_result(self):
        import threading
        import uuid
        release=threading.Event();verified=threading.Event();worker=None;handle=None;errors=[]
        try:
            with self.scope():handle=core.start_process([sys.executable,'--version'],cwd=self.root,env=self.env,timeout=3)
            raw=handle.handle;original=raw.wait
            def pause():
                result=original();verified.set()
                if not release.wait(4):raise AssertionError('Bounded finalization release timed out')
                return result
            def finish():
                try:handle.wait()
                except BaseException as error:errors.append(error)
            with patch.object(raw,'wait',side_effect=pause):
                worker=threading.Thread(target=finish);worker.start();self.assertTrue(verified.wait(3))
                cached=dict(raw._result);receipt=raw.receipt.read_bytes();creator=raw.creator_pid;code=raw.supervisor.returncode
                for mode in ('interrupted','foreign','missing','mismatched','capture-error','dead','unknown','foreign-proof'):
                    try:
                        if mode=='interrupted':raw._result={**cached,'status':'INTERRUPTED','returncode':None}
                        elif mode=='foreign':raw.creator_pid=creator+1
                        elif mode=='missing':raw.receipt.unlink()
                        elif mode=='mismatched':
                            current=json.loads(receipt);current['execution_id']=uuid.uuid4().hex;processes.write_receipt(raw.receipt,current)
                        elif mode=='capture-error':raw._capture_errors.add('stdout')
                        elif mode=='dead':raw.supervisor.returncode=-9
                        elif mode=='unknown':raw._result=None
                        else:
                            current=json.loads(receipt);current['admission']={'policy_id':'foreign'};processes.write_receipt(raw.receipt,current)
                        with self.subTest(mode=mode),self.assertRaises((core.Blocked,ValueError,OSError)):
                            with processes._COMMAND_LOCK:handle.journal.require_reconciled()
                    finally:
                        raw._result=dict(cached);raw.creator_pid=creator;raw.supervisor.returncode=code;raw._capture_errors.clear();raw.receipt.write_bytes(receipt)
                release.set();worker.join(4);self.assertFalse(worker.is_alive());self.assertEqual([],errors)
            with processes._COMMAND_LOCK:handle.journal.require_reconciled()
        finally:
            release.set()
            if worker is not None:worker.join(5)
            if handle is not None:handle.close()

    def test_precache_finalization_coordinates_independent_admission(self):
        import threading
        for interval in ('precache','before-owner-wait'):
            with self.subTest(interval=interval):
                handle=None;owner=None;other=None;paused=threading.Event();release=threading.Event();done=threading.Event();errors=[];outputs=[]
                try:
                    with self.scope():handle=core.start_process([sys.executable,'--version'],cwd=self.root,env=self.env,timeout=3)
                    original=processes.close_lease
                    def close(process):
                        original(process)
                        if process is handle.supervisor:
                            paused.set()
                            if not release.wait(4):raise AssertionError('Bounded pre-cache release timed out')
                    def finish():
                        try:handle.wait()
                        except BaseException as error:errors.append(error)
                    def independent():
                        try:
                            with self.scope():outputs.append(core.command([sys.executable,'--version'],cwd=self.root,env=self.env))
                        except BaseException as error:errors.append(error)
                        finally:done.set()
                    if interval=='precache':
                        with patch('execution.processes.close_lease',side_effect=close):
                            owner=threading.Thread(target=finish);owner.start();self.assertTrue(paused.wait(3))
                            self.assertIsNone(handle.handle._result)
                            other=threading.Thread(target=independent);other.start()
                            self.assertFalse(done.wait(.15),'Admission must coordinate unfinished current-owner validation')
                            acquired=processes._COMMAND_LOCK.acquire(timeout=.2)
                            self.assertTrue(acquired,'Finalization waiting must release the global admission lock')
                            if acquired:processes._COMMAND_LOCK.release()
                            release.set();owner.join(4);other.join(4)
                    else:
                        handle.supervisor.wait(timeout=3)
                        self.assertIsNone(handle.handle._result)
                        other=threading.Thread(target=independent);other.start();other.join(4)
                        handle.wait()
                    self.assertTrue(done.is_set());self.assertEqual([],errors)
                    self.assertEqual(1,len(outputs));self.assertIn('Python ',outputs[0])
                finally:
                    release.set()
                    if owner is not None:owner.join(5)
                    if other is not None:other.join(5)
                    if handle is not None:handle.close()

    def test_precache_interruption_or_stall_does_not_admit_command(self):
        import threading
        import time
        initial=self.root
        for mode in ('stall','capture-error','interrupted','missing'):
            with self.subTest(mode=mode):
                self.root=initial/mode;self.root.mkdir();handle=None;owner=None;other=None
                paused=threading.Event();release=threading.Event();done=threading.Event();owner_errors=[];admission_errors=[]
                try:
                    with self.scope():handle=core.start_process([sys.executable,'--version'],cwd=self.root,env=self.env,timeout=3)
                    original=processes.close_lease
                    def close(process):
                        original(process)
                        if process is handle.supervisor:
                            paused.set()
                            if not release.wait(4):raise AssertionError('Bounded failed-finalization release timed out')
                            if mode=='capture-error':handle.handle._capture_errors.add('stdout')
                            elif mode=='interrupted':handle.supervisor.returncode=-9
                            elif mode=='missing':handle.handle.receipt.unlink()
                    def finish():
                        try:handle.wait()
                        except BaseException as error:owner_errors.append(error)
                    def independent():
                        try:
                            with self.scope():core.command([sys.executable,'--version'],cwd=self.root,env=self.env)
                        except BaseException as error:admission_errors.append(error)
                        finally:done.set()
                    with patch('execution.processes.close_lease',side_effect=close),patch.object(processes,'FINALIZATION_WAIT_SECONDS',.25,create=True):
                        owner=threading.Thread(target=finish);owner.start();self.assertTrue(paused.wait(3))
                        with patch('execution.processes.start',wraps=processes.start) as spawn:
                            started=time.monotonic();other=threading.Thread(target=independent);other.start()
                            if mode=='stall':
                                self.assertFalse(done.wait(.05),'Unknown current-owner completion must be awaited before bounded refusal')
                            else:release.set()
                            self.assertTrue(done.wait(2));self.assertLess(time.monotonic()-started,2)
                            self.assertEqual(1,len(admission_errors));self.assertIsInstance(admission_errors[0],core.Blocked)
                            spawn.assert_not_called()
                        release.set();owner.join(4);other.join(4)
                        self.assertFalse(owner.is_alive());self.assertFalse(other.is_alive())
                finally:
                    release.set()
                    if owner is not None:owner.join(5)
                    if other is not None:other.join(5)
                    if handle is not None:handle.close()
                    self.root=initial
