"""Pure bounded comparison. No acceptance, execution, or persistent cache."""
import argparse
import hashlib
import json
from common import read_json, emit
from validate_contract import validate

EVENTS={'session_start','task_start','task_closeout','handoff','risk_change','stage_start','release','ordinary'}

ACTIONS={'discussion','read_only_audit','isolated_prototype','local_development','task_loop','stage_loop','real_data_operation','release','continuous_scheduling'}
REQUIRED={'project_id','root','identity','version','event','action','authority','coverage'}
OPTIONAL={'task_id','receipt_version','side_effect_result'}

def valid_facts(value, previous=False):
    if not isinstance(value,dict) or not REQUIRED<=value.keys(): return False
    if set(value)-REQUIRED-OPTIONAL-({'dedup_key'} if previous else set()): return False
    if any(not isinstance(value[k],str) or not value[k].strip() or len(value[k])>4096 for k in REQUIRED): return False
    if value['event'] not in EVENTS or value['action'] not in ACTIONS: return False
    if value['authority'] not in {'current','unknown','revoked'} or value['coverage'] not in {'complete','partial'}: return False
    for k in OPTIONAL & value.keys():
        if not isinstance(value[k],str) or not value[k].strip() or len(value[k])>4096: return False
    if 'side_effect_result' in value and value['side_effect_result'] not in {'known','unknown','not_run','succeeded','failed'}: return False
    if 'dedup_key' in value:
        key=value['dedup_key']
        if not isinstance(key,str) or len(key)!=64 or any(c not in '0123456789abcdef' for c in key): return False
    return True

def check(contract, facts, previous=None):
    base={'status':'unknown','mode':None,'reasons':[], 'affected_action':'unspecified','authorizes':False,'dedup_key':None}
    if not valid_facts(facts) or (previous is not None and not valid_facts(previous,True)):
        return dict(base,reasons=['invalid_facts_or_previous'])
    base['affected_action']=facts['action']
    if validate(contract): return dict(base,reasons=['invalid_contract'])
    key=hashlib.sha256(json.dumps({'contract':contract,'facts':facts},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    base['dedup_key']=key
    def result(status,reason,mode=None): return dict(base,status=status,reasons=[reason],mode=mode)
    if facts['project_id']!=contract['project_id'] or facts['root']!=contract['project_root']: return result('pause','project_identity_mismatch','continuity-check')
    if facts['authority']=='revoked': return result('pause','authority_revoked_for_dependent_actions','continuity-check')
    if not facts['identity'] or not facts['version']: return result('unknown','identity_or_version_unknown','continuity-check')
    if previous:
        if previous.get('identity')!=facts['identity'] or previous.get('root')!=facts['root']: return result('pause','identity_changed','continuity-check')
    if facts['authority']!='current' and facts['action'] not in {'discussion','read_only_audit'}: return result('pause','authority_unknown_for_action','continuity-check')
    if facts.get('side_effect_result')=='unknown': return result('pause','unknown_side_effect_no_retry','continuity-check')
    if facts['event']=='ordinary': return result('no_check','ordinary_event')
    if facts['event']=='risk_change': return result('suggest','risk_changed','retrofit')
    if facts['event']=='stage_start': return result('suggest','new_stage_requires_scoped_draft','milestone-charter')
    if facts['event']=='task_closeout' and facts.get('task_id') and facts.get('receipt_version')!=facts['version']: return result('suggest','missing_current_task_receipt','continuity-check')
    if facts['coverage']!='complete': return result('unknown','partial_sources_only','continuity-check')
    if not previous: return result('suggest','establish_limited_baseline','continuity-check')
    if previous.get('dedup_key')==key: return result('no_check','duplicate_observation_not_acceptance')
    if previous.get('version')!=facts['version']: return result('suggest','version_changed','continuity-check')
    return result('suggest','event_or_contract_changed','continuity-check')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('contract'); p.add_argument('facts'); p.add_argument('--previous'); a=p.parse_args()
    try: emit(check(read_json(a.contract),read_json(a.facts),read_json(a.previous) if a.previous else None))
    except (ValueError,OSError,TypeError,KeyError,RecursionError): emit({'status':'unknown','reason':'invalid_bounded_input','authorizes':False}); raise SystemExit(2)
