import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/engineering-foundation-steward'
sys.path.insert(0,str(SKILL/'scripts'))
from common import read_json
from inspect_project import inspect
from validate_contract import validate,shape
from attention_check import check
from host_adapter import adapt
from preview_install import preview

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name).resolve()
        self.contract=json.loads((SKILL/'examples/project-contract.example.json').read_text())
        self.contract['project_root']=str(self.root)
        self.facts=dict(project_id=self.contract['project_id'],root=str(self.root),identity='synthetic-root-1',version='v1',event='session_start',action='read_only_audit',authority='current',coverage='complete')
    def tearDown(self): self.temp.cleanup()
    def git(self,*args):
        return subprocess.run(['git','-C',str(self.root),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def test_example_contract(self): self.assertEqual(validate(self.contract),[])
    def test_assessment(self): self.assertEqual(validate(read_json(SKILL/'examples/assessment.example.json')),[])
    def test_invalid_supplied(self):
        fixtures = sorted((ROOT/'evals').glob('invalid*.json'))
        required = {'invalid_draft_claims_approval.json', 'invalid_verified_without_evidence.json'}
        self.assertTrue(required.issubset({f.name for f in fixtures}),
                        'Required negative fixtures missing; restore evals/invalid*.json')
        for f in fixtures:
            with self.subTest(fixture=f.name):
                self.assertTrue(validate(read_json(f)), f.name)
    def test_references(self):
        self.contract['identity_refs']=['missing']; self.assertTrue(validate(self.contract))
    def test_schema_unknown(self): self.assertTrue(shape({}, {'unknown':True}))
    def test_boolean_integer(self):
        self.contract['revision']=True; self.assertTrue(validate(self.contract))
    def test_unknown_version(self):
        self.contract['schema_version']='engineering.project-contract/v3'; self.assertTrue(validate(self.contract))
    def test_observed_without_event(self):
        self.contract['trigger_bindings'][0]['state']='observed'; self.assertTrue(validate(self.contract))
    def test_later_without_trigger(self):
        self.contract['controls'][1]['trigger_condition']=None; self.assertTrue(validate(self.contract))
    def test_draft_cannot_authorize(self):
        d=read_json(SKILL/'examples/stage-charter.example.json'); d['status']='approved'; self.assertTrue(validate(d))
    def test_dependency_cycle(self):
        d=read_json(SKILL/'examples/stage-charter.example.json'); d['tasks'][0]['depends_on']=[d['tasks'][1]['task_id']]; self.assertIn('task dependency cycle',validate(d))
    def test_verified_evidence(self):
        d=read_json(SKILL/'examples/assessment.example.json'); d['capabilities'][0]['state']='verified_in_scope'; self.assertTrue(validate(d))
    def test_unknown_git(self):
        result=inspect(self.root,['.'],include_git=True); self.assertEqual(result['content_reads'],0); self.assertEqual(result['git']['head']['state'],'unknown')
    def test_default_never_starts_git(self):
        from unittest.mock import patch
        self.git('init')
        with patch('inspect_project.subprocess.Popen',side_effect=AssertionError('Git forbidden')):
            result=inspect(self.root,['.'])
        self.assertEqual(result['git']['head']['reason'],'git_not_requested')
    def test_cli_default_no_git(self):
        self.git('init')
        run=subprocess.run([sys.executable,'-B',str(SKILL/'scripts/inspect_project.py'),str(self.root),'--allow','.'],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(run.stdout)['git']['root']['reason'],'git_not_requested')
    def test_cli_git_opt_in(self):
        self.git('init')
        run=subprocess.run([sys.executable,'-B',str(SKILL/'scripts/inspect_project.py'),str(self.root),'--allow','.','--include-git'],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(run.stdout)['git']['root']['value'],str(self.root))
    def test_parent_repository(self):
        self.git('init'); child=self.root/'child'; child.mkdir()
        self.assertEqual(inspect(child,['.'],include_git=True)['git']['root']['state'],'unknown')
        self.assertEqual(inspect(self.root,['.'],include_git=True)['git']['root']['value'],str(self.root))
    def test_worktree(self):
        self.git('init'); (self.root/'a.txt').write_text('synthetic')
        self.git('add','--','a.txt'); self.git('-c','user.name=Synthetic Test','-c','user.email=test@example.invalid','commit','-m','fixture')
        work=self.root/'work'; self.git('worktree','add','--detach',str(work))
        result=inspect(work,['.'],include_git=True); self.assertEqual(result['git']['head']['reason'],'external_or_linked_git_metadata_not_supported')
    def test_git_link_no_subprocess(self):
        from unittest.mock import patch
        (self.root/'.git').write_text('gitdir: /not-authorized/repo.git\n')
        with patch('inspect_project.subprocess.Popen',side_effect=AssertionError('outside Git forbidden')):
            result=inspect(self.root,['.'],include_git=True)
        self.assertEqual(result['git']['head']['reason'],'external_or_linked_git_metadata_not_supported')
    def test_git_symlink_no_subprocess(self):
        from unittest.mock import patch
        (self.root/'.git').symlink_to('/not-authorized/repo.git')
        with patch('inspect_project.subprocess.Popen',side_effect=AssertionError('outside Git forbidden')):
            result=inspect(self.root,['.'],include_git=True)
        self.assertEqual(result['git']['head']['reason'],'external_or_linked_git_metadata_not_supported')
    def test_symlink_secret_excluded(self):
        (self.root/'.env').write_text('SYNTHETIC_SENTINEL_NOT_A_SECRET')
        (self.root/'outside').symlink_to('/tmp'); (self.root/'ok.txt').write_text('abc')
        result=inspect(self.root,['.']); self.assertEqual([e['path'] for e in result['entries']],['ok.txt']); self.assertEqual(result['content_reads'],0)
    def test_scope_escape(self):
        with self.assertRaises(ValueError): inspect(self.root,['../'])
    def test_nested_symlink(self):
        (self.root/'link').symlink_to('/tmp')
        result=inspect(self.root,['link']); self.assertEqual(result['entries'],[])
    def test_limits(self):
        for i in range(20): (self.root/str(i)).write_text('x'*20)
        result=inspect(self.root,['.'],5,10); self.assertLessEqual(len(result['entries']),5); self.assertTrue(result['skipped'])
    def test_json_limits(self):
        p=self.root/'large.json'; p.write_text(' '*262145)
        with self.assertRaises(ValueError): read_json(p)
    def test_json_symlink(self):
        p=self.root/'a'; p.write_text('{}'); q=self.root/'b'; q.symlink_to(p)
        with self.assertRaises(ValueError): read_json(q)
    def test_first_baseline(self): self.assertEqual(check(self.contract,self.facts)['status'],'suggest')
    def test_dedup(self):
        first=check(self.contract,self.facts); last=dict(self.facts,dedup_key=first['dedup_key']); self.assertEqual(check(self.contract,self.facts,last)['status'],'no_check')
    def test_changed_version(self):
        last=dict(self.facts); self.facts['version']='v2'; self.assertEqual(check(self.contract,self.facts,last)['reasons'],['version_changed'])
    def test_identity_conflict(self):
        last=dict(self.facts,identity='other'); self.assertEqual(check(self.contract,self.facts,last)['status'],'pause')
    def test_wrong_project(self):
        self.facts['project_id']='other'; self.assertEqual(check(self.contract,self.facts)['status'],'pause')
    def test_revoked_even_duplicate(self):
        self.facts['authority']='revoked'; self.assertEqual(check(self.contract,self.facts,self.facts)['status'],'pause')
    def test_partial(self):
        self.facts['coverage']='partial'; self.assertEqual(check(self.contract,self.facts)['status'],'unknown')
    def test_risk(self):
        self.facts['event']='risk_change'; self.assertEqual(check(self.contract,self.facts)['mode'],'retrofit')
    def test_stage(self):
        self.facts['event']='stage_start'; self.assertEqual(check(self.contract,self.facts)['mode'],'milestone-charter')
    def test_closeout_receipt(self):
        self.facts.update(event='task_closeout',task_id='task1'); self.assertEqual(check(self.contract,self.facts)['reasons'],['missing_current_task_receipt'])
    def test_ordinary(self):
        self.facts['event']='ordinary'; self.assertEqual(check(self.contract,self.facts)['status'],'no_check')
    def test_unknown_effect(self):
        self.facts['side_effect_result']='unknown'; self.assertEqual(check(self.contract,self.facts)['status'],'pause')
    def test_fifo_refused(self):
        p=self.root/'fifo'; os.mkfifo(p)
        with self.assertRaises(ValueError): read_json(p)
    def test_unknown_authority(self):
        self.facts.update(authority='unknown',action='real_data_operation')
        self.assertEqual(check(self.contract,self.facts,self.facts)['status'],'pause')
    def test_ordinary_unknown_effect(self):
        self.facts.update(event='ordinary',side_effect_result='unknown')
        self.assertEqual(check(self.contract,self.facts)['status'],'pause')
    def test_conflicting_evidence(self):
        d=copy.deepcopy(self.contract); d['evidence'][0]['kind']='tool_result'
        self.assertTrue(validate(self.contract,[d]))
    def test_null_schema(self): self.assertTrue(validate({'schema_version':None}))
    def test_dangerous_ready(self):
        d=read_json(SKILL/'examples/assessment.example.json'); d['readiness'][0]['for_action']='real_data_operation'
        self.assertTrue(validate(d))
    def test_large_dag(self):
        d=read_json(SKILL/'examples/stage-charter.example.json'); template=d['tasks'][0]; d['tasks']=[]
        for i in range(35):
            t=copy.deepcopy(template); t.update(task_id=str(i),depends_on=[str(j) for j in range(max(0,i-2),i)]); d['tasks'].append(t)
        self.assertNotIn('task dependency cycle',validate(d))
    def test_related_unknown_schema(self):
        d=read_json(SKILL/'examples/assessment.example.json')
        self.assertTrue(validate(d,[{'schema_version':'unknown/version','project_id':d['project_id'],'controls':[]}]))
    def test_related_invalid_shape(self):
        d=read_json(SKILL/'examples/assessment.example.json')
        self.assertTrue(validate(d,[{'schema_version':'engineering.project-contract/v2','project_id':d['project_id']}]))
    def test_nonobject_facts(self): self.assertEqual(check(self.contract,[])['status'],'unknown')
    def test_nonobject_event(self):
        with self.assertRaises(ValueError): adapt(self.root,[])
    def test_adapter_invalid_cli_json(self):
        r=subprocess.run([sys.executable,str(SKILL/'scripts/host_adapter.py'),'--root',str(self.root)],input='[]',text=True,capture_output=True,timeout=2)
        self.assertEqual(r.returncode,0); self.assertIn('unknown',json.loads(r.stdout)['systemMessage']); self.assertEqual(r.stderr,'')
    def test_concurrent_hook(self):
        from concurrent.futures import ThreadPoolExecutor
        self.install_fixture(); event=dict(cwd=str(self.root),hook_event_name='Stop',turn_id='turn1')
        before={p.name:p.read_bytes() for p in (self.root/'.engineering').iterdir()}
        with ThreadPoolExecutor(max_workers=2) as pool: outputs=list(pool.map(lambda _:adapt(self.root,event),range(2)))
        self.assertEqual(outputs[0],outputs[1]); self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'.engineering').iterdir()})
    def test_duplicate_control(self):
        self.contract['controls'][1]['control_id']=self.contract['controls'][0]['control_id']; self.assertIn('duplicate control id',validate(self.contract))
    def test_duplicate_capability(self):
        d=read_json(SKILL/'examples/assessment.example.json'); d['capabilities'].append(copy.deepcopy(d['capabilities'][0])); self.assertIn('duplicate capability id',validate(d))
    def test_git_output_budget(self):
        from unittest.mock import patch
        import io
        # Real bounded child process uses the same Popen pipeline; no project code is run.
        real_popen=subprocess.Popen
        def noisy(*args,**kwargs):
            return real_popen([sys.executable,'-c','import sys; sys.stdout.write("x"*20000)'],**kwargs)
        with patch('inspect_project.subprocess.Popen',noisy): result=inspect(self.root,['.'],include_git=True)
        self.assertEqual(result['git']['root']['reason'],'output_limit')
    def test_git_timeout(self):
        from unittest.mock import patch
        real_popen=subprocess.Popen
        calls=[0]
        def delayed(*args,**kwargs):
            calls[0]+=1
            script='import time; time.sleep(3)' if calls[0]==1 else 'print("synthetic")'
            return real_popen([sys.executable,'-c',script],**kwargs)
        with patch('inspect_project.subprocess.Popen',delayed): result=inspect(self.root,['.'],include_git=True)
        self.assertEqual(result['git']['root']['reason'],'timeout')
    def install_fixture(self):
        d=self.root/'.engineering'; d.mkdir()
        (d/'contract.json').write_text(json.dumps(self.contract))
        (d/'attention.json').write_text(json.dumps({'enabled':True,'facts':self.facts,'closeout_requested':True,'task_id':'t1','turn_id':'turn1'}))
    def test_stop_no_binding(self): self.assertEqual(adapt(self.root,dict(cwd=str(self.root),hook_event_name='Stop')), {})
    def test_stop_wrong_turn(self):
        self.install_fixture(); self.assertEqual(adapt(self.root,dict(cwd=str(self.root),hook_event_name='Stop',turn_id='other')), {})
    def test_hook_disabled(self): self.assertEqual(adapt(self.root,{},False),{})
    def test_subdirectory_no_git(self):
        self.install_fixture(); sub=self.root/'sub'; sub.mkdir(); self.assertIn('systemMessage',adapt(self.root,dict(cwd=str(sub),hook_event_name='SessionStart')))
    def test_hook_duplicate_no_writes(self):
        self.install_fixture(); before={p.name:p.read_bytes() for p in (self.root/'.engineering').iterdir()}; event=dict(cwd=str(self.root),hook_event_name='Stop',turn_id='turn1')
        a=adapt(self.root,event); b=adapt(self.root,event); self.assertEqual(a,b); self.assertNotIn('decision',a); self.assertNotIn('continue',a)
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'.engineering').iterdir()})
    def test_hook_outside(self):
        with self.assertRaises(ValueError): adapt(self.root,dict(cwd='/outside',hook_event_name='SessionStart'))
    def test_preview_preserves_existing(self):
        d=self.root/'.codex'; d.mkdir(); p=d/'hooks.json'; p.write_text('{"hooks": {"Stop": []}}'); before=p.read_bytes(); out=preview(self.root,SKILL); self.assertEqual(out['writes'],[]); self.assertEqual(p.read_bytes(),before)

if __name__=='__main__': unittest.main(verbosity=2)
