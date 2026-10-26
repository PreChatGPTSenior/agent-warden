"""Bounded audit path policy; inspect names before any protected/secret metadata."""
import os
from pathlib import Path

from .core import safe

DATABASES = ('state.sqlite', 'budgets.sqlite', 'trace.sqlite')
TREES = ('runs', 'model-preflight', 'batches', 'versions')
LEAVES = ('usage.jsonl', 'policy.json', 'result.json', 'budget-stop.json', 'execution-identity.json')
PROTECTED_NAMES = {'engineering-log', '.git'}
SECRET_NAMES = {'secrets', '.secrets', 'credentials', '.credentials', '.ssh',
                'credentials.json', 'credentials.toml', 'auth.json', 'auth.toml',
                'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519'}


def secret_path(parts):
    """A path exclusion, not content redaction or a claim that logs contain no secrets."""
    for part in parts:
        name = part.lower()
        if (name in SECRET_NAMES or name.startswith('.env') or name.endswith('.env')
                or '.env.' in name or name.endswith(('.key', '.pem', '.p12', '.pfx'))):
            return True
    return False


def retained_artifacts(directory):
    """Detect prior execution without reading files or recursively walking worktrees."""
    directory = Path(directory)
    if any(safe(directory, name).exists() for name in LEAVES if name!='execution-identity.json'):
        return True
    for name in DATABASES:
        if not safe(directory, name).exists():
            if any(safe(directory, name + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
                return True
    for name in TREES + ('worktrees', 'integration'):
        folder = safe(directory, name)
        if not folder.exists():
            continue
        # A malformed non-directory is also retained evidence, never a fresh start.
        if not folder.is_dir():
            return True
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name.lower() in PROTECTED_NAMES:
                    continue
                # Even an empty attempt directory or a secret file signals prior work.
                # Do not stat/follow the entry or read its content.
                return True
    return False


def evidence_path(root, reference):
    """Resolve only a relative artifact inside an explicitly trusted attempt root."""
    from .core import Blocked
    from .check_selection import checked_root
    if not isinstance(reference, str): raise Blocked('Invalid evidence reference')
    path = Path(reference)
    if (not path.parts or path.is_absolute() or '..' in path.parts
            or any(part.lower() in PROTECTED_NAMES for part in path.parts)
            or secret_path(path.parts)):
        raise Blocked('Unsafe relative evidence reference')
    return safe(checked_root(root), reference)


def public_artifacts(directory):
    """Inventory only admitted evidence trees, pruning protected/secret names first."""
    from .core import Blocked
    from .check_selection import checked_root
    root=checked_root(directory)
    def walk(folder):
        with os.scandir(folder) as rows:
            for row in rows:
                if row.name.lower() in PROTECTED_NAMES or secret_path((row.name,)):continue
                if row.is_symlink():raise Blocked('Symlink retained artifact')
                if row.is_dir(follow_symlinks=False):yield from walk(Path(row.path))
                elif row.is_file(follow_symlinks=False):yield Path(row.path)
    if not root.exists():return
    operational=set(DATABASES)|{'execution-identity.json','usage.jsonl','coordinator.lock','manifest.json','worktrees','integration'}
    operational.update(name+suffix for name in DATABASES for suffix in ('-wal','-shm','-journal'))
    with os.scandir(root) as rows:
        for row in rows:
            if row.name.lower() in PROTECTED_NAMES or secret_path((row.name,)):continue
            if row.name in operational:continue
            if row.is_symlink():raise Blocked('Symlink root artifact')
            if row.name in TREES:
                if not row.is_dir(follow_symlinks=False):raise Blocked('Malformed retained evidence tree')
                yield from walk(Path(row.path))
            elif row.is_file(follow_symlinks=False):yield Path(row.path)
            else:raise Blocked('Unapproved root evidence entry: '+row.name)
