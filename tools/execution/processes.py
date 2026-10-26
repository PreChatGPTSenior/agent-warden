"""Trusted-command process-group supervision; no containment of hostile commands.

Only trusted coordinator policy may call admit_command after review establishing
that the exact command does not detach, daemonize or create another group/session.
The opaque in-process approval is not accepted from worker dictionaries or booleans.
This API binds that caller-supplied approval; policy integration belongs to T0010-009.

Output sanitization masks exact configured values and nonempty environment values
whose names contain TOKEN, SECRET, PASSWORD, PASSWD, CREDENTIAL, API_KEY,
ACCESS_KEY or PRIVATE_KEY. It masks boundary-spanning values and partial suffixes
before capture truncation. It does not claim detection of unknown/encoded secrets.
"""
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import uuid
from .supervision import launch, close_lease, write_receipt

TERMINAL = {'EXITED','SPAWN_FAILED','ADMISSION_FAILED','TIMED_OUT','CANCELLED','INTERRUPTED'}
BOUNDARY = 'non-detaching-process-group'
ASSURANCE = 'TRUSTED_COMMAND_PROCESS_GROUP'
_ADMISSION_SEAL = object()
_SECRET_NAME = re.compile(r'TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|API_KEY|ACCESS_KEY|PRIVATE_KEY', re.I)


@dataclass(frozen=True, repr=False)
class _CommandAdmission:
    argv: tuple
    cwd: str
    policy_id: str
    seal: object


def _command(argv, cwd):
    if (not isinstance(argv,(list,tuple)) or not argv
            or not all(isinstance(a,str) and a and '\0' not in a for a in argv)):
        raise ValueError('Explicit command argv required')
    return tuple(argv), str(Path(cwd).resolve(strict=True))


def admit_command(argv, cwd, *, policy_id):
    """Trusted coordinator only: approve one reviewed non-detaching command/cwd.

    policy_id identifies the caller's reviewed policy decision, not worker evidence.
    No command is automatically reviewed or qualified by calling this function.
    """
    if not isinstance(policy_id,str) or not policy_id.strip():
        raise ValueError('Trusted coordinator policy identity required')
    argv, cwd = _command(argv, cwd)
    return _CommandAdmission(argv, cwd, policy_id, _ADMISSION_SEAL)


def _approval(admission, argv, cwd):
    if not isinstance(admission,_CommandAdmission) or admission.seal is not _ADMISSION_SEAL:
        raise ValueError('Trusted coordinator command admission required')
    argv, cwd = _command(argv, cwd)
    if admission.argv != argv or admission.cwd != cwd:
        raise ValueError('Command or working directory differs from trusted admission')
    binding = {'argv':list(argv),'cwd':cwd,'policy_id':admission.policy_id,'boundary':BOUNDARY}
    proof = {'policy_id':admission.policy_id,'boundary':BOUNDARY,
             'command_sha256':hashlib.sha256(json.dumps(binding,sort_keys=True).encode()).hexdigest()}
    return cwd, proof


