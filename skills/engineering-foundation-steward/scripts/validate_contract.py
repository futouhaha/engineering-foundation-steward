"""Restricted schema checker for the shipped v2 schemas, plus consistency checks.
Supported: type/const/enum/properties/required/additionalProperties/items/
minItems/minLength/minimum. Unknown schema keywords fail closed.
Not a general JSON Schema implementation. Never authenticates evidence.
"""
import argparse
import json
from pathlib import Path
from common import read_json, emit

KEYS={'$schema','type','const','enum','properties','required','additionalProperties','items','minItems','minLength','minimum'}
TYPES={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool,'null':type(None)}

def shape(value, schema, path='$'):
    errors=[]
    unknown=set(schema)-KEYS
    if unknown: return [path+': unsupported schema keyword']
    types=schema.get('type'); types=types if isinstance(types,list) else [types] if types else []
    if types and not any(type(value) is TYPES.get(t) for t in types): return [path+': type']
    if 'const' in schema and value != schema['const']: errors.append(path+': const')
    if 'enum' in schema and value not in schema['enum']: errors.append(path+': enum')
    if isinstance(value,dict):
        for k in schema.get('required',[]):
            if k not in value: errors.append(path+'.'+k+': required')
        for k,v in value.items():
            if k in schema.get('properties',{}): errors += shape(v,schema['properties'][k],path+'.'+k)
            elif schema.get('additionalProperties') is False: errors.append(path+': extra field')
    if isinstance(value,list):
        if len(value)<schema.get('minItems',0): errors.append(path+': minItems')
        for i,v in enumerate(value): errors+=shape(v,schema.get('items',{}),path+'['+str(i)+']')
    if isinstance(value,str) and len(value)<schema.get('minLength',0): errors.append(path+': minLength')
    if type(value) is int and value<schema.get('minimum',value): errors.append(path+': minimum')
    return errors

NAMES={'project-contract','assessment','implementation-brief','stage-charter'}

def validate(doc, related=None):
    """Validate a bounded set once, then check every document in the same context.
    Supply one effective contract (identical repeats allowed), not revision history.
    References terminate at evidence/source locators; they cannot name documents.
    """
    if related is None: related=[]
    if not isinstance(related,list) or len(related)>16: return ['related input limit or type']
    docs=[doc]+related
    try:
        if len(json.dumps(docs,allow_nan=False).encode())>1048576: return ['context size limit']
    except (TypeError,ValueError,RecursionError): return ['invalid bounded context']
    errors=[]; names=[]
    for i,d in enumerate(docs):
        if not isinstance(d,dict): return ['object required']
        version=d.get('schema_version')
        if not isinstance(version,str): return ['unsupported schema version; writes prohibited']
        name=version.removeprefix('engineering.').removesuffix('/v2')
        if name not in NAMES or version!='engineering.'+name+'/v2': return ['unsupported schema version; writes prohibited']
        if i and name not in {'project-contract','assessment'}: return ['related source must be a supported contract or assessment']
        try: errors+=shape(d,read_json(Path(__file__).resolve().parents[1]/'schemas'/(name+'.schema.json')))
        except RecursionError: return ['context depth limit']
        names.append(name)
    if errors: return sorted(set(errors))
    if any(d['project_id']!=doc['project_id'] for d in docs): return ['related project mismatch']
    contracts=[d for d in docs if d['schema_version']=='engineering.project-contract/v2']
    if contracts and any(d!=contracts[0] for d in contracts[1:]):
        errors.append('ambiguous effective contract; select one exact revision, do not union history')
    definitions={}; assessments={}
    for d in docs:
        control_ids=[c['control_id'] for c in d.get('controls',[])]
        if len(control_ids)!=len(set(control_ids)): errors.append('duplicate control id')
        for c in d.get('controls',[]):
            if c['control_id'] in definitions and definitions[c['control_id']]!=c: errors.append('conflicting control definition across documents')
            definitions[c['control_id']]=c
        if 'assessment_id' in d:
            key=d['assessment_id']
            if key in assessments and assessments[key]!=d: errors.append('conflicting assessment identity')
            assessments[key]=d
    if errors: return sorted(set(errors))
    try:
        for d,name in zip(docs,names): errors+=_semantics(d,name,docs,list(definitions.values()))
    except RecursionError: return ['semantic depth limit']
    return sorted(set(errors))

