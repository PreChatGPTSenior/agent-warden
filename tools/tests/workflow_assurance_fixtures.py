"""Offline test runner: no providers, no network, only owned local fixtures.

macOS refuses /bin/ps inside Seatbelt. Run its exact read-only process-table
query in the parent; sandbox Python/Git children instead. Never use this runner
for real agent execution. Guards are process-lifetime and cannot be uninstalled.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import unittest


BASELINE = (
    'test_agent_history', 'test_agent_workflow', 'test_agent_budgets',
    'test_agent_supervision', 'test_agent_models',
)
SANDBOX = ''  # Bound to the exact approved executables when guards install.
_INSTALLED = False


def install_offline_guards():
    """Deny parent networking; sandbox allowed children; refuse model launch."""
    global _INSTALLED, SANDBOX
    if _INSTALLED or getattr(subprocess, '_stone_offline_guards_installed', False):
        return
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        raise RuntimeError('This offline process qualification requires macOS sandbox-exec')
    python = str(Path(sys.executable).resolve())
    git = shutil.which('git')
    if not git:
        raise RuntimeError('Git fixture executable unavailable')
    git = str(Path(git).resolve())
    import json
    SANDBOX = '(version 1)(allow default)(deny network*)(deny process-exec)(allow process-exec ' + ' '.join('(literal ' + json.dumps(path) + ')' for path in (python, git, str((Path(sys.base_prefix) / 'Resources/Python.app/Contents/MacOS/Python').resolve()), '/usr/bin/sandbox-exec', '/bin/ps')) + ')'
    original = subprocess.Popen

    def guarded(args, *positional, **kwargs):
        if kwargs.get('shell') or kwargs.get('executable') or not isinstance(args, (list, tuple)) or not args:
            raise AssertionError('Offline runner requires explicit argv without shell/executable overrides')
        argv = [os.fspath(part) for part in args]
        executable = shutil.which(argv[0])
        resolved = str(Path(executable).resolve()) if executable else ''
        if resolved == '/bin/ps' and argv[1:] == ['-axo', 'pgid=,stat=']:
            argv[0] = '/bin/ps'
        elif resolved in (python, git):
            if resolved == git and (len(argv) < 2 or argv[1] not in {
                    'init', 'config', 'add', 'commit', 'worktree', 'merge',
                    'rev-parse', 'diff', 'status', 'ls-files'}):
                raise AssertionError('Git network/destructive operation forbidden in offline tests')
            argv = ['/usr/bin/sandbox-exec', '-p', SANDBOX, resolved, *argv[1:]]
        else:
            raise AssertionError('Unapproved executable in offline tests: ' + Path(argv[0]).name)
        return original(argv, *positional, **kwargs)

    def audit(event, args):
        if event in {'socket.connect', 'socket.connect_ex', 'socket.getaddrinfo',
                     'socket.gethostbyname', 'socket.sendto', 'socket.sendmsg', 'socket.bind'}:
            raise AssertionError('Network forbidden in offline qualification')
        if event in {'os.system', 'os.posix_spawn', 'os.posix_spawnp', 'os.exec'}:
            raise AssertionError('Unsupervised process launch forbidden in offline tests')
        if event == 'subprocess.Popen':
            executable, argv = os.fspath(args[0]), args[1]
            sandboxed = (executable == '/usr/bin/sandbox-exec' and
                         isinstance(argv, (list, tuple)) and len(argv) >= 5 and
                         list(argv[:3]) == ['/usr/bin/sandbox-exec', '-p', SANDBOX] and
                         argv[3] in (python, git))
            process_query = executable == '/bin/ps' and list(argv) == ['/bin/ps', '-axo', 'pgid=,stat=']
            if not (sandboxed or process_query):
                raise AssertionError('Raw process launch bypassed the offline allowlist')

    # Prevent subprocess from choosing a posix_spawn route also denied above.
    subprocess._USE_POSIX_SPAWN = False
    sys.addaudithook(audit)
    subprocess.Popen = guarded
    subprocess._stone_offline_guards_installed = True
    _INSTALLED = True


def fake_executor_start(factory):
    """Adapt an existing in-memory provider fixture at the common executor seam.

    Non-provider actions still use the real guarded executor. Fake terminal
    evidence is explicit disposable test data and cannot qualify a live process.
    """
    import time
    import uuid
    from execution import processes
    real_start = processes.start
    def start(argv, *, cwd, env, timeout, receipt, admission, **kwargs):
        if Path(argv[0]).name != 'codex':
            return real_start(argv,cwd=cwd,env=env,timeout=timeout,receipt=receipt,
                              admission=admission,**kwargs)
        _, proof = processes._approval(admission,argv,cwd)
        supervisor = factory(argv,cwd=cwd,env=env,timeout=timeout)
        if not hasattr(supervisor,'poll'):
            supervisor.poll = lambda: supervisor.returncode
        class Handle:
            execution_id = uuid.uuid4().hex
            started_at = time.time()
            def __init__(self):
                self.supervisor = supervisor
                self.receipt = Path(receipt)
                self.receipt.parent.mkdir(parents=True,exist_ok=True)
            def wait(self):
                code = self.supervisor.wait(timeout=timeout)
                result = {'schema':1,'execution_id':self.execution_id,'status':'EXITED',
                          'returncode':code,'started_at':self.started_at,'finished_at':time.time(),
                          'assurance':processes.ASSURANCE,'admission':proof,
                          'stdout':'','stderr':'','stdout_truncated':False,'stderr_truncated':False}
                processes.write_receipt(self.receipt,result)
                return result
            def cancel(self): self.supervisor.returncode = -15
            def close(self):
                self.cancel()
                return self.wait()
        return Handle()
    return start


def main():
    selected = sys.argv[1:] or list(BASELINE)
    allowed = set(BASELINE) | {'test_maintenance_dispatch'}
    if any(name.split('.')[0] not in allowed for name in selected):
        raise SystemExit('Only explicitly scoped offline modules/cases are allowed')
    install_offline_guards()
    suite = unittest.defaultTestLoader.loadTestsFromNames(selected)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())


def fixture_money_policy():
    """Nonzero fictional accounting values, never written to production policy."""
    return {'schema': 2, 'unit': 'usd', 'pools': {
        pool: {'limit_usd': '0.000200', 'invocation_allowance_usd': '0.000100'}
        for pool in ('codex', 'openrouter')}, 'prices': {'codex:fixture': {
        'input_usd_per_million': '1.000000', 'cached_input_usd_per_million': '0.500000',
        'output_usd_per_million': '2.000000', 'basis': 'configured_estimate',
        'source': 'https://fixture.invalid/rate', 'valid_until': '2099-01-01T00:00:00+00:00'}}}


_COMBINED_COORDINATOR = r'''
import json, os, pathlib, sys, time
from execution.budgets import Budgets
from execution.core import State, sha
from execution.history import History
from execution.processes import start, admit_command, CommandJournal
from execution.agent_runtime import append_ledger
from workflow_assurance_fixtures import fixture_money_policy
from test_agent_supervision import CHILD
root=pathlib.Path(sys.argv[1]); boundary=sys.argv[2]; audit=root/'.execution'
history=History(audit/'trace.sqlite')
task={'id':'T0010-018','depends_on':[],'exclusive_resources':['fixture']}
state=State(audit/'state.sqlite'); state.claim(task,'attempt-1')
history.append('task.claimed',task=task['id'],trace='attempt-1',payload={'owner':'attempt-1','packet':task})
budget=Budgets(audit/'budgets.sqlite',fixture_money_policy())
selection={'model':'fixture','provider_config':{'kind':'builtin','provider_id':'openai'}}
budget.reserve('fake-call',selection,task['id'],'developer','fixture')
history.append('invocation.started',task=task['id'],trace='attempt-1',session='fake-call',role='developer',payload={'kind':'preflight'})
argv=[sys.executable,'-c',CHILD,str(root)] if boundary!='normal' else [sys.executable,'-c','print("fake provider complete")']
journal=CommandJournal(audit/'commands'); action='fixture-action'
record={'schema':1,'action_id':action,'actor':'fixture-coordinator','task':task['id'],
 'parent_action':'attempt-1','candidate':sys.argv[3],'argv':argv,'cwd':str(root),
 'policy':'fixture-reviewed-nondetaching-command','side_effect':False,
 'events':[{'event':'intent','action_id':action,'at':time.time()}]}
journal.write(action,record)
handle=start(argv,cwd=root,env=dict(os.environ),timeout=12,receipt=audit/'commands/processes/fixture-action.process.json',admission=admit_command(argv,root,policy_id=record['policy']))
record['events'].append({'event':'started','action_id':action,'at':time.time(),'execution_id':handle.execution_id})
journal.write(action,record)
def fault(position):
 if position==boundary:
  deadline=time.monotonic()+4
  while not (root/'heartbeat').exists() and time.monotonic()<deadline:time.sleep(.01)
  if not (root/'heartbeat').exists():raise RuntimeError('dummy tree did not start')
  (root/'boundary.json').write_text(json.dumps({'boundary':position,'execution_id':handle.execution_id,'pid':os.getpid()}))
  while True:time.sleep(.01)
history.write_artifact('runs/attempt-1/evidence.json',{'fixture':'written at actual boundary'},trace='attempt-1',task=task['id'],fault=fault)
outcome=handle.wait()
record['events'].append({'event':'outcome','action_id':action,'at':time.time(),'outcome':outcome}); journal.write(action,record)
budget.observe('fake-call',{'known_input_tokens':2,'known_output_tokens':1,'status':'COMPLETE'},final=True)
receipt=history.write_artifact('runs/attempt-1/fake-call.execution.json',{'session':'fake-call','artifact_hashes':{}},trace='attempt-1',task=task['id'])
history.append('invocation.finished',task=task['id'],trace='attempt-1',session='fake-call',role='developer',payload={'receipt':str(receipt),'sha256':sha(receipt),'status':'COMPLETED'})
append_ledger(audit/'usage.jsonl',{'session':'fake-call','artifact_hashes':{}})
state.release('attempt-1')
'''


def combined_workflow_fixture(root, *, boundary):
    """Kill only the owned coordinator at the real durable-write callback.

    Fixed boundaries and deadlines replace random scheduling. The unrelated
    process must survive; only the supervisor owns descendant group cleanup.
    """
    import json
    import time
    root = Path(root); root.mkdir(parents=True)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent))), PYTHONDONTWRITEBYTECODE='1')
    def git(*args):
        result = subprocess.run(['git',*args],cwd=root,env=env,capture_output=True,text=True,timeout=5)
        if result.returncode: raise AssertionError(result.stderr)
        return result.stdout.strip()
    git('init','-b','main');git('config','user.name','Combined Offline Fixture');git('config','user.email','fixture@example.invalid')
    (root/'feature.txt').write_text('baseline')
    git('add','feature.txt');git('commit','-m','disposable fixture seed')
    before = git('rev-parse','HEAD')
    effective_boundary = boundary or 'normal'
    unrelated = subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],env=env)
    coordinator = None
    try:
        coordinator = subprocess.Popen([sys.executable,'-c',_COMBINED_COORDINATOR,str(root),effective_boundary,before],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if effective_boundary != 'normal':
            deadline = time.monotonic()+7
            while not (root/'boundary.json').exists() and coordinator.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            if not (root/'boundary.json').exists():
                raise AssertionError('Coordinator missed persisted boundary: '+str(coordinator.communicate(timeout=2)))
            coordinator.kill()
        stdout, stderr = coordinator.communicate(timeout=8)
        if coordinator.returncode not in (0,-9):raise AssertionError(stderr)
        receipt = root/'.execution/commands/processes/fixture-action.process.json'
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            if receipt.exists():
                try:
                    outcome=json.loads(receipt.read_text())
                    if outcome.get('status') not in ('STARTING','RUNNING'):break
                except json.JSONDecodeError:pass
            time.sleep(.02)
        outcome=json.loads(receipt.read_text())
        stopped=True
        if effective_boundary!='normal':
            heartbeat=(root/'heartbeat').read_text();time.sleep(.15)
            pgid=int((root/'child-pgid').read_text())
            rows=subprocess.check_output(['/bin/ps','-axo','pgid=,stat='],text=True)
            stopped=(heartbeat==(root/'heartbeat').read_text() and all(row.split()[1].startswith('Z') for row in rows.splitlines() if row.split()[0]==str(pgid)))
        import sqlite3
        with sqlite3.connect(root/'.execution/budgets.sqlite') as db:
            reservation_state=db.execute('SELECT state FROM calls WHERE session=?',('fake-call',)).fetchone()[0]
        return {'process_status':outcome['status'],'reservation_state':reservation_state,
                'git_head_before':before,'git_head_after':git('rev-parse','HEAD'),
                'unrelated_survived':unrelated.poll() is None,'tree_stopped':stopped,
                'boundary':boundary,'coordinator_returncode':coordinator.returncode}
    finally:
        if coordinator is not None and coordinator.poll() is None:coordinator.kill();coordinator.communicate(timeout=3)
        if unrelated.poll() is None:unrelated.kill()
        unrelated.wait(timeout=3)
