"""Verified audit copies into new directories; never restores an active coordinator in place."""
from contextlib import closing, contextmanager
import fcntl
import os
from pathlib import Path
import shutil
import sqlite3
import time

from .core import Blocked, json_read, json_write, safe, sha
from .history import verify_evidence
from .audit_paths import DATABASES, TREES, LEAVES, PROTECTED_NAMES, secret_path


def checked(path):
    path = Path(path).absolute()
    # Reject protected components before checking any metadata, including ancestors.
    return safe(Path(path.anchor), str(path.relative_to(path.anchor)))


@contextmanager
def idle(directory):
    directory = checked(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with safe(directory, 'coordinator.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error: raise Blocked('Coordinator is active; stop it before audit backup/restore') from error
        yield


def walk(folder, *, reject_secrets=False):
    with os.scandir(folder) as entries:
        for entry in sorted(entries, key=lambda row: row.name):
            if entry.name.lower() in PROTECTED_NAMES: continue
            if secret_path((entry.name,)):
                if reject_secrets: raise Blocked('Audit copy contains an excluded secret path; re-export from preserved source')
                continue
            if entry.is_symlink(): raise Blocked('Audit backup rejects symlinks')
            if entry.is_dir(follow_symlinks=False): yield from walk(Path(entry.path), reject_secrets=reject_secrets)
            elif entry.is_file(follow_symlinks=False): yield Path(entry.path)


def database_check(path):
    with closing(sqlite3.connect(Path(path).absolute().as_uri() + '?mode=ro', uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise Blocked('Corrupt audit database')


def copy_private(source, target):
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copyfile(source, target); os.chmod(target, 0o600)
    with target.open('rb') as stream: os.fsync(stream.fileno())
    parent = os.open(target.parent, os.O_RDONLY)
    try: os.fsync(parent)
    finally: os.close(parent)


def verify(directory):
    directory = checked(directory)
    manifest = json_read(safe(directory, 'manifest.json'))
    if manifest.get('schema') != 1 or not isinstance(manifest.get('files'), dict):
        raise Blocked('Invalid audit manifest')
    # Also refuse secret files omitted from the manifest, without reading their bytes.
    for _ in walk(directory, reject_secrets=True):
        pass
    for name, digest in manifest['files'].items():
        parts = Path(name).parts
        if secret_path(parts): raise Blocked('Audit manifest contains an excluded secret path')
        path = safe(directory, name)
        if not parts or (parts[0] not in TREES and name not in DATABASES + LEAVES):
            raise Blocked('Unapproved audit artifact path')
        if not path.is_file() or sha(path) != digest: raise Blocked('Missing or changed audit artifact: ' + name)
        if name in DATABASES: database_check(path)
    verify_evidence(directory)
    return manifest


def backup(directory, destination):
    directory, destination = checked(directory), checked(destination)
    if destination == directory or directory in destination.parents:
        raise Blocked('Audit backup must be outside the active execution directory')
    if destination.exists(): raise Blocked('Backup destination must be new')
    with idle(directory):
        verify_evidence(directory)
        destination.mkdir(parents=True, mode=0o700)
        paths = []
        for name in DATABASES:
            source = safe(directory, name)
            if not source.exists(): continue
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as db, \
                    closing(sqlite3.connect(destination / name)) as target:
                db.backup(target)
            os.chmod(destination / name, 0o600)
            database_check(destination / name)
            paths.append(name)
        sources = [safe(directory, name) for name in LEAVES if safe(directory, name).exists()]
        for name in TREES:
            folder = safe(directory, name)
            if folder.exists(): sources.extend(walk(folder))
        for source in sources:
            name = str(source.relative_to(directory)); target = safe(destination, name)
            copy_private(source, target); paths.append(name)
        manifest = {'schema': 1, 'created_at_epoch': time.time(), 'source': str(directory),
                    'scope': 'Audit databases and evidence only; excludes environment/credential/key files, Git/worktrees, app volumes and model context',
                    'files': {name: sha(destination / name) for name in paths}}
        json_write(destination / 'manifest.json', manifest)
        verify(destination)
        return manifest


def restore(source, destination):
    source, destination = checked(source), checked(destination)
    manifest = verify(source)
    if destination.exists(): raise Blocked('Restore target must be new; active state is never overwritten')
    destination.mkdir(parents=True, mode=0o700)
    for name in manifest['files']:
        target = safe(destination, name)
        copy_private(safe(source, name), target)
    json_write(destination / 'manifest.json', manifest)
    verify(destination)
    return {'status': 'AUDIT_RESTORED', 'destination': str(destination), 'files': len(manifest['files']),
            'execution_resumed': False}
