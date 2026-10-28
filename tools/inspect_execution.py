#!/usr/bin/env python3
"""Inspect local history/recovery or create/restore an audit copy; never launches agents."""
import argparse
import json
import sqlite3

from execution.core import ROOT, Blocked,stable
from execution.history import recovery_status, timeline, verify_evidence
from execution.audit_backup import backup, checked, restore, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('timeline', 'recovery', 'verify-history', 'backup', 'verify-backup', 'restore-audit','recovery-plan','notifications','notification-sync','notification-deliver','notification-ack','notification-diagnose'))
    parser.add_argument('--audit-dir', default=str(ROOT / '.execution'))
    parser.add_argument('--task')
    parser.add_argument('--destination')
    parser.add_argument('--incident')
    parser.add_argument('--actor')
    parser.add_argument('--retry',action='store_true')
    parser.add_argument('--plan',help='Relative proposal inside audit-dir; default-deny dry-run only')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--require-independent-checkpoint',action='store_true',help='Fail closed unless a separately qualified independent reader is configured; no destination is qualified by this CLI')
    args = parser.parse_args()
    try:
        directory = checked(args.audit_dir)
        if args.action.startswith('notification'):
            from execution.notifications import Notifications,_actor
            if args.action=='notifications':result=Notifications(directory,create=False).view()
            else:
                if not args.execute:raise Blocked('Notification mutation requires explicit --execute')
                store=Notifications(directory)
                if args.action=='notification-sync':result=store.reconcile()
                elif args.action=='notification-ack':result=store.acknowledge(args.incident,actor=args.actor)
                elif args.action=='notification-deliver':
                    presented=[]
                    result=store.deliver(args.incident,lambda payload,key:presented.append({'incident_id':key,'payload':payload}),actor=args.actor,retry=args.retry)
                    result['local_presentation']=presented
                else:
                    _actor(args.actor)
                    if args.plan:
                        from execution.audit_paths import evidence_path
                        from execution.recovery_plans import dry_run
                        from execution.notifications import record_recovery_result
                        proposal=json.loads(evidence_path(directory,args.plan).read_text());decision=dry_run(proposal)
                        source=record_recovery_result(directory,decision,{'command':'explicit-recovery-diagnosis','plan_sha256':stable(proposal)})
                        result={'status':'DIAGNOSTIC_RECORDED','kind':'RECOVERY_REJECTED','source_id':source,'meaning':'Explicit denial diagnostic; no recovery authorized or applied'}
                    else:
                        try:verify_evidence(directory);result={'status':'VERIFIED','meaning':'No mismatch notification created'}
                        except (Blocked,OSError,ValueError,KeyError,sqlite3.Error) as error:
                            source=store.record('HISTORY_MISMATCH',{'inspection':'verify-history','reason_sha256':stable(str(error))},evidence={'verified':False,'error_type':type(error).__name__},evidence_state='UNVERIFIED_DIAGNOSTIC')
                            result={'status':'DIAGNOSTIC_RECORDED','source_id':source,'meaning':'History remains unverified; run explicit notification-sync'}
        elif args.action == 'recovery-plan':
            if args.execute:raise Blocked('Recovery plan application is not available')
            if not args.plan:raise Blocked('Recovery proposal reference required')
            from execution.audit_paths import evidence_path
            from execution.recovery_plans import dry_run
            proposal=json.loads(evidence_path(directory,args.plan).read_text());result=dry_run(proposal)

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
