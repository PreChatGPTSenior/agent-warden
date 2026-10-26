"""Harmless owned process trees; no providers or application services."""
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
from execution.supervision import launch, close_lease
from test_agent_supervision import CHILD

class ProcessExecutionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(Path(__file__).absolute().parents[1]))
        self.receipt=self.root/'receipt.json'
    def start(self,code='print("fixture")',**kwargs):
        from execution.processes import start,admit_command
        argv=[sys.executable,'-c',code]
        admission=admit_command(argv,self.root,policy_id='fixture-reviewed-nondetaching-command')
        handle=start(argv,cwd=self.root,env=self.env,timeout=kwargs.pop('timeout',5),receipt=self.receipt,admission=admission,**kwargs)
        self.addCleanup(handle.close)
        return handle
    def tree(self,**kwargs):
        return self.start(CHILD.replace('sys.argv[1]',repr(str(self.root))),**kwargs)
    def ready(self):
        until=time.monotonic()+4
        while not (self.root/'heartbeat').exists() and time.monotonic()<until:time.sleep(.02)
        self.assertTrue((self.root/'heartbeat').exists())
    def stopped(self):
        first=(self.root/'heartbeat').read_text();time.sleep(.15)
        self.assertEqual(first,(self.root/'heartbeat').read_text())
        pgid=int((self.root/'child-pgid').read_text())
        rows=subprocess.check_output(['ps','-axo','pgid=,stat='],text=True)
        self.assertTrue(all(row.split()[1].startswith('Z') for row in rows.splitlines() if row.split()[0]==str(pgid)))
    def test_normal_exit(self):
        h=self.start('import sys; print("out"); print("err",file=sys.stderr); sys.exit(7)')
        r=h.wait();self.assertEqual(('EXITED',7,'out\n','err\n'),(r['status'],r['returncode'],r['stdout'],r['stderr']))
        self.assertEqual('EXITED',json.loads(self.receipt.read_text())['status'])
    def test_spawn_failure(self):
        from execution.processes import start,admit_command
        argv=['/no/such/offline-fixture'];admission=admit_command(argv,self.root,policy_id='fixture-reviewed-spawn-failure')
        h=start(argv,cwd=self.root,env=self.env,timeout=3,receipt=self.receipt,admission=admission)
        self.addCleanup(h.close);self.assertEqual('SPAWN_FAILED',h.wait()['status'])
    def test_timeout_cleans_descendants(self):
        h=self.tree(timeout=.7);self.ready();self.assertEqual('TIMED_OUT',h.wait()['status']);self.stopped()
    def test_cancel_cleans_descendants(self):
        h=self.tree();self.ready();h.cancel();self.assertEqual('CANCELLED',h.wait()['status']);self.stopped()
    def test_coordinator_sigkill_cleans_descendants(self):
        code='''import pathlib,sys,time
from execution.processes import start,admit_command
root=pathlib.Path(sys.argv[1]);argv=[sys.executable,'-c',sys.argv[2],str(root)];approval=admit_command(argv,root,policy_id='fixture-reviewed-nondetaching-command')
start(argv,cwd=root,env=dict(__import__('os').environ),timeout=10,receipt=root/'receipt.json',admission=approval)
time.sleep(20)
'''
        parent=subprocess.Popen([sys.executable,'-c',code,str(self.root),CHILD],env=self.env)
        try:
            self.ready();parent.kill();parent.wait(timeout=2)
            until=time.monotonic()+4
            while time.monotonic()<until:
                if self.receipt.exists() and json.loads(self.receipt.read_text())['status']=='INTERRUPTED':break
                time.sleep(.03)
            self.assertEqual('INTERRUPTED',json.loads(self.receipt.read_text())['status']);self.stopped()
        finally:
            if parent.poll() is None:parent.kill();parent.wait(timeout=2)
    def test_supervisor_death_is_not_success(self):
        watchdog='import threading,os,signal,time; threading.Thread(target=lambda: (time.sleep(2),os.killpg(os.getpgrp(),signal.SIGKILL)),daemon=True).start()\n'
        process=launch([sys.executable,'-c',watchdog+CHILD,str(self.root)],cwd=self.root,env=self.env,timeout=8)
        try:
            process.stdin.close();self.ready();process.kill();process.wait(timeout=2);time.sleep(.5);self.stopped()
        finally:
            # A fixture-side watchdog signals its own live group if old supervision leaks.
            close_lease(process);process.stdout.close();process.stderr.close()
        (self.root/'heartbeat').unlink();(self.root/'child-pgid').unlink()
        handle=self.tree();self.ready();handle.supervisor.kill()
        self.assertEqual('INTERRUPTED',handle.wait()['status']);self.stopped()
    def test_supervisor_admission_failure(self):
        with patch('execution.processes.launch',side_effect=OSError('fixture admission failure')):
            h=self.start();self.assertEqual('ADMISSION_FAILED',h.wait()['status'])
        self.assertEqual('ADMISSION_FAILED',json.loads(self.receipt.read_text())['status'])
    def test_output_backpressure_is_bounded(self):
        h=self.start('import os; [(os.write(1,b"x"*8192),os.write(2,b"y"*8192)) for _ in range(128)]',output_limit=1024)
        r=h.wait();self.assertEqual('EXITED',r['status']);self.assertEqual(0,r['returncode'])
        self.assertEqual((1024,1024),(len(r['stdout']),len(r['stderr'])));self.assertTrue(r['stdout_truncated']);self.assertTrue(r['stderr_truncated'])
    def test_missing_terminal_receipt_is_interrupted(self):
        from execution.processes import read_outcome
        self.receipt.write_text(json.dumps({'schema':1,'status':'STARTING','execution_id':'fixture'}))
        self.assertEqual('INTERRUPTED',read_outcome(self.receipt)['status'])
    def test_unrelated_process_survives(self):
        survivor=subprocess.Popen([sys.executable,'-c','import time; time.sleep(15)'],env=self.env)
        try:
            h=self.tree();self.ready();h.cancel();h.wait();self.stopped();self.assertIsNone(survivor.poll())
        finally:survivor.terminate();survivor.wait(timeout=2)

    def test_completion_pipe_failure_cleans_owned_group(self):
        pulse="""import os,pathlib,signal,sys,threading,time
signal.signal(signal.SIGTERM,signal.SIG_IGN)
threading.Thread(target=lambda:(time.sleep(3),os.killpg(os.getpgrp(),signal.SIGKILL)),daemon=True).start()
root=pathlib.Path(sys.argv[1]);(root/'child-pgid').write_text(str(os.getpgrp()))
while True:
    (root/'heartbeat').write_text(str(time.monotonic()));time.sleep(.03)
"""
        child="import pathlib,subprocess,sys,time; subprocess.Popen([sys.executable,'-c',sys.argv[2],sys.argv[1]]); p=pathlib.Path(sys.argv[1])/'heartbeat'\nwhile not p.exists():time.sleep(.01)"
        result_read,result_write=os.pipe();owner_read,owner_write=os.pipe();os.close(result_read)
        script='from execution.supervision import group_runner; import sys; group_runner(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3:])'
        anchor=subprocess.Popen([sys.executable,'-c',script,str(result_write),str(owner_read),sys.executable,'-c',child,str(self.root),pulse],
            env=self.env,start_new_session=True,pass_fds=(result_write,owner_read),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        os.close(result_write);os.close(owner_read)
        try:
            self.ready();anchor.wait(timeout=3);self.stopped()
        finally:
            os.close(owner_write)
            # The fixture-side watchdog self-signals its live group even on the red path.
            if anchor.poll() is None:anchor.wait(timeout=4)
            time.sleep(3 if anchor.returncode==1 else 0)
    def test_output_sanitization_across_chunks_and_truncation(self):
        secret='fixture-private-token-value'
        self.env['FIXTURE_API_TOKEN']=secret
        code='import os,time; os.write(1,b"ok:fixture-pri"); time.sleep(.08); os.write(1,b"vate-token-value:end"); os.write(2,b"fixture-private-token-value")'
        handle=self.start(code,output_limit=15);result=handle.wait()
        self.assertEqual('EXITED',result['status'])
        for name in ['stdout','stderr']:
            self.assertNotIn('fixture-pri',result[name]);self.assertIn('[REDACTED]',result[name]);self.assertLessEqual(len(result[name]),15)
        self.assertNotIn(secret,self.receipt.read_text())
        self.receipt=self.root/'configured.json'
        result=self.start('print("configured-private-value")',sensitive_values=['configured-private-value']).wait()
        self.assertEqual('[REDACTED]\n',result['stdout'])
        self.receipt=self.root/'partial.json'
        result=self.start('print("fixture-pri",end="")').wait()
        self.assertNotIn('fixture-pri',result['stdout'])
    def test_capture_failure_is_interrupted(self):
        from execution.processes import ProcessHandle
        value={'schema':1,'status':'EXITED','execution_id':'a'*32,'returncode':0,'started_at':1.,'finished_at':2.}
        self.receipt.write_text(json.dumps(value));handle=ProcessHandle(self.receipt,'a'*32,2,100)
        class Stream:
            def fileno(self):return 0
            def close(self):pass
        with patch('execution.processes.os.read',side_effect=OSError('private fixture capture detail')):
            try:handle._drain('stdout',Stream())
            except OSError:pass
        result=handle.wait();self.assertEqual('INTERRUPTED',result['status']);self.assertEqual(['stdout'],result['capture_errors'])
        self.assertNotIn('private fixture capture detail',str(result))
    def test_malformed_terminal_receipts_are_interrupted(self):
        from execution.processes import read_outcome
        valid={'schema':1,'status':'EXITED','execution_id':'a'*32,'returncode':0,'started_at':1.,'finished_at':2.}
        self.receipt.write_text(json.dumps(valid));self.assertEqual('EXITED',read_outcome(self.receipt,'a'*32)['status'])
        invalid=[{},dict(valid,returncode=None),dict(valid,returncode=True),dict(valid,returncode=999),
                 dict(valid,status='TIMED_OUT',returncode=0),dict(valid,finished_at=0),dict(valid,finished_at=float('nan')),
                 dict(valid,started_at=True),dict(valid,execution_id=''),dict(valid,schema=True),dict(valid,status=['EXITED'])]
        invalid.extend({k:v for k,v in valid.items() if k!=missing} for missing in ['returncode','started_at','finished_at'])
        for number,value in enumerate(invalid):
            with self.subTest(case=number):
                self.receipt.write_text(json.dumps(value));self.assertEqual('INTERRUPTED',read_outcome(self.receipt,'a'*32)['status'])
    def test_missing_or_mismatched_admission_blocks_before_spawn(self):
        from execution.processes import start
        with patch('execution.processes.launch',side_effect=OSError('spawn must not be reached')) as spawn:
            with self.subTest(case='missing'):
                with self.assertRaises(ValueError):start([sys.executable,'-c','pass'],cwd=self.root,env=self.env,timeout=2,receipt=self.receipt)
            self.assertFalse(spawn.called)
        from execution.processes import admit_command
        approved=admit_command([sys.executable,'-c','pass'],self.root,policy_id='fixture-reviewed-policy')
        cases=[True,{},approved]
        for index,approval in enumerate(cases):
            with self.subTest(case=index),patch('execution.processes.launch') as spawn:
                with self.assertRaises(ValueError):start([sys.executable,'-c','print("changed")'],cwd=self.root,env=self.env,timeout=2,receipt=self.root/('denied-'+str(index)),admission=approval)
                spawn.assert_not_called()
        other=self.root/'other';other.mkdir()
        with patch('execution.processes.launch') as spawn:
            with self.assertRaises(ValueError):start([sys.executable,'-c','pass'],cwd=other,env=self.env,timeout=2,receipt=self.root/'wrong-cwd',admission=approved)
            spawn.assert_not_called()
    def test_admitted_command_reports_process_group_boundary(self):
        from execution.processes import start,admit_command
        argv=[sys.executable,'-c','print("trusted")']
        admission=admit_command(argv,self.root,policy_id='fixture-reviewed-policy')
        handle=start(argv,cwd=self.root,env=self.env,timeout=2,receipt=self.receipt,admission=admission)
        self.addCleanup(handle.close);result=handle.wait()
        self.assertEqual('EXITED',result['status']);self.assertEqual('TRUSTED_COMMAND_PROCESS_GROUP',result['assurance'])
        self.assertEqual('non-detaching-process-group',result['admission']['boundary'])
        self.assertEqual('fixture-reviewed-policy',result['admission']['policy_id'])
        receipt=json.loads(self.receipt.read_text());self.assertEqual(result['admission'],receipt['admission'])
        self.assertNotIn('argv',receipt);self.assertNotIn('env',receipt)

    def test_final_interruption_is_durable_and_preserves_supervisor_evidence(self):
        from execution.processes import ProcessHandle,read_outcome
        class Supervisor:
            parent_lease_fd=None
            def __init__(self,code):self.returncode=code
            def wait(self,**kwargs):return self.returncode
        class UnfinishedCapture:
            def join(self,**kwargs):pass
            def is_alive(self):return True
        original={'schema':1,'execution_id':'a'*32,'status':'EXITED','returncode':0,'started_at':1.,'finished_at':2.}
        raw=json.dumps(original,indent=2).encode()+b'\n'
        for case in ['supervisor_death','unfinished_capture','admission_mismatch','capture_error','normal']:
            with self.subTest(case=case):
                receipt=self.root/(case+'.json');receipt.write_bytes(raw)
                handle=ProcessHandle(receipt,'a'*32,2,100)
                handle.supervisor=Supervisor(-9 if case=='supervisor_death' else 0)
                if case=='unfinished_capture':handle._threads=[UnfinishedCapture()]
                if case=='admission_mismatch':handle.admission={'policy_id':'expected','boundary':'non-detaching-process-group','command_sha256':'b'*64}
                if case=='capture_error':handle._capture_errors.add('stdout')
                result=handle.wait();durable=read_outcome(receipt,'a'*32)
                self.assertEqual('EXITED' if case=='normal' else 'INTERRUPTED',result['status'])
                self.assertEqual((result['status'],result['returncode']),(durable['status'],durable['returncode']))
                if case=='normal':self.assertEqual(raw,receipt.read_bytes())
                else:
                    backup=receipt.parent/result['supervisor_evidence']['reference']
                    self.assertEqual(raw,backup.read_bytes());self.assertEqual(durable['supervisor_evidence'],result['supervisor_evidence'])
                    self.assertEqual(result,handle.wait())
        receipt=self.root/'durable-failure.json';receipt.write_bytes(raw)
        handle=ProcessHandle(receipt,'a'*32,2,100);handle.supervisor=Supervisor(-9)
        with patch('execution.processes.write_receipt',side_effect=OSError('fixture durable write failure')):
            with self.assertRaises(OSError):handle.wait()
        self.assertEqual(raw,receipt.read_bytes())
        self.assertEqual(raw,receipt.with_name(receipt.name+'.supervisor.json').read_bytes())
        self.assertEqual('INTERRUPTED',read_outcome(receipt,'a'*32)['status'])