def _semantics(doc, name, docs, effective_controls):
    errors=[]
    ids={}
    locators=set()
    for d in docs:
        if d.get('project_id')!=doc['project_id']: errors.append('related project mismatch')
        local=set()
        for e in d.get('evidence',[]):
            if e['id'] in local: errors.append('duplicate evidence id')
            local.add(e['id'])
            if e['id'] in ids and ids[e['id']] != e: errors.append('conflicting evidence id across documents')
            else: ids[e['id']]=e
            locators.add(e['locator'])
        locators.update(b['locator'] for b in d.get('source_bindings',[]))
    def walk(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in {'evidence_refs','identity_refs','authority_refs'}:
                    for ref in x:
                        if ref not in ids: errors.append('unresolved '+k)
                walk(x)
        elif isinstance(v,list):
            for x in v: walk(x)
    walk(doc)
    def strong(refs):
        return bool(refs) and all(r in ids and ids[r]['version'] and ids[r]['observed_at'] and ids[r]['kind'] in {'tool_result','git','file'} for r in refs)
    for c in doc.get('capabilities',[]):
        if c['state'] in {'verified_in_scope','partially_verified'} and not strong(c['evidence_refs']): errors.append('verified capability requires versioned observed evidence')
    for r in doc.get('readiness',[]):
        if r['status']=='ready' and not r['evidence_refs']: errors.append('ready requires evidence')
        minima={'isolated_prototype':{'E01','E03','E04','E08'},'local_development':{'E03','E04','E05','E08','E10'},'task_loop':{'E03','E04','E05','E08','E10'},'stage_loop':{'E03','E04','E05','E06','E07','E08','E10'},'real_data_operation':{'E02','E04','E08','E09'},'release':{'E02','E04','E08','E09','E10'},'continuous_scheduling':{'E05','E06','E08','E09','E10'}}
        if r['status']=='ready' and r['for_action'] in minima:
            if not strong(r['evidence_refs']): errors.append('operational ready requires versioned observed evidence')
            controls=[c for c in effective_controls if c['timing']=='now']
            verified={c['control_id'] for c in doc.get('capabilities',[]) if c['state']=='verified_in_scope' and strong(c['evidence_refs'])}
            covered={c['domain'] for c in controls if c['control_id'] in verified}
            if not minima[r['for_action']] <= covered: errors.append('ready lacks verified minimum action controls; supply related contract')
        if r['authorization']=='verified_for_scope' and r['authorization_ref'] not in ids: errors.append('authorization requires resolvable source; still manually authenticate')
    for t in doc.get('trigger_bindings',[]):
        if t['state']=='observed' and (not t['host_version'] or not strong(t['evidence_refs'])): errors.append('observed trigger requires host and versioned event evidence')
    control_ids=[c['control_id'] for c in doc.get('controls',[])]
    if len(set(control_ids))!=len(control_ids): errors.append('duplicate control id')
    capability_ids=[c['control_id'] for c in doc.get('capabilities',[])]
    if len(set(capability_ids))!=len(capability_ids): errors.append('duplicate capability id')
    for c in doc.get('controls',[]):
        if c['timing']=='later_when' and not c['trigger_condition']: errors.append('later_when requires event')
    a=doc.get('autonomy',{})
    if a.get('demonstrated') in {'A1','A2','A3'} and not strong(a['evidence_refs']): errors.append('demonstrated autonomy requires evidence')
    if name=='project-contract':
        for b in doc['source_bindings']:
            if b['status']=='verified_in_scope' and not any(e['locator']==b['locator'] and strong([e['id']]) for e in doc['evidence']): errors.append('verified source requires evidence')
    if name in {'implementation-brief','stage-charter'}:
        for field in ['baseline_refs','reuse_refs','starting_sources','state_sources']:
            for ref in doc.get(field,[]):
                if ref not in ids and ref not in locators: errors.append('unresolved '+field+'; supply related evidence')
        for field in ['changes'] if name=='implementation-brief' else ['tasks','acceptance','stop_conditions']:
            if not doc[field]: errors.append('executable draft requires '+field)
    tasks=doc.get('tasks',[]); task_ids=[t['task_id'] for t in tasks]
    if len(set(task_ids))!=len(task_ids): errors.append('duplicate task id')
    graph={t['task_id']:t['depends_on'] for t in tasks}
    visiting=set(); visited=set()
    def cycle(node):
        if node in visiting: return True
        if node in visited: return False
        visiting.add(node)
        found=any(cycle(dep) for dep in graph.get(node,[]) if dep in graph)
        visiting.remove(node); visited.add(node)
        return found
    for t in tasks:
        if any(d not in graph for d in t['depends_on']): errors.append('unknown task dependency')
        if cycle(t['task_id']): errors.append('task dependency cycle')
    return sorted(set(errors))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('file'); p.add_argument('--related',action='append',default=[]); a=p.parse_args()
    try:
        errors=validate(read_json(a.file),[read_json(f) for f in a.related]); emit({'valid':not errors,'errors':errors,'assurance':'structure_and_reference_consistency_only_not_truth_or_authorization'}); raise SystemExit(bool(errors))
    except (ValueError,OSError,RecursionError,KeyError,TypeError): emit({'valid':False,'errors':['invalid bounded input']}); raise SystemExit(2)
