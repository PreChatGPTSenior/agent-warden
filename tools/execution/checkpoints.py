"""Read-only independent checkpoint protocol; no production destination is qualified here."""
from .core import Blocked,stable


def checkpoint_record(events,*,sequence,previous=None):
    if not events:raise Blocked('Cannot checkpoint an uninitialized execution')
    execution_id=events[-1].get('execution_id')
    if not execution_id or type(sequence) is not int or sequence<1:raise Blocked('Invalid checkpoint identity/sequence')
    if previous and (previous['execution_id']!=execution_id or sequence!=previous['sequence']+1
                     or events[-1]['seq']<previous['journal_seq']):raise Blocked('Nonmonotonic checkpoint')
    if not previous and sequence!=1:raise Blocked('Checkpoint chain must start at one')
    body={'schema':1,'execution_id':execution_id,'sequence':sequence,'journal_seq':events[-1]['seq'],
          'journal_sha256':events[-1]['sha256'],'previous_checkpoint_sha256':previous['checkpoint_sha256'] if previous else None}
    return {**body,'checkpoint_sha256':stable(body)}


def verify_checkpoint(events,source=None,*,required=False):
    """source is a separately admitted read-only adapter, never a candidate file/flag."""
    if source is None or getattr(source,'admitted',False) is not True:
        if required:raise Blocked('Independent checkpoint unavailable or destination unqualified')
        return {'assurance':'UNVERIFIABLE_EXTERNAL','reason':'No qualified independent checkpoint reader; local consistency cannot detect complete rollback'}
    if not events:raise Blocked('Local history rollback or missing execution identity')
    try:records=source.read(events[-1]['execution_id'])
    except Exception as error:raise Blocked('Independent checkpoint unavailable') from error
    if not isinstance(records,list) or not records:raise Blocked('Independent checkpoint unavailable')
    prior=None;execution_id=events[-1]['execution_id']
    for record in records:
        keys={'schema','execution_id','sequence','journal_seq','journal_sha256','previous_checkpoint_sha256','checkpoint_sha256'}
        if (not isinstance(record,dict) or set(record)!=keys or record['schema']!=1
                or record['execution_id']!=execution_id or type(record['sequence']) is not int
                or type(record['journal_seq']) is not int or record['journal_seq']<1
                or record['checkpoint_sha256']!=stable({k:v for k,v in record.items() if k!='checkpoint_sha256'})
                or record['sequence']!=(prior['sequence']+1 if prior else 1)
                or record['previous_checkpoint_sha256']!=(prior['checkpoint_sha256'] if prior else None)
                or (prior and record['journal_seq']<prior['journal_seq'])):
            raise Blocked('Foreign, forked or nonmonotonic independent checkpoint')
        if record['journal_seq']>len(events):raise Blocked('Local history rollback detected against independent checkpoint')
        if events[record['journal_seq']-1]['sha256']!=record['journal_sha256']:raise Blocked('Independent checkpoint fork detected')
        prior=record
    if prior['journal_seq']<len(events):
        if required:raise Blocked('Independent checkpoint stale; current history not qualified')
        return {'assurance':'INDEPENDENT_PREFIX_VERIFIED','checkpoint':prior,'reason':'Current head remains unqualified'}
    return {'assurance':'INDEPENDENT_HEAD_VERIFIED','checkpoint':prior,'reason':'Qualified reader matched this exact execution/head; adapter independence is an admission responsibility'}
