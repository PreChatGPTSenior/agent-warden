"""POSIX supervision using live anchors and exclusive owner pipes, never saved PIDs."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time


def write_receipt(path, value):
    """Private atomic outcome; command, environment and raw output are never included."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.process-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            json.dump(value, stream); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def launch(argv, *, cwd, env, timeout, receipt=None, execution_id=None, started_at=None, admission=None):
    """The coordinator alone owns this write end, including across SIGKILL."""
    if os.name != 'posix': raise OSError('Invocation supervision requires POSIX process groups')
    read_fd, write_fd = os.pipe()
    try:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).absolute()), 'supervise', str(read_fd), str(timeout),
             str(receipt) if receipt else '', execution_id or '',
             str(started_at if started_at is not None else time.time()), json.dumps(admission or {}), *argv],
            cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, start_new_session=True, pass_fds=(read_fd,))
    except BaseException:
        os.close(write_fd); raise
    finally: os.close(read_fd)
    process.parent_lease_fd = write_fd
    return process


def close_lease(process):
    descriptor = getattr(process, 'parent_lease_fd', None)
    if descriptor is not None:
        os.close(descriptor); process.parent_lease_fd = None
        process.wait(timeout=3)


def group_runner(result_fd, owner_fd, argv):
    """An independently watched live group leader survives its command until cleanup."""
    signal.signal(signal.SIGTERM, lambda *_: None)
    signal.signal(signal.SIGINT, lambda *_: None)
    os.set_inheritable(result_fd, False); os.set_inheritable(owner_fd, False)
    child = None
    try:
        try:
            child = subprocess.Popen(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, close_fds=True)
        except OSError:
            os.write(result_fd, b'{"status":"SPAWN_FAILED","returncode":127}\n')
        with selectors.DefaultSelector() as selector:
            selector.register(owner_fd, selectors.EVENT_READ)
            sent = child is None
            while True:
                if selector.select(.03):
                    # The live process signals its own group, so no PID can be reused.
                    os.killpg(os.getpgrp(), signal.SIGTERM)
                    time.sleep(.2)
                    os.killpg(os.getpgrp(), signal.SIGKILL)
                if not sent and child.poll() is not None:
                    code = child.returncode
                    os.write(result_fd, (json.dumps({'status':'EXITED','returncode':code})+'\n').encode())
                    sent = True
    finally:
        os.close(result_fd); os.close(owner_fd)
        # Completion-pipe failures must take exactly the same owned-group cleanup path.
        os.killpg(os.getpgrp(), signal.SIGTERM)
        time.sleep(.2)
        os.killpg(os.getpgrp(), signal.SIGKILL)


def supervise(read_fd, timeout, receipt, execution_id, started_at, admission, argv):
    stopping = False
    def stop(_signal, _frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
    os.set_inheritable(read_fd, False)
    deadline = time.monotonic() + timeout
    anchor = None
    outcome = {'schema':1,'execution_id':execution_id,'status':'INTERRUPTED','returncode':125,
               'started_at':started_at}
    if admission:
        outcome.update(assurance='TRUSTED_COMMAND_PROCESS_GROUP', admission=admission)
    result_read, result_write = os.pipe()
    anchor_read, anchor_write = os.pipe()
    with selectors.DefaultSelector() as selector:
        selector.register(read_fd, selectors.EVENT_READ, 'parent')
        selector.register(result_read, selectors.EVENT_READ, 'result')
        try:
            if stopping or selector.select(0): return 125
            try:
                anchor = subprocess.Popen(
                    [sys.executable, str(Path(__file__).absolute()), 'group', str(result_write), str(anchor_read), *argv],
                    stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr, close_fds=True,
                    start_new_session=True, pass_fds=(result_write, anchor_read))
            except OSError:
                outcome.update(status='ADMISSION_FAILED', returncode=125)
            os.close(result_write); result_write = None
            os.close(anchor_read); anchor_read = None
            while anchor is not None:
                if stopping:
                    outcome.update(status='CANCELLED', returncode=125); break
                if time.monotonic() >= deadline:
                    outcome.update(status='TIMED_OUT', returncode=124); break
                ready = selector.select(.05)
                if any(key.data == 'parent' for key, _ in ready): break
                if any(key.data == 'result' for key, _ in ready):
                    value = os.read(result_read, 4096)
                    if value:
                        outcome.update(json.loads(value))
                    break
        finally:
            if anchor is not None:
                # This unreaped anchor owns the group for the entire signal sequence.
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try: os.killpg(anchor.pid, sig)
                    except ProcessLookupError: pass
                    if sig == signal.SIGTERM: time.sleep(.2)
                anchor.wait()
            for descriptor in (read_fd, result_read, result_write, anchor_read, anchor_write):
                if descriptor is not None: os.close(descriptor)
            if receipt:
                outcome['finished_at'] = time.time()
                write_receipt(receipt, outcome)
    code = outcome['returncode']
    return 128 - code if code < 0 else code


if __name__ == '__main__':
    if sys.argv[1] == 'group': group_runner(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:])
    else: raise SystemExit(supervise(int(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5],
                                    float(sys.argv[6]), json.loads(sys.argv[7]), sys.argv[8:]))
