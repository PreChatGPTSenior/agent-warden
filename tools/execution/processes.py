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
from .core import Blocked

TERMINAL = {'EXITED','SPAWN_FAILED','ADMISSION_FAILED','TIMED_OUT','CANCELLED','INTERRUPTED'}
BOUNDARY = 'non-detaching-process-group'
ASSURANCE = 'TRUSTED_COMMAND_PROCESS_GROUP'
_ADMISSION_SEAL = object()
_COMMAND_LOCK = threading.RLock()
_OWNED_COMMANDS = {}
FINALIZATION_WAIT_SECONDS = 2.0


class FinalizationPending(Blocked):
    def __init__(self, handle):
        super().__init__('Current owner is finalizing; completion must be revalidated')
        self.handle = handle
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
        self.creator_pid = os.getpid()
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
        self._wait_lock = threading.Lock()
        self._wait_started = threading.Event()
        self._wait_done = threading.Event()
        self._wait_error = False
        self._finalizer_lock = threading.Lock()
        self._finalizer = None
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
        # Per-handle serialization prevents independent admission and the owner
        # from reaping/closing the same lease concurrently. Never a global lock.
        with self._wait_lock:
            self._wait_started.set()
            self._wait_done.clear()
            self._wait_error = False
            try:return self._finish()
            except BaseException:
                self._wait_error = True
                raise
            finally:self._wait_done.set()

    def finish_for_admission(self, timeout):
        """Await attributable completion outside admission, with one bounded deadline.

        If the supervisor exits before its caller invokes wait(), this handle
        owns the finalizer too. Completion notification is never approval: the
        caller must revalidate safe journal, capture and terminal evidence.
        """
        if self.creator_pid!=os.getpid() or self._wait_error:return False
        with self._finalizer_lock:
            if not self._wait_started.is_set() and self._finalizer is None:
                def finish():
                    try:self.wait()
                    except BaseException:pass  # _wait_error retains uncertainty.
                self._finalizer=threading.Thread(target=finish,daemon=True)
                self._finalizer.start()
        return self._wait_done.wait(timeout)

    def _finish(self):
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
    def verified_completion_pending(self, receipt):
        """Recognize this current owner's fully checked normal result, never reap here.

        wait() caches only after supervisor reaping, lease closure and complete
        capture validation. The durable receipt must still match that exact
        cached evidence; an exited process alone supplies no such permission.
        """
        result=self._result
        if (self.creator_pid!=os.getpid() or not isinstance(result,dict)
                or self.supervisor is None or self.supervisor.poll()!=0
                or getattr(self.supervisor,'parent_lease_fd',None) is not None
                or self._capture_errors or any(thread.is_alive() for thread in self._threads)
                or result.get('status')!='EXITED' or result.get('returncode')!=0
                or result.get('capture_errors') or result.get('execution_id')!=self.execution_id):
            return False
        actual=read_outcome(receipt,self.execution_id)
        return (actual.get('status')=='EXITED' and actual.get('returncode')==0
                and actual.get('assurance')==ASSURANCE and actual.get('admission')==self.admission
                and all(key in result and result[key]==value for key,value in actual.items()))

    def cancel(self):
        if self.supervisor is not None and self.supervisor.poll() is None: self.supervisor.terminate()
    def close(self):
        self.cancel(); self.wait()


class ProcessSetupFailure(Blocked):
    """An already-owned launch failed adapter setup; its usage remains uncertain."""
    def __init__(self, handle):
        super().__init__('Postlaunch process setup failed; reconciliation required')
        self.handle = handle
        self.may_have_started = True
        self.cleanup_completed = False


def _cleanup_setup_failure(failure):
    errors = []
    try: failure.handle.cancel()
    except BaseException: errors.append('cancellation')
    try: failure.handle.wait()
    except BaseException: errors.append('reaping/evidence')
    for channel in ('stdin','stdout','stderr'):
        try: getattr(failure.handle.supervisor,channel).close()
        except (AttributeError,OSError,ValueError): pass
    failure.cleanup_completed = not errors


def start(argv, *, cwd, env, timeout, receipt, output_limit=65536, sensitive_values=(), admission=None, external_stream=False, _failure_owner=None):
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
    try:
        if external_stream:
            return handle
        handle.supervisor.stdin.close()
        for name in ('stdout','stderr'):
            thread = threading.Thread(target=handle._drain,args=(name,getattr(handle.supervisor,name)),daemon=True)
            thread.start()
            handle._threads.append(thread)
        return handle
    except BaseException as error:
        failure = ProcessSetupFailure(handle)
        failure.__cause__ = error
        if _failure_owner is not None:
            # Core already owns the durable intent and transfers this exact
            # handle to its outer cleanup boundary after releasing admission.
            _failure_owner(failure)
        _cleanup_setup_failure(failure)
        raise failure from error


