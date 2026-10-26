"""Real POSIX lifetime fixtures; children are harmless Python programs, never models."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).absolute().parents[1]))
from execution.supervision import close_lease, launch
from execution.history import recovery_status


CHILD = '''import os, pathlib, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
root=pathlib.Path(sys.argv[1]);sys.stdin.read()
grandchild="import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)"
subprocess.Popen([sys.executable,'-c',grandchild])
(root/'child-pgid').write_text(str(os.getpgrp()))
while True:
    (root/'heartbeat').write_text(str(time.monotonic()))
    time.sleep(.03)
'''


class SupervisionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                        PYTHONPATH=str(Path(__file__).absolute().parents[1]))
        self.addCleanup(patch.stopall)
        patch('socket.socket.connect', side_effect=AssertionError('Network forbidden')).start()

    def wait_file(self, path):
        deadline = time.monotonic() + 5
        while not path.exists() and time.monotonic() < deadline: time.sleep(.02)
        self.assertTrue(path.exists(), 'Harmless fixture did not start')

    def assert_stopped(self):
        first = (self.root / 'heartbeat').read_text(); time.sleep(.15)
        self.assertEqual(first, (self.root / 'heartbeat').read_text())
        # No runnable member can remain, even if the platform temporarily retains
        # an adopted zombie. Reaping is performed by its owning parent/init.
        pgid = int((self.root / 'child-pgid').read_text())
        output = subprocess.check_output(['ps','-axo','pgid=,stat='], text=True)
        states = [line.split()[1] for line in output.splitlines() if line.split()[0] == str(pgid)]
        self.assertTrue(all(s.startswith('Z') for s in states), states)

    def test_lease_close_terminates_child_and_sigterm_ignoring_descendant(self):
        process = launch([sys.executable,'-c',CHILD,str(self.root)], cwd=self.root, env=self.env, timeout=15)
        self.addCleanup(close_lease, process)
        process.stdin.close(); self.wait_file(self.root/'heartbeat')
        close_lease(process)
        self.assertEqual(125, process.returncode)
        self.assert_stopped()
        process.stdout.close(); process.stderr.close()

    def test_independent_deadline_stops_process_with_parent_alive(self):
        process = launch([sys.executable,'-c',CHILD,str(self.root)], cwd=self.root, env=self.env, timeout=.8)
        self.addCleanup(close_lease, process)
        process.stdin.close(); self.wait_file(self.root/'heartbeat')
        self.assertEqual(124, process.wait(timeout=3)); self.assert_stopped()
        process.stdout.close(); process.stderr.close()

    def test_normal_exit_preserves_output_and_exit_status(self):
        process = launch([sys.executable,'-c','import sys; print(sys.stdin.read()); sys.exit(7)'],
                         cwd=self.root, env=self.env, timeout=5)
        self.addCleanup(close_lease, process)
        out, err = process.communicate('offline fixture', timeout=3)
        self.assertEqual(7, process.returncode); self.assertEqual('offline fixture\n',out); self.assertEqual('',err)

    def test_sigkill_of_coordinator_ends_invocation_but_keeps_unresolved_accounting(self):
        parent_code = '''import pathlib,sys
import execution.agent_runtime as runtime
from execution.budgets import Budgets
from execution.supervision import launch
root=pathlib.Path(sys.argv[1]); runtime.ROOT=root
def harmless(argv,**kwargs):
    assert argv[0]=='codex'
    return launch([sys.executable,'-c',sys.argv[2],str(root)],**kwargs)
runtime.launch=harmless
budget=Budgets(root/'.execution/budgets.sqlite',{'schema':1,'unit':'input_plus_output_tokens','pools':{
    pool:{'limit_tokens':100,'invocation_allowance_tokens':50} for pool in ('codex','openrouter')}})
selection={'model':'offline-fixture','reasoning_effort':'medium','provider_config':{'kind':'builtin','provider_id':'openai'}}
runtime.invoke(selection,'T0002-002','developer',root,root/'.execution/runs/attempt','offline',15,env={},budget=budget)
'''
        parent = subprocess.Popen([sys.executable,'-c',parent_code,str(self.root),CHILD],
                                  env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            self.wait_file(self.root/'heartbeat')
            parent.kill(); parent.wait(timeout=2)
            time.sleep(.6); self.assert_stopped()
            report = recovery_status(self.root/'.execution')
            self.assertEqual('RECOVERY_REQUIRED',report['status'])
            self.assertEqual(1,len(report['unsettled_budgets']))
            self.assertEqual(1,len(report['unfinished_invocations']))
        finally:
            if parent.poll() is None: parent.kill(); parent.wait(timeout=2)
            parent.stderr.close()


if __name__ == '__main__': unittest.main()
