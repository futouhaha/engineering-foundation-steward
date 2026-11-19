"""Advisory SessionStart/Stop adapter. Stdout never requests continuation.
Invocation pins an explicit canonical root, even for projects without Git.
No transcript reading, subprocess, model call, state writes, or task execution.
"""
import argparse
import json
import sys
from pathlib import Path
from common import read_json, LIMIT
from attention_check import check

def adapt(root, event, enabled=True):
    if not enabled: return {}
    if not isinstance(event,dict): raise ValueError('event object required')
    root=Path(root).absolute()
    if root.resolve()!=root or not root.is_dir(): raise ValueError('invalid root')
    if not isinstance(event.get('cwd'),str) or not event['cwd'].strip(): raise ValueError('cwd required')
    cwd=Path(event['cwd']).absolute()
    if cwd.resolve()!=cwd or not (cwd==root or root in cwd.parents): raise ValueError('cwd mismatch')
    kind=event.get('hook_event_name')
    if kind not in {'SessionStart','Stop'}: return {}
    # Ordinary Stop has no business meaning. Read only an explicit local binding.
    binding=root/'.engineering'/'attention.json'
    if not binding.exists(): return {} if kind=='Stop' else {'systemMessage':'工程提醒未登记：如需检查，请显式调用工程基建 Skill。'}
    data=read_json(binding)
    if not isinstance(data,dict): raise ValueError('binding object required')
    if data.get('enabled') is not True: return {}
    if kind=='Stop':
        values=[data.get('task_id'),data.get('turn_id'),event.get('turn_id')]
        if data.get('closeout_requested') is not True or not all(isinstance(v,str) and v.strip() and len(v)<=4096 for v in values): return {}
        if data['turn_id']!=event['turn_id']: return {}
    contract=read_json(root/'.engineering'/'contract.json')
    if not isinstance(data.get('facts'),dict): raise ValueError('facts object required')
    facts=data['facts'].copy()
    # Current metadata is independently compared; caller snapshot is not latest Git proof.
    facts['root']=str(root)
    facts['event']='task_closeout' if kind=='Stop' else 'session_start'
    if kind=='Stop': facts['task_id']=data['task_id']
    facts['coverage']='partial' # no external sources queried by this lightweight hook
    result=check(contract,facts,data.get('previous'))
    if result['status']=='no_check': return {}
    reason=','.join(result['reasons'])
    message='工程轻检查：'+result['status']+' / '+reason+'。仅提醒；请按允许范围显式复查，不代表验收或授权。'
    return {'systemMessage':message}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--root',required=True); p.add_argument('--disabled',action='store_true'); a=p.parse_args()
    try:
        raw=sys.stdin.buffer.read(16385)
        if len(raw)>16384: raise ValueError('event too large')
        out=adapt(a.root,json.loads(raw),not a.disabled)
    except (ValueError,OSError,TypeError,KeyError,RecursionError):
        out={'systemMessage':'工程轻检查 unknown：输入或来源不可用；相关结论未验证，请显式检查。'}
    print(json.dumps(out,ensure_ascii=False))
