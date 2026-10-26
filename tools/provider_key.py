"""Codex credential helper only: stdout is the private auth protocol, never a log."""
import os
import re
import sys

if __name__ == '__main__':
    if len(sys.argv) != 2 or not re.fullmatch(r'[A-Z][A-Z0-9_]*', sys.argv[1]):
        raise SystemExit('Expected an environment-variable name')
    token = os.environ.get(sys.argv[1], '').strip()
    if not token:
        raise SystemExit('Required provider credential is missing')
    # Invoked by Codex internally; do not run this helper manually or redirect its output.
    sys.stdout.write(token)