class CommandJournal:
    """Durable local causal records. Unfinished side effects require operator reconciliation.

    This is retained local evidence, not an independently anchored audit store.
    No automatic replay or repair is performed by the command service.
    """
    def __init__(self, root):
        from .check_selection import checked_root
        from .history import History
        self.root = checked_root(root)
        if self.root.name != 'commands' or self.root.parent.name != '.execution':
            raise ValueError('Command journal requires the retained commands namespace')
        self.history = History(self.root.parent/'trace.sqlite')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    def write(self, action_id, value):
        if not re.fullmatch(r'[a-zA-Z0-9-]+', action_id):
            raise ValueError('Invalid command action identity')
        from .check_selection import checked_root
        checked_root(self.root/'processes')
        # The supervisor owns the live receipt. Register only its final bytes;
        # publishing a STARTING snapshot could overwrite a racing terminal write.
        receipts=(self.root/'processes').glob(action_id+'.process.json*') if value.get('events', [{}])[-1].get('event')=='outcome' else ()
        for path in receipts:
            if path.is_symlink(): raise ValueError('Symlink process evidence')
            self.history.write_artifact('commands/processes/'+path.name,path.read_bytes(),
                                       trace=value.get('parent_action'),task=value.get('task'))
        self.history.write_artifact('commands/'+action_id+'.json',value,
                                   trace=value.get('parent_action'),task=value.get('task'))
        directory = os.open(self.root, os.O_RDONLY)
        try: os.fsync(directory)
        finally: os.close(directory)
    def require_reconciled(self):
        """Validate safe indexed evidence before using current-process ownership.

        The registry is an in-memory lifetime handle, never a persisted PID,
        worker assertion or restart permission. A restored record has no lease.
        """
        from .core import Blocked, sha
        from .history import timeline
        from .audit_paths import evidence_path
        from .check_selection import checked_root
        published, staging = {}, {}
        for event in timeline(self.history.path):
            payload=event['payload']
            reference=payload.get('reference','')
            if not isinstance(reference,str) or not reference.startswith('commands/'):continue
            if event['event']=='artifact.staging':
                staging[event['event_id']]=event
            elif event['event']=='artifact.completed':
                intent=staging.pop(payload.get('staging_event_id'),None)
                if (not intent or any(payload.get(key)!=intent['payload'].get(key)
                        for key in ('reference','version_reference','sha256'))
                        or event['task']!=intent['task'] or event['trace']!=intent['trace']):
                    raise Blocked('Unregistered command evidence')
                version=payload.get('version_reference','')
                if not version.startswith('versions/'+payload['sha256']+'/'):
                    raise Blocked('Invalid immutable command version')
                version_path=evidence_path(self.root.parent,version)
                if sha(version_path)!=payload['sha256']:raise Blocked('Changed immutable command evidence')
                published[reference]=event
        if staging:raise Blocked('Interrupted command evidence publication; reconciliation required')
        for reference,indexed in published.items():
            retained=evidence_path(self.root.parent,reference)
            if not retained.is_file() or sha(retained)!=indexed['payload']['sha256']:
                raise Blocked('Missing/changed indexed command evidence')
        owned_receipts=set()
        with os.scandir(self.root) as entries:
            for entry in entries:
                # Prune protected names before metadata, including indirect aliases.
                if entry.name.lower()=='engineering-log':continue
                path=evidence_path(self.root,entry.name)
                if entry.name=='processes':
                    checked_root(path)
                    continue
                if not re.fullmatch(r'[0-9a-f]{32}\.json',entry.name):
                    raise Blocked('Unindexed/malformed command evidence')
                action=entry.name[:-5]
                reference='commands/'+entry.name
                indexed=published.get(reference)
                if indexed is None or sha(path)!=indexed['payload']['sha256']:
                    raise Blocked('Unindexed/changed command evidence')
                value=json.loads(path.read_text())
                records=value.get('events',[])
                names=[record.get('event') for record in records]
                if (value.get('schema')!=1 or value.get('action_id')!=action
                        or names not in (['intent','started'],['intent','started','outcome'])
                        or any(record.get('action_id')!=action for record in records)
                        or any(type(record.get('at')) not in (int,float) or not math.isfinite(record['at']) for record in records)
                        or not all(isinstance(value.get(key),str) and value[key].strip()
                                   for key in ('actor','task','parent_action','candidate','cwd','policy'))
                        or indexed['trace']!=value['parent_action'] or indexed['task']!=value['task']):
                    raise Blocked('Invalid command causality; reconciliation required')
                receipt=self.root/'processes'/(action+'.process.json')
                if names==['intent','started']:
                    owned=_OWNED_COMMANDS.get((str(self.root),action))
                    if (isinstance(owned,ProcessHandle) and owned.creator_pid==os.getpid()
                            and owned.receipt==receipt and owned.execution_id==records[1].get('execution_id')
                            and owned.verified_completion_pending(evidence_path(self.root.parent,'commands/processes/'+receipt.name))):
                        owned_receipts.add(receipt.name)
                        continue
                    if (isinstance(owned,ProcessHandle) and owned.creator_pid==os.getpid()
                            and owned.receipt==receipt and owned.execution_id==records[1].get('execution_id')
                            and owned.supervisor is not None and owned.supervisor.poll()==0
                            and owned._result is None and not owned._wait_error and not owned._capture_errors):
                        safe_process=evidence_path(self.root.parent,'commands/processes/'+receipt.name)
                        current=read_outcome(safe_process,owned.execution_id)
                        if (current.get('status')=='EXITED' and current.get('returncode')==0
                                and current.get('assurance')==ASSURANCE and current.get('admission')==owned.admission):
                            raise FinalizationPending(owned)
                    if (isinstance(owned,ProcessHandle) and owned.creator_pid==os.getpid() and owned.receipt==receipt
                            and owned.execution_id==records[1].get('execution_id')
                            and owned.supervisor is not None
                            and owned.supervisor.poll() is None
                            and getattr(owned.supervisor,'parent_lease_fd',None) is not None):
                        safe_process=evidence_path(self.root.parent,'commands/processes/'+receipt.name)
                        current=json.loads(safe_process.read_text())
                        lease=owned.supervisor.parent_lease_fd
                        try:os.fstat(lease)
                        except OSError:raise Blocked('Owned supervisor lease is no longer live')
                        if (current.get('schema')!=1 or current.get('execution_id')!=owned.execution_id
                                or current.get('status') not in {'STARTING','EXITED'}
                                or current.get('assurance')!=ASSURANCE or current.get('admission')!=owned.admission
                                or (current.get('status')=='EXITED' and read_outcome(safe_process,owned.execution_id)['status']!='EXITED')):
                            raise Blocked('Interrupted/foreign live process evidence requires reconciliation')
                        owned_receipts.add(receipt.name)
                        continue
                    raise Blocked('Unfinished command requires observed-state reconciliation')
                process_reference='commands/processes/'+receipt.name
                indexed_process=published.get(process_reference)
                safe_receipt=evidence_path(self.root.parent,process_reference)
                if indexed_process is None or sha(safe_receipt)!=indexed_process['payload']['sha256']:
                    raise Blocked('Missing/changed indexed process outcome')
                actual=read_outcome(safe_receipt,records[1].get('execution_id'))
                outcome=records[-1].get('outcome',{})
                if (actual['status']=='INTERRUPTED'
                        or (value.get('side_effect') and actual['status']!='EXITED')
                        or any(actual.get(key)!=outcome.get(key) for key in ('execution_id','status','returncode'))):
                    raise Blocked('Interrupted command requires observed-state reconciliation')
        receipts=checked_root(self.root/'processes')
        if receipts.exists():
            with os.scandir(receipts) as entries:
                for entry in entries:
                    if entry.name.lower()=='engineering-log':continue
                    reference='commands/processes/'+entry.name
                    path=evidence_path(self.root.parent,reference)
                    if reference in published:continue
                    if entry.name in owned_receipts:continue
                    # Atomic live-receipt temporary files are owned only while
                    # an admitted handle in this exact directory holds its lease.
                    if owned_receipts and entry.name.startswith('.process-') and path.is_file():continue
                    raise Blocked('Unindexed process evidence requires reconciliation')


class JournalHandle:
    def __init__(self, handle, journal, record):
        self.handle, self.journal, self.record = handle, journal, record
        self.supervisor = handle.supervisor
        self._result = None
    def wait(self):
        if self._result is not None: return dict(self._result)
        result = self.handle.wait()
        record = {**self.record,'events':[*self.record['events'],
                  {'event':'outcome','action_id':self.record['action_id'],'at':time.time(),'outcome':result}]}
        with _COMMAND_LOCK:
            try:self.journal.write(record['action_id'], record)
            finally:_OWNED_COMMANDS.pop((str(self.journal.root),record['action_id']),None)
            self.record = record
            self._result = result
        return dict(result)
    def publish_output_artifacts(self, artifacts):
        with _COMMAND_LOCK:
            record={**self.record,'output_artifacts':dict(artifacts)}
            self.journal.write(record['action_id'],record)
            self.record=record
    def cancel(self): self.handle.cancel()
    def close(self):
        self.cancel()
        return self.wait()
