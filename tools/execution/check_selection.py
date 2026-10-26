"""Trusted check selection. Candidate data never defines its own enforcement policy."""
from pathlib import Path
import fnmatch
import stat
from .core import ROOT, Blocked, identity, safe, sha, stable

# Rules belong to this installed coordinator, never a candidate-imported module.
RULES = (
    ('stone-shelter-api/src/main/java/*.java', ('java',)),
    ('stone-shelter-api/src/test/java/*.java', ('java',)),
    ('stone-shelter-api/pom.xml', ('java', 'maven')),
    ('stone-shelter-api/.mvn/wrapper/maven-wrapper.properties', ('java', 'maven')),
    *((f'stone-shelter-ui/src/*{suffix}', ('react', 'frontend'))
      for suffix in ('.ts', '.tsx', '.js', '.jsx', '.css')),
    ('stone-shelter-ui/package.json', ('react', 'frontend')),
    ('stone-shelter-ui/package-lock.json', ('react', 'frontend')),
    ('stone-shelter-ui/tsconfig.json', ('react', 'frontend')),
    ('stone-shelter-ui/vite.config.js', ('react', 'frontend')),
    ('infra/compose.yaml', ('compose',)),
    *((f'{folder}/{filename}', ('compose',))
      for folder in ('stone-shelter-api', 'stone-shelter-ui', 'infra/minio')
      for filename in ('Dockerfile', '.dockerignore')),
    ('execution/runtime-lock.json', ('runtime',)),
    ('package.json', ('package', 'dependencies')),
    ('package-lock.json', ('package', 'dependencies')),
    ('execution/tasks.json', ('package',)),
)

POLICY = ('quality/static-analysis/*', 'tools/*', 'execution/agent-*.json',
          'execution/prompts/*', '.github/*', 'quality/playwright.config.*',
          'stone-shelter-api/mvnw*', 'stone-shelter-ui/eslint*', 'templates/*')
NON_EXECUTABLE = (
    ('README.md', ('.md',)), ('AGENTS.md', ('.md',)),
    ('START-HERE.md', ('.md',)), ('environment-setup.md', ('.md',)),
    ('docs/*', ('.md',)), ('specs/*', ('.md',)), ('openspec/*', ('.md',)),
    ('stone-shelter-ui/public/*', ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.woff', '.woff2')),
    ('stone-shelter-api/src/main/resources/static/*', ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.woff', '.woff2')),
)


def qualified_non_executable(root, trusted_root, name):
    if not any(fnmatch.fnmatchcase(name, pattern) and Path(name).suffix in suffixes
               for pattern, suffixes in NON_EXECUTABLE):
        return False
    observed = False
    # Cover existing candidate inputs and deletions; never follow a symbolic link.
    for base in {root, trusted_root}:
        try:
            mode = safe(base, name).stat(follow_symlinks=False).st_mode
        except FileNotFoundError:
            continue
        observed = True
        if not stat.S_ISREG(mode) or mode & 0o111:
            raise Blocked('Executable or nonregular input cannot use non-executable allowance: ' + name)
    if not observed:
        raise Blocked('Missing qualified non-executable input: ' + name)
    return True



def checked_root(value):
    path = Path(value).absolute()
    if '..' in path.parts or any(part.lower() == 'engineering-log' for part in path.parts):
        raise Blocked('Protected/unbounded candidate root')
    for parent in (*reversed(path.parents), path):
        if parent.is_symlink():
            raise Blocked('Symlink candidate root')
    return path


def select_checks(candidate_root, candidate, changed, *, trusted_root=ROOT, release=False):
    root = checked_root(candidate_root)
    trusted_root = checked_root(trusted_root)
    paths = sorted(set(changed))
    required = {'java', 'react', 'frontend', 'maven', 'compose', 'runtime', 'package'} if release else set()
    for name in paths:
        safe(root, name)  # lexical protected-name check precedes metadata
        if name == 'package.json':
            import json
            proposed = json.loads(safe(root, name).read_text())
            trusted = json.loads(safe(trusted_root, name).read_text())
            scripts, candidate_scripts = trusted.get('scripts', {}), proposed.get('scripts', {})
            if any(candidate_scripts.get(key) != scripts.get(key)
                   for key in set(scripts) | set(candidate_scripts)
                   if key == 'check' or key.startswith(('check:', 'precheck', 'postcheck'))):
                raise Blocked('Enforcement script change requires independent qualification: ' + name)
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in POLICY):
            original, proposed = safe(trusted_root, name), safe(root, name)
            if not original.is_file() or not proposed.is_file() or sha(original) != sha(proposed):
                raise Blocked('Enforcement policy change requires independent qualification: ' + name)
            required.add('package')
            continue
        families = {family for pattern, checks in RULES if fnmatch.fnmatchcase(name, pattern) for family in checks}
        if not families and not qualified_non_executable(root, trusted_root, name):
            raise Blocked('Unmapped executable configuration: ' + name)
        required.update(families)
    if identity(root) != candidate:
        raise Blocked('Candidate identity differs from check plan')
    return {'schema': 1, 'candidate': candidate, 'candidate_root': str(root),
            'trusted_root': str(trusted_root), 'selector_sha256': sha(Path(__file__)),
            'policy_sha256': stable({'rules': RULES, 'policy': POLICY, 'non_executable': NON_EXECUTABLE}),
            'changed_paths': paths, 'checks': sorted(required)}