def read_outcome(receipt, execution_id=None):
    """A terminal record is evidence of an outcome, never semantic stage approval."""
    try:
        path = Path(receipt)
        value = json.loads(path.read_text())
        if not isinstance(value,dict): raise ValueError('Invalid record')
        backup = path.with_name(path.name+'.supervisor.json')
        preserved = value.get('supervisor_evidence')
        if backup.is_symlink(): raise ValueError('Invalid supervisor evidence')
        if backup.exists() or preserved is not None:
            # Creating the backup is also a finalization intent: an interrupted
            # write cannot leave the old EXITED classification usable as final.
            if (not isinstance(preserved,dict) or preserved.get('reference') != backup.name
                    or preserved.get('sha256') != hashlib.sha256(backup.read_bytes()).hexdigest()):
                raise ValueError('Unfinished final classification or changed supervisor evidence')
        status, code = value.get('status'), value.get('returncode')
        identity = value.get('execution_id')
        started, finished = value.get('started_at'), value.get('finished_at')
        valid_times = all(type(t) in (int,float) and math.isfinite(t) and t >= 0 for t in (started,finished))
        valid_code = type(code) is int and -127 <= code <= 255
        if isinstance(status,str):
            if status == 'SPAWN_FAILED': valid_code = type(code) is int and code == 127
            elif status == 'ADMISSION_FAILED': valid_code = type(code) is int and code == 125
            elif status == 'TIMED_OUT': valid_code = type(code) is int and code == 124
            elif status == 'CANCELLED': valid_code = type(code) is int and code == 125
            elif status == 'INTERRUPTED': valid_code = code is None or (type(code) is int and code == 125)
        if (type(value.get('schema')) is int and value['schema'] == 1
                and isinstance(status,str) and status in TERMINAL and 'returncode' in value and valid_code
                and isinstance(identity,str) and re.fullmatch('[0-9a-f]{32}',identity)
                and (execution_id is None or identity == execution_id)
                and valid_times and finished >= started):
            return value
    except (OSError, ValueError, TypeError): pass
    return {'schema':1,'execution_id':execution_id,'status':'INTERRUPTED','returncode':None}


class _Sanitizer:
    def __init__(self, values):
        self.values = sorted(values,key=len,reverse=True)
        self.pending = b''
    def feed(self, chunk, *, final=False):
        if not self.values: return chunk
        self.pending += chunk
        output = bytearray()
        while self.pending:
            partial = any(value.startswith(self.pending) and len(value)>len(self.pending) for value in self.values)
            if partial and not final: break
            match = next((value for value in self.values if self.pending.startswith(value)),None)
            if match is not None:
                output.extend(b'[REDACTED]'); self.pending = self.pending[len(match):]
            elif partial:
                output.extend(b'[REDACTED]'); self.pending = b''
            else:
                output.append(self.pending[0]); self.pending = self.pending[1:]
        return bytes(output)


def _sensitive_values(env, configured):
    if not isinstance(configured,(list,tuple)) or not all(isinstance(v,str) and v for v in configured):
        raise ValueError('Explicit sensitive values must be nonempty strings')
    values = {v.encode('utf-8') for v in configured}
    values.update(value.encode('utf-8') for name,value in env.items() if value and _SECRET_NAME.search(name))
    if len(values)>128 or any(len(value)>4096 for value in values):
        raise ValueError('Sanitization policy exceeds bounded capture limits')
    return values


