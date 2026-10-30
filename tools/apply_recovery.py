#!/usr/bin/env python3
"""Default-deny recovery dry-run; files cannot install trusted host authority."""
import argparse
import json
from execution.core import ROOT,Blocked
from execution.audit_backup import checked
from execution.audit_paths import evidence_path
from execution.recovery_plans import apply_plan

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-dir',default=str(ROOT/'.execution'))
    parser.add_argument('--plan',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    directory=None;plan=None;attempted=False
    try:
        directory=checked(args.audit_dir)
        plan=json.loads(evidence_path(directory,args.plan).read_text())
        attempted=args.execute
        result=apply_plan(directory,plan,execute=args.execute)
    except (Blocked,OSError,ValueError):
        result=({'status':'RECONCILIATION_REQUIRED','reason':'RECOVERY_OUTCOME_UNAVAILABLE','applied':None,'effects_possible':True}
                if attempted else {'status':'BLOCKED','reason':'PROPOSAL_OR_AUTHORITY_UNAVAILABLE','applied':False})
    # Dry-run remains read-only. A notification failure cannot replace a known
    # recovery outcome or turn possibly committed effects into applied:false.
    if args.execute and directory is not None and result.get('status') in ('BLOCKED','RECONCILIATION_REQUIRED'):
        try:
            from execution.notifications import record_recovery_result
            from execution.core import stable
            record_recovery_result(directory,result,{'command':'apply-recovery','plan_sha256':stable(plan)})
        except Exception:
            result={**result,'notification':{'status':'FAILED','reason':'NOTIFICATION_PERSISTENCE_UNAVAILABLE'}}
    print(json.dumps(result,indent=2));return 0 if result['status'] in ('DRY_RUN_VALIDATED','COMPLETED') else 2

if __name__=='__main__':raise SystemExit(main())
