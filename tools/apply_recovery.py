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
    try:
        directory=checked(args.audit_dir)
        plan=json.loads(evidence_path(directory,args.plan).read_text())
        result=apply_plan(directory,plan,execute=args.execute)
    except (Blocked,OSError,ValueError):result={'status':'BLOCKED','reason':'PROPOSAL_OR_AUTHORITY_UNAVAILABLE','applied':False}
    print(json.dumps(result,indent=2));return 0 if result['status'] in ('DRY_RUN_VALIDATED','COMPLETED') else 2

if __name__=='__main__':raise SystemExit(main())
