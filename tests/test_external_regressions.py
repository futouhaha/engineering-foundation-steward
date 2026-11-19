"""candidate.2: positive compositions and boundary invariants from external review."""
import copy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_runtime import SKILL
from validate_contract import validate
from inspect_project import inspect
from attention_check import check
from host_adapter import adapt

def example(name): return json.loads((SKILL/'examples'/(name+'.example.json')).read_text())

def chain(root='/workspace/synthetic'):
    c=example('project-contract'); c['project_root']=root; c['controls']=[]
    a=example('assessment'); a['capabilities']=[]
    for domain in ['E02','E04','E08','E09']:
        cid='control-'+domain
        c['controls'].append(dict(domain=domain,control_id=cid,implementation_target=domain,timing='now',reason='synthetic',trigger_condition=None,verify_by='test',owner='synthetic'))
        ev=dict(id='e-'+domain,kind='tool_result',locator='synthetic://'+domain,version='v1',observed_at='2026-11-19T00:00:00Z',scope=domain)
        a['evidence'].append(ev)
        a['capabilities'].append(dict(control_id=cid,state='verified_in_scope',evidence_refs=[ev['id']],limitation='synthetic only'))
    a['readiness']=[dict(for_action='real_data_operation',status='ready',reasons=['synthetic'],evidence_refs=['e-E09'],authorization='missing',authorization_ref=None)]
    b=example('implementation-brief'); b['baseline_refs']=['e-E09']; b['reuse_refs']=[]
    return c,a,b

