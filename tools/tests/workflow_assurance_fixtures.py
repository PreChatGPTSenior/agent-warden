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
SANDBOX = '(version 1)(allow default)(deny network*)(deny process-exec (regex #".*/codex$"))'
_INSTALLED = False


def install_offline_guards():
    """Deny parent networking; sandbox allowed children; refuse model launch."""
    global _INSTALLED
    if _INSTALLED or getattr(subprocess, '_stone_offline_guards_installed', False):
        return
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        raise RuntimeError('This offline process qualification requires macOS sandbox-exec')
    python = str(Path(sys.executable).resolve())
    git = shutil.which('git')
    if not git:
        raise RuntimeError('Git fixture executable unavailable')
    git = str(Path(git).resolve())
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
                     'socket.gethostbyname', 'socket.sendto', 'socket.bind'}:
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