class ProcessHandle:
    def __init__(self, receipt, execution_id, timeout, output_limit, *, sensitive_values=(), admission=None, started_at=None):
        self.receipt = Path(receipt)
        self.execution_id = execution_id
        self.timeout = timeout
        self.output_limit = output_limit
        self.admission = admission
        self.started_at = started_at if started_at is not None else time.time()
        self.supervisor = None
        self._threads = []
        self._output = {'stdout':bytearray(),'stderr':bytearray()}
        self._truncated = {'stdout':False,'stderr':False}
        self._sanitizers = {name:_Sanitizer(sensitive_values) for name in self._output}
        self._capture_errors = set()
        self._result = None
    def _capture(self, name, chunk):
        room = self.output_limit - len(self._output[name])
        self._output[name].extend(chunk[:room])
        if len(chunk)>room: self._truncated[name] = True
    def _drain(self, name, stream):
        try:
            while True:
                chunk = os.read(stream.fileno(),8192)
                if not chunk: break
                self._capture(name,self._sanitizers[name].feed(chunk))
            self._capture(name,self._sanitizers[name].feed(b'',final=True))
        except Exception:
            # Error text can contain private output or paths; record the channel only.
            self._capture_errors.add(name)
        finally:
            try: stream.close()
            except Exception: self._capture_errors.add(name)
    def _persist_interruption(self, result):
        try: original = self.receipt.read_bytes()
        except FileNotFoundError: original = b''
        backup = self.receipt.with_name(self.receipt.name+'.supervisor.json')
        try:
            descriptor = os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:
            if backup.is_symlink() or backup.read_bytes() != original:
                raise OSError('Supervisor evidence preservation conflict')
        else:
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(original); stream.flush(); os.fsync(stream.fileno())
            directory_fd = os.open(backup.parent,os.O_RDONLY)
            try: os.fsync(directory_fd)
            finally: os.close(directory_fd)
        result.update(schema=1,execution_id=self.execution_id,
                      supervisor_evidence={'reference':backup.name,'sha256':hashlib.sha256(original).hexdigest()})
        result.setdefault('started_at',self.started_at)
        result['finished_at'] = max(time.time(),result['started_at'])
        # Failure propagates; no successful/cached result is returned. The retained
        # intent makes read_outcome fail closed until finalization succeeds.
        write_receipt(self.receipt,result)
    def wait(self):
        if self._result is not None: return dict(self._result)
        if self.supervisor is not None:
            try: self.supervisor.wait(timeout=self.timeout + 3)
            except subprocess.TimeoutExpired:
                self.supervisor.terminate()
                try: self.supervisor.wait(timeout=2)
                except subprocess.TimeoutExpired: self.supervisor.kill(); self.supervisor.wait(timeout=2)
            close_lease(self.supervisor)
            for thread in self._threads: thread.join(timeout=2)
        result = read_outcome(self.receipt,self.execution_id)
        interrupted = ((self.supervisor is not None and self.supervisor.returncode < 0)
                or any(thread.is_alive() for thread in self._threads)
                or (self.admission is not None and (result.get('admission') != self.admission or result.get('assurance') != ASSURANCE))
                or bool(self._capture_errors))
        if interrupted:
            result.update(status='INTERRUPTED',returncode=None)
        if self.admission is not None:
            result.update(assurance=ASSURANCE,admission=self.admission)
        if self._capture_errors:
            result.update(capture_errors=sorted(self._capture_errors))
        if interrupted or (result['status'] == 'INTERRUPTED' and 'finished_at' not in result):
            self._persist_interruption(result)
        for name in self._output:
            result[name] = self._output[name].decode('utf-8',errors='replace')
            result[name+'_truncated'] = self._truncated[name]
        self._result = result
        return dict(result)
    def cancel(self):
        if self.supervisor is not None and self.supervisor.poll() is None: self.supervisor.terminate()
    def close(self):
        self.cancel(); self.wait()


def start(argv, *, cwd, env, timeout, receipt, output_limit=65536, sensitive_values=(), admission=None):
    cwd, proof = _approval(admission,argv,cwd)
    if (type(timeout) not in (int,float) or not math.isfinite(timeout) or timeout<=0
            or type(output_limit) is not int or output_limit<0):
        raise ValueError('Positive finite timeout and nonnegative output limit required')
    if not isinstance(env,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in env.items()):
        raise ValueError('Explicit string environment required')
    env = dict(env)
    values = _sensitive_values(env,sensitive_values)
    path = Path(receipt).absolute()
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.exists() or path.is_symlink(): raise FileExistsError('Process evidence already exists')
    execution_id, started = uuid.uuid4().hex, time.time()
    write_receipt(path,{'schema':1,'execution_id':execution_id,'status':'STARTING','started_at':started,
                        'assurance':ASSURANCE,'admission':proof})
    handle = ProcessHandle(path,execution_id,timeout,output_limit,sensitive_values=values,admission=proof,started_at=started)
    try:
        handle.supervisor = launch(argv,cwd=cwd,env=env,timeout=timeout,receipt=path,execution_id=execution_id,
                                   started_at=started,admission=proof)
    except OSError:
        write_receipt(path,{'schema':1,'execution_id':execution_id,'status':'ADMISSION_FAILED','returncode':125,
                           'started_at':started,'finished_at':time.time(),'assurance':ASSURANCE,'admission':proof})
        return handle
    handle.supervisor.stdin.close()
    for name in ('stdout','stderr'):
        thread = threading.Thread(target=handle._drain,args=(name,getattr(handle.supervisor,name)),daemon=True)
        handle._threads.append(thread); thread.start()
    return handle
