"""Print candidate additions only, never install or edit config."""
import argparse
import hashlib
import json
import shlex
from pathlib import Path
from common import emit, read_json

def preview(root, skill):
    root=Path(root).absolute(); skill=Path(skill).absolute()
    if root.resolve()!=root or skill.resolve()!=skill or not root.is_dir() or not (skill/'SKILL.md').is_file(): raise ValueError('invalid roots')
    config=root/'.codex/hooks.json'
    existing=read_json(config) if config.exists() else None
    digest=hashlib.sha256(json.dumps(existing,sort_keys=True).encode()).hexdigest()
    command='python3 '+shlex.quote(str(skill/'scripts/host_adapter.py'))+' --root '+shlex.quote(str(root))
    addition={'hooks':{event:[{'hooks':[{'type':'command','command':command,'timeout':5}]}] for event in ['SessionStart','Stop']}}
    return {'status':'proposed','writes':[], 'target':'.codex/hooks.json','expected_existing_semantic_sha256':digest,'additions_only':addition,'requires':['project permission','inspect other config layers and duplicate handlers','normal host trust','real trigger and disable test'],'rollback':'remove only these exact handlers; preserve all other configuration'}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('root'); p.add_argument('skill'); a=p.parse_args()
    try: emit(preview(a.root,a.skill))
    except (ValueError,OSError): emit({'status':'unknown','reason':'invalid configuration or scope'}); raise SystemExit(2)
