#!/usr/bin/env python3
"""Inspect local history/recovery or create/restore an audit copy; never launches agents."""
import argparse
import json
import sqlite3

from execution.core import ROOT, Blocked
from execution.history import recovery_status, timeline, verify_evidence
from execution.audit_backup import backup, checked, restore, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('timeline', 'recovery', 'verify-history', 'backup', 'verify-backup', 'restore-audit','recovery-plan'))
    parser.add_argument('--audit-dir', default=str(ROOT / '.execution'))
    parser.add_argument('--task')
    parser.add_argument('--destination')
    parser.add_argument('--plan',help='Relative proposal inside audit-dir; default-deny dry-run only')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--require-independent-checkpoint',action='store_true',help='Fail closed unless a separately qualified independent reader is configured; no destination is qualified by this CLI')
    args = parser.parse_args()
    try:
        directory = checked(args.audit_dir)
        if args.action == 'recovery-plan':
            if args.execute:raise Blocked('Recovery plan application is not available')
            if not args.plan:raise Blocked('Recovery proposal reference required')
            from execution.audit_paths import evidence_path
            from execution.recovery_plans import dry_run
            result=dry_run(json.loads(evidence_path(directory,args.plan).read_text()))
        elif args.action == 'timeline': result = {'events': timeline(directory / 'trace.sqlite', args.task)}
        elif args.action == 'recovery': result = recovery_status(directory,require_checkpoint=args.require_independent_checkpoint)
        elif args.action == 'verify-history':
            result = verify_evidence(directory)
            if args.require_independent_checkpoint:raise Blocked('Independent checkpoint reader unavailable; external assurance unverifiable')
        elif args.action == 'verify-backup': result = {'status': 'VERIFIED', 'manifest': verify(directory)}
        else:
            if not args.execute or not args.destination: raise Blocked('Copy operations require --execute and a new --destination')
            operation = backup if args.action == 'backup' else restore
            result = operation(directory, args.destination)
        print(json.dumps(result, indent=2))
        return 2 if result.get('status') in ('RECOVERY_REQUIRED','BLOCKED') else 0
    except (Blocked, ValueError, OSError, KeyError, sqlite3.Error) as error:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(error)})); return 2


if __name__ == '__main__': raise SystemExit(main())