class ExternalRegressions(unittest.TestCase):
    def test_complete_chain_and_reordered_context(self):
        c,a,b=chain()
        self.assertEqual(validate(a,[c]),[])
        self.assertEqual(validate(b,[c,a]),[])
        self.assertEqual(validate(b,[a,c]),[])
    def test_identical_contract_deduplicated(self):
        c,a,b=chain(); self.assertEqual(validate(a,[c,copy.deepcopy(c)]),[])
    def test_conflicting_control_across_contracts(self):
        c,a,b=chain(); contracts=[]
        for ctrl in c['controls']:
            d=copy.deepcopy(c); d['controls']=[dict(ctrl,control_id='shared')]; contracts.append(d)
        a['capabilities']=[dict(a['capabilities'][0],control_id='shared')]
        self.assertTrue(validate(a,contracts))
    def test_history_union_rejected(self):
        c,a,b=chain(); d=copy.deepcopy(c); d['revision']+=1
        self.assertTrue(validate(a,[c,d]))
    def test_different_roots_rejected(self):
        c,a,b=chain(); d=copy.deepcopy(c); d['project_root']='/workspace/other'
        self.assertTrue(validate(a,[c,d]))
    def test_missing_context_rejected(self):
        c,a,b=chain(); self.assertTrue(validate(b,[a])); self.assertTrue(validate(b,[c]))
    def test_cross_project_rejected(self):
        c,a,b=chain(); c['project_id']='other'; self.assertTrue(validate(b,[c,a]))
    def test_conflicting_assessment_rejected(self):
        c,a,b=chain(); other=copy.deepcopy(a); other['scope']='different'
        self.assertTrue(validate(b,[c,a,other]))
    def test_unresolved_reference_not_document_cycle(self):
        c,a,b=chain(); a['capabilities'][0]['evidence_refs']=[a['assessment_id']]
        self.assertTrue(validate(b,[c,a]))
    def test_context_count_and_size(self):
        c,a,b=chain(); self.assertTrue(validate(a,[c]*17))
        c['profile']['rationale']='x'*1048576; self.assertTrue(validate(a,[c]))
    def test_bad_related_semantics_not_skipped(self):
        c,a,b=chain(); a['capabilities'][0]['evidence_refs']=[]; self.assertTrue(validate(b,[c,a]))
    def test_fact_types_and_enums(self):
        c,a,b=chain(); facts=dict(project_id=c['project_id'],root=c['project_root'],identity='id',version='v1',event='session_start',action='read_only_audit',authority='current',coverage='complete')
        for key in facts:
            for bad in [None,False,[],{},'', '  ']:
                with self.subTest(key=key,bad=bad):
                    f=dict(facts); f[key]=bad; r=check(c,f)
                    self.assertEqual(r['status'],'unknown'); self.assertIsNone(r['dedup_key'])
        for key in ['event','action','authority','coverage']:
            f=dict(facts); f[key]='INVALID'; self.assertEqual(check(c,f)['status'],'unknown')
        for key in ['task_id','receipt_version','side_effect_result']:
            f=dict(facts); f[key]={}; self.assertEqual(check(c,f)['status'],'unknown')
    def test_previous_validation_before_dedup(self):
        c,a,b=chain(); f=dict(project_id=c['project_id'],root=c['project_root'],identity='id',version='v1',event='session_start',action='read_only_audit',authority='current',coverage='complete')
        key=check(c,f)['dedup_key']
        for prev in [{},dict(f,version={}),dict(f,dedup_key='bad')]: self.assertEqual(check(c,f,prev)['status'],'unknown')
        self.assertEqual(check(c,f,dict(f,dedup_key=key))['status'],'no_check')
    def test_stop_binding_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); eng=root/'.engineering'; eng.mkdir(); c,a,b=chain(str(root))
            (eng/'contract.json').write_text(json.dumps(c))
            f=dict(project_id=c['project_id'],root=str(root),identity='id',version='v1',event='session_start',action='read_only_audit',authority='current',coverage='complete')
            for bad in [None,'',' ',[],{},42]:
                for field in ['task_id','turn_id']:
                    data=dict(enabled=True,facts=f,closeout_requested=True,task_id='t1',turn_id='turn1'); data[field]=bad
                    (eng/'attention.json').write_text(json.dumps(data))
                    self.assertEqual(adapt(root,dict(cwd=str(root),hook_event_name='Stop',turn_id=bad)),{})
            data=dict(enabled=True,facts=f,closeout_requested=True,task_id='t1',turn_id='turn1')
            (eng/'attention.json').write_text(json.dumps(data))
            self.assertIn('systemMessage',adapt(root,dict(cwd=str(root),hook_event_name='Stop',turn_id='turn1')))
            self.assertEqual(adapt(root,dict(cwd=str(root),hook_event_name='Stop',turn_id='turn2')), {})
    def test_clean_and_process_filters_never_invoked(self):
        for filter_kind in ['clean','process']:
            with self.subTest(filter=filter_kind), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp).resolve()
                env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
                env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
                def git(*args): subprocess.run(['git','-C',str(root),*args],env=env,check=True,capture_output=True,timeout=3)
                git('init'); (root/'data.txt').write_text('base'); git('add','data.txt'); git('-c','user.name=Synthetic Test','-c','user.email=test@example.invalid','commit','-m','base')
                marker=root/'marker'; script=root/'filter.py'
                script.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("invoked")\n')
                (root/'.gitattributes').write_text('data.txt filter=probe\n.env filter=probe\nlarge.txt filter=probe\n')
                git('config','filter.probe.'+filter_kind,shlex.quote(sys.executable)+' '+shlex.quote(str(script)))
                (root/'data.txt').write_text('changed'); (root/'.env').write_text('synthetic'); (root/'large.txt').write_text('x'*2048)
                result=inspect(root,['.'],max_size=1024,include_git=True)
                self.assertFalse(marker.exists()); self.assertEqual(result['content_reads'],0)
                self.assertIsNone(result['git']['tracked_changes']['count']); self.assertEqual(result['git']['tracked_changes']['state'],'unknown')
                self.assertFalse(any(x['path'] in ['.env','large.txt'] for x in result['entries']))
    def test_no_worktree_commands(self):
        real=subprocess.Popen; calls=[]
        def record(args,**kwargs): calls.append(args); return real(args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp, patch('inspect_project.subprocess.Popen',record): inspect(Path(tmp).resolve(),['.'],include_git=True)
        self.assertEqual(len(calls),5)
        self.assertTrue(all('rev-parse' in c or 'symbolic-ref' in c for c in calls))
    def test_timeout_kills_descendant(self):
        # Synthetic injected subprocess, not a repository program. A leaked child writes later.
        real=subprocess.Popen
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); marker=root/'leak'; count=[0]
            child='import time; from pathlib import Path; time.sleep(2.5); Path('+repr(str(marker))+').write_text("leaked")'
            parent='import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",'+repr(child)+']); time.sleep(5)'
            def spawn(args,**kwargs):
                count[0]+=1; return real([sys.executable,'-c',parent if count[0]==1 else 'print("synthetic")'],**kwargs)
            with patch('inspect_project.subprocess.Popen',spawn): result=inspect(root,['.'],include_git=True)
            import time; time.sleep(.7)
            self.assertEqual(result['git']['root']['reason'],'timeout'); self.assertFalse(marker.exists())

    def test_timeout_kills_descendant_after_parent_exit(self):
        real=subprocess.Popen
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve(); marker=root/'leak'; count=[0]
            child='import time; from pathlib import Path; time.sleep(2.5); Path('+repr(str(marker))+').write_text("leaked")'
            parent='import subprocess,sys; subprocess.Popen([sys.executable,"-c",'+repr(child)+'])'
            def spawn(args,**kwargs):
                count[0]+=1; return real([sys.executable,'-c',parent if count[0]==1 else 'print("synthetic")'],**kwargs)
            with patch('inspect_project.subprocess.Popen',spawn): result=inspect(root,['.'],include_git=True)
            import time; time.sleep(.7)
            self.assertEqual(result['git']['root']['reason'],'timeout'); self.assertFalse(marker.exists())
