import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
from repo_temp import workspace

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('booster', ROOT / 'scripts/booster.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

def plan():
    return {'revision':'r1','goal':'visible value','next':'a','nodes':[{'id':'a','owner':'one','depends_on':[], 'status':'planned','acceptance':'value is visible','target':'real-terminal','revision':'r1'}]}

class PlanTests(unittest.TestCase):
    def test_nonobject(self):
        with self.assertRaises(ValueError): b.validate([])
    def test_nested_malformed_evidence(self):
        for malformed in (None, [], 'invalid', 42):
            p=plan();p['next']=None;p['nodes'][0].update(status='verified',evidence=malformed)
            with self.subTest(evidence=malformed), self.assertRaisesRegex(ValueError,'evidence must be object'):
                b.validate(p)
    def test_malformed_nodes(self):
        for malformed in (None, [], 'invalid', 42):
            p=plan();p['nodes']=[malformed]
            with self.subTest(node=malformed), self.assertRaisesRegex(ValueError,'node must be object'):
                b.validate(p)
    def test_ready(self): self.assertTrue(b.validate(plan())['valid'])
    def test_verified(self):
        p=plan(); p['next']=None; p['nodes'][0].update(status='verified', evidence={'kind':'real','result':'pass','revision':'r1','target':'real-terminal','reference':'run.log','observed_at':'2020-01-01T00:00:00Z'})
        self.assertTrue(b.validate(p)['valid'])
        for field,value in [('kind','mock'),('revision','old'),('target','different')]:
            bad=copy.deepcopy(p); bad['nodes'][0]['evidence'][field]=value
            with self.assertRaises(ValueError): b.validate(bad)
    def test_cycle_and_unknown(self):
        for dependency in ['a','missing']:
            p=plan();p['nodes'][0]['depends_on']=[dependency]
            with self.assertRaises(ValueError):b.validate(p)
    def test_dependency_gate(self):
        p=plan(); second=copy.deepcopy(p['nodes'][0]);second.update(id='b',depends_on=['a'],status='active');p['nodes'].append(second);p['next']='b'
        with self.assertRaises(ValueError):b.validate(p)
    def test_blocked(self):
        p=plan();p['nodes'][0]['status']='blocked';p['next']=None
        self.assertTrue(b.validate(p)['valid'])
    def test_status(self):
        p=plan();p['nodes'][0]['status']='report_ready'
        with self.assertRaises(ValueError):b.validate(p)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.root=workspace(self)
        (self.root/'.booster-tmp').mkdir();self.file=self.root/'.booster-tmp/out.txt';self.file.write_text('owned scratch')
        self.item={'path':'.booster-tmp/out.txt','owner':'test','inactive':True,'retain':False,'expires_at':'2020-01-01T00:00:00Z','sha256':hashlib.sha256(self.file.read_bytes()).hexdigest()}
        self.save()
    def save(self):(self.root/'manifest.json').write_text(json.dumps({'owner':'test','files':[self.item]}))
    def run_gc(self,apply=False):return b.collect(str(self.root),'manifest.json','test',apply)
    def test_dry_run(self):
        self.assertEqual(len(self.run_gc()['eligible']),1);self.assertTrue(self.file.exists())
    def test_actual_move_and_recovery(self):
        result=self.run_gc(True);self.assertFalse(self.file.exists());self.assertEqual(len(result['moved']),1)
        self.assertEqual((self.root/result['moved'][0]['destination']).read_text(),'owned scratch')
        self.assertTrue((self.root/result['recovery']).is_file())
        mapping=json.loads((self.root/result['recovery']).read_text())
        original=b.checked(self.root,mapping[0]['source']); saved=b.checked(self.root,mapping[0]['destination'])
        self.assertFalse(original.exists());self.assertEqual(b.digest(saved),mapping[0]['sha256'])
        saved.rename(original)
        self.assertEqual(original.read_text(),'owned scratch')
    def test_retained_active_unexpired_changed(self):
        original=self.item.copy()
        for field,value in [('retain',True),('inactive',False),('expires_at','2999-01-01T00:00:00Z'),('sha256','changed'),('owner','other'),('path','../outside')]:
            self.item=original.copy();self.item[field]=value;self.save()
            self.assertEqual(self.run_gc(True)['moved'],[]);self.assertTrue(self.file.exists())
    def test_lock(self):
        (self.root/'.booster-gc.lock').write_text('other owner')
        with self.assertRaises(FileExistsError):self.run_gc(True)
        self.assertTrue(self.file.exists());self.assertEqual((self.root/'.booster-gc.lock').read_text(),'other owner')
    def test_collector_preserves_changed_lock_content(self):
        lock=self.root/'.booster-gc.lock';original_rename=Path.rename
        def changed(path,destination):
            lock.write_bytes(b'changed by fixture writer')
            return original_rename(path,destination)
        with patch.object(Path,'rename',changed):
            with self.assertRaisesRegex(ValueError,'collector lock content changed'):self.run_gc(True)
        self.assertEqual(lock.read_bytes(),b'changed by fixture writer')
        mapping_path=next((self.root/'.booster-quarantine').glob('*/recovery.json'))
        mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
        saved=self.root/mapping[0]['destination'];self.assertEqual(saved.read_text(),'owned scratch')
        saved.rename(self.file)
        with self.assertRaises(FileExistsError):self.run_gc(True)
        self.assertEqual(lock.read_bytes(),b'changed by fixture writer')
    def test_collector_preserves_replacement_lock(self):
        lock=self.root/'.booster-gc.lock';original=self.root/'original-owned-lock';original_rename=Path.rename
        def replaced(path,destination):
            os.replace(lock,original);lock.write_bytes(b'replacement fixture owner')
            return original_rename(path,destination)
        with patch.object(Path,'rename',replaced):
            with self.assertRaisesRegex(ValueError,'collector lock identity changed'):self.run_gc(True)
        self.assertEqual(lock.read_bytes(),b'replacement fixture owner');self.assertTrue(original.is_file())
    def test_collector_stops_following_moves_after_lock_change(self):
        second=self.root/'.booster-tmp/second.txt';second.write_text('second owned scratch')
        item=dict(self.item,path='.booster-tmp/second.txt',sha256=hashlib.sha256(second.read_bytes()).hexdigest())
        (self.root/'manifest.json').write_text(json.dumps({'owner':'test','files':[self.item,item]}))
        lock=self.root/'.booster-gc.lock';original_rename=Path.rename;calls=[]
        def changed(path,destination):
            result=original_rename(path,destination);calls.append(path)
            lock.write_bytes(b'changed by fixture writer')
            return result
        with patch.object(Path,'rename',changed):
            with self.assertRaisesRegex(ValueError,'collector lock content changed'):self.run_gc(True)
        self.assertEqual(len(calls),1);self.assertFalse(self.file.exists());self.assertTrue(second.is_file())
        self.assertEqual(lock.read_bytes(),b'changed by fixture writer')
        self.assertEqual(len(list((self.root/'.booster-quarantine').glob('*/recovery.json'))),1)
    def test_collector_preserves_hardlinked_lock(self):
        lock=self.root/'.booster-gc.lock';alias=self.root/'lock-alias';original_rename=Path.rename
        def linked(path,destination):
            alias.hardlink_to(lock)
            return original_rename(path,destination)
        with patch.object(Path,'rename',linked):
            with self.assertRaisesRegex(ValueError,'collector lock link/reparse forbidden'):self.run_gc(True)
        self.assertTrue(lock.is_file());self.assertEqual(lock.read_bytes(),alias.read_bytes())
    def test_collector_lock_initialization_preserves_permission_denial(self):
        with patch.object(b.os,'write',side_effect=PermissionError('fixture access denied')):
            with self.assertRaisesRegex(PermissionError,'fixture access denied'):self.run_gc(True)
        self.assertTrue((self.root/'.booster-gc.lock').is_file());self.assertTrue(self.file.is_file())
        self.assertFalse((self.root/'.booster-quarantine').exists())
    def test_gc_cli_reports_reconciliation_for_existing_lock(self):
        lock=self.root/'.booster-gc.lock';lock.write_text('retained owner')
        cli=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),'gc-apply','--root',str(self.root),'--manifest','manifest.json','--owner','test'],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1,cli.stdout+cli.stderr)
        result=json.loads(cli.stdout);self.assertTrue(result['reconciliation_required'])
        self.assertEqual(result['error_type'],'FileExistsError');self.assertEqual(result['effect'],'UNKNOWN');self.assertEqual(lock.read_text(),'retained owner')
        self.assertTrue(self.file.is_file())
    def test_gc_cli_reports_unknown_after_partial_move(self):
        code='''import importlib.util, sys\nfrom pathlib import Path\nspec=importlib.util.spec_from_file_location("booster_fixture",sys.argv[1]); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\nroot=Path(sys.argv[2]); original=Path.rename\ndef changed(path,destination):\n    result=original(path,destination); (root/".booster-gc.lock").write_bytes(b"changed by fixture writer"); return result\nPath.rename=changed\nsys.argv=[sys.argv[1],"gc-apply","--root",str(root),"--manifest","manifest.json","--owner","test"]\nraise SystemExit(module.main())\n'''
        cli=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(ROOT/'scripts/booster.py'),str(self.root)],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1,cli.stdout+cli.stderr)
        result=json.loads(cli.stdout);self.assertTrue(result['reconciliation_required']);self.assertEqual(result['effect'],'UNKNOWN')
        self.assertEqual(result['error_type'],'ValueError');self.assertEqual((self.root/'.booster-gc.lock').read_bytes(),b'changed by fixture writer')
        self.assertFalse(self.file.exists());self.assertEqual(len(list((self.root/'.booster-quarantine').glob('*/recovery.json'))),1)
    def test_gc_cli_preserves_first_permission_denial_when_lock_also_changes(self):
        code='''import importlib.util, sys\nfrom pathlib import Path\nspec=importlib.util.spec_from_file_location("booster_fixture",sys.argv[1]); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\nroot=Path(sys.argv[2])\ndef denied(path,destination):\n    (root/".booster-gc.lock").write_bytes(b"changed by fixture writer"); raise PermissionError("fixture access denied")\nPath.rename=denied\nsys.argv=[sys.argv[1],"gc-apply","--root",str(root),"--manifest","manifest.json","--owner","test"]\nraise SystemExit(module.main())\n'''
        cli=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(ROOT/'scripts/booster.py'),str(self.root)],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1,cli.stdout+cli.stderr)
        result=json.loads(cli.stdout);self.assertTrue(result['reconciliation_required'])
        self.assertEqual(result['first_error_type'],'PermissionError');self.assertIn('fixture access denied',result['first_error'])
        self.assertTrue(self.file.exists());self.assertEqual((self.root/'.booster-gc.lock').read_bytes(),b'changed by fixture writer')
    @unittest.skipUnless(sys.platform=='win32','Windows junction test')
    def test_checked_refuses_broken_junction(self):
        target=self.root/'junction-target';target.mkdir();junction=self.root/'broken-junction'
        made=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(target)],capture_output=True,text=True)
        self.assertEqual(made.returncode,0,made.stdout+made.stderr);self.addCleanup(junction.rmdir)
        target.rmdir()
        with self.assertRaisesRegex(ValueError,'links/reparse'):b.checked(self.root,'broken-junction/item')
    def test_hardlink(self):
        (self.root/'.booster-tmp/alias.txt').hardlink_to(self.file)
        self.assertEqual(self.run_gc(True)['moved'],[])
    def test_cli_nested_error_json(self):
        p=plan();p['next']=None;p['nodes'][0].update(status='verified',evidence=None)
        target=self.root/'invalid-plan.json';target.write_text(json.dumps(p))
        result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/booster.py'),'validate',str(target)],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertEqual(json.loads(result.stdout),{'error':'evidence must be object'})
        self.assertEqual(result.stderr,'')
    def test_malformed_manifest(self):
        for value in (None, [], {'owner':'test','files':[None]}):
            (self.root/'manifest.json').write_text(json.dumps(value))
            with self.subTest(manifest=value),self.assertRaises(ValueError): self.run_gc(True)
            self.assertTrue(self.file.exists())
    def test_self_check_without_site_packages(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),'self-check'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        outcome=json.loads(result.stdout)
        self.assertEqual(outcome['validator'],'bundled-stdlib')
        self.assertEqual(outcome['codex_repo_registration'],'present_valid')
        self.assertEqual(outcome['canonical_source_sha256'],hashlib.sha256((ROOT/'SKILL.md').read_bytes()).hexdigest())
        self.assertEqual(outcome['canonical_source_sha256'],outcome['registration_target_sha256'])
        self.assertEqual(outcome['python_version'],'.'.join(str(n) for n in sys.version_info[:3]))
        self.assertFalse(outcome['agent_discovery_verified'])
    def test_codex_registration_rejects_mismatches(self):
        canonical=(ROOT/'SKILL.md').read_text(encoding='utf-8').split('---\n',2)[1]
        expected={line.partition(':')[0]:line.partition(':')[2].strip() for line in canonical.splitlines()}
        entry=(ROOT/'.agents/skills/booster-ai/SKILL.md').read_text(encoding='utf-8')
        self.assertTrue(b.check_codex_entry(entry,expected))
        for changed in (entry.replace('name: booster-ai','name: different'),
                        entry.replace('../../../SKILL.md','../../../missing.md'),
                        entry.replace('description: ', 'description: changed ', 1),
                        entry.replace('name: booster-ai\n', 'name: booster-ai\nname: booster-ai\n',1)):
            with self.subTest(change=changed[:90]),self.assertRaises(ValueError):
                b.check_codex_entry(changed,expected)
    def test_self_check_reports_missing_and_broken_registration(self):
        target=self.root/'portable-copy';target.mkdir()
        for name in ('SKILL.md','README.md'):
            shutil.copy2(ROOT/name,target/name)
        for name in ('scripts','references','tests','solutions'):
            shutil.copytree(ROOT/name,target/name)
        missing=b.self_check(target)
        self.assertEqual(missing['codex_repo_registration'],'not_present')
        self.assertIsNone(missing['registration_target_sha256'])
        self.assertFalse(missing['agent_discovery_verified'])
        entry=target/'.agents/skills/booster-ai/SKILL.md';entry.parent.mkdir(parents=True)
        entry.write_text('---\nname: broken\ndescription: broken\n---\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'metadata differs'):
            b.self_check(target)
    def test_self_check_missing_resource(self):
        target=self.root/'skill-fixture';target.mkdir()
        (target/'SKILL.md').write_text('---\nname: booster-ai\ndescription: test\n---\n[missing](references/missing.md)\n')
        with self.assertRaisesRegex(ValueError,'missing bundled resource'):b.self_check(target)
    @unittest.skipUnless(sys.platform=='win32','Windows junction test')
    def test_self_check_rejects_junction_root(self):
        target=self.root/'actual';target.mkdir()
        marker=target/'preserve.txt';marker.write_text('preserve')
        junction=self.root/'linked'
        made=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(target)],capture_output=True,text=True)
        self.assertEqual(made.returncode,0,made.stdout+made.stderr);self.addCleanup(junction.rmdir)
        cli=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),'self-check','--root',str(junction)],capture_output=True,text=True)
        self.assertEqual(cli.returncode,1,cli.stdout+cli.stderr)
        self.assertIn('root link forbidden',json.loads(cli.stdout)['error'])
        with self.assertRaisesRegex(ValueError,'root link forbidden'):b.schema_status(junction)
        self.assertEqual(marker.read_text(),'preserve')
    def test_partials_init_new_standard_and_idempotence(self):
        first=b.partials_init(self.root)
        index=self.root/'_boosterAI/_partials/README.md'
        self.assertTrue(first['created'])
        self.assertFalse(first['preserved_existing'])
        self.assertEqual(first['directory'],'_boosterAI/_partials')
        self.assertEqual(first['index'],'_boosterAI/_partials/README.md')
        self.assertIsNone(first['legacy_location'])
        self.assertIsNone(first['legacy_root_location'])
        self.assertTrue(index.is_file())
        self.assertFalse((self.root/'_partials').exists())
        original=index.read_bytes();before=index.stat()
        second=b.partials_init(self.root)
        after=index.stat()
        self.assertFalse(second['created'])
        self.assertTrue(second['preserved_existing'])
        self.assertEqual(second['legacy_location'],'_boosterAI/_partials')
        self.assertIsNone(second['legacy_root_location'])
        self.assertEqual(index.read_bytes(),original)
        self.assertEqual((after.st_ino,after.st_size,after.st_mtime_ns),
                         (before.st_ino,before.st_size,before.st_mtime_ns))

    def test_partials_init_preserves_existing(self):
        standard=self.root/'_boosterAI/_partials';standard.mkdir(parents=True)
        legacy=self.root/'_partials';legacy.mkdir()
        files={standard/'README.md':b'existing standard notes\n',
               standard/'piece.py':b'existing standard code\n',
               legacy/'README.md':b'existing legacy notes\n',
               legacy/'piece.py':b'existing legacy code\n'}
        for path,content in files.items():path.write_bytes(content)
        before={path:(path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns) for path in files}
        first=b.partials_init(self.root)
        second=b.partials_init(self.root)
        self.assertFalse(first['created']);self.assertFalse(second['created'])
        self.assertEqual(first['legacy_location'],'_boosterAI/_partials')
        self.assertEqual(first['legacy_root_location'],'_partials')
        self.assertEqual(first['index'],'_boosterAI/_partials/README.md')
        for path,original in before.items():
            self.assertEqual((path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns),original)

    def test_partials_init_preserves_legacy_root_file(self):
        legacy=self.root/'_partials';legacy.write_bytes(b'owner file is not a directory')
        before=(legacy.read_bytes(),legacy.stat().st_ino,legacy.stat().st_mtime_ns)
        first=b.partials_init(self.root)
        self.assertTrue(first['created'])
        self.assertIsNone(first['legacy_location'])
        self.assertEqual(first['legacy_root_location'],'_partials')
        self.assertTrue((self.root/'_boosterAI/_partials/README.md').is_file())
        self.assertEqual((legacy.read_bytes(),legacy.stat().st_ino,legacy.stat().st_mtime_ns),before)
        self.assertFalse(b.partials_init(self.root)['created'])
        self.assertEqual((legacy.read_bytes(),legacy.stat().st_ino,legacy.stat().st_mtime_ns),before)

    def test_partials_init_preserves_legacy_directory_when_standard_is_missing(self):
        legacy=self.root/'_partials';legacy.mkdir()
        existing=legacy/'README.md';existing.write_bytes(b'legacy project notes')
        before=(existing.read_bytes(),existing.stat().st_ino,existing.stat().st_mtime_ns)
        report=b.partials_init(self.root)
        self.assertTrue(report['created'])
        self.assertIsNone(report['legacy_location'])
        self.assertEqual(report['legacy_root_location'],'_partials')
        self.assertTrue((self.root/'_boosterAI/_partials/README.md').is_file())
        self.assertEqual((existing.read_bytes(),existing.stat().st_ino,existing.stat().st_mtime_ns),before)
    def test_partials_real_functions_then_integration(self):
        result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),'partials-init','--root',str(self.root)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        partials=self.root/'_boosterAI/_partials'
        first=partials/'normalize_ab12cd34.py';first.write_text('def normalize(value):\n    """Normalize a text value for the project fixture.\n\n    Accept a string and return its stripped lower-case form without side effects.\n    A value without the string methods raises an error to the caller.\n    """\n    return value.strip().lower()\n')
        # Execute the actual fixture function in its intended Python runtime before adding its dependent function.
        probe='from normalize_ab12cd34 import normalize; assert normalize("  ALICE ") == "alice"; print("normalized")'
        checked=subprocess.run([sys.executable,'-S','-B','-c',probe],cwd=partials,capture_output=True,text=True)
        self.assertEqual(checked.returncode,0,checked.stderr)
        self.assertEqual(checked.stdout.strip(),'normalized')
        second=partials/'greet_1f2e3d4c.py';second.write_text('from normalize_ab12cd34 import normalize\ndef greet(value):\n    """Compose a greeting for a supplied text value.\n\n    Normalize the input using the verified helper and return a new string.\n    This function has no side effects and propagates invalid input errors.\n    """\n    return "Hello " + normalize(value)\n')
        app=self.root/'app.py';app.write_text('import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).parent/"_boosterAI"/"_partials"))\nfrom greet_1f2e3d4c import greet\nprint(greet(sys.argv[1]))\n')
        integrated=subprocess.run([sys.executable,'-I','-S','-B',str(app),' ALICE '],capture_output=True,text=True)
        self.assertEqual(integrated.returncode,0,integrated.stderr)
        self.assertEqual(integrated.stdout.strip(),'Hello alice')
        self.assertTrue((partials/'README.md').is_file())
    def test_partials_refuses_missing_root_and_file_collision(self):
        with self.assertRaises(ValueError):b.partials_init(self.root/'absent')
        owned=self.root/'_boosterAI';owned.mkdir()
        collision=owned/'_partials';collision.write_text('do not overwrite')
        with self.assertRaises(OSError):b.partials_init(self.root)
        self.assertEqual(collision.read_text(),'do not overwrite')
    def test_workspace_real_cli_and_preservation(self):
        source=self.root/'existing-schema.md';source.write_text('# Existing schema\nunchanged source')
        record=self.root/'existing-record.md';record.write_text('existing record owner')
        args=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),'workspace-init','--root',str(self.root),'--records-existing','existing-record.md','--schema','existing-schema.md']
        result=subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual((self.root/'_boosterAI/algorithm.md').read_bytes(),source.read_bytes())
        self.assertEqual(record.read_text(),'existing record owner')
        self.assertFalse((self.root/'PROJECT_RECORDS.md').exists())
        self.assertTrue((self.root/'_boosterAI/_partials/README.md').is_file())
        self.assertFalse((self.root/'_partials').exists())
        self.assertIn('`_partials/README.md`',(self.root/'_boosterAI/README.md').read_text())
        self.assertFalse(b.schema_status(self.root)['source_changed'])
        source.write_text('updated original')
        self.assertTrue(b.schema_status(self.root)['source_changed'])
        self.assertEqual((self.root/'_boosterAI/algorithm.md').read_text(),'# Existing schema\nunchanged source')
        with self.assertRaisesRegex(ValueError,'reconcile'):b.workspace_init(self.root, schema='existing-schema.md')
    def test_workspace_new_records_no_overwrite(self):
        result=b.workspace_init(self.root,create_records=True)
        self.assertEqual(result['project_record'],'PROJECT_RECORDS.md')
        record=self.root/'PROJECT_RECORDS.md';record.write_text('user added history')
        algorithm=self.root/'_boosterAI/algorithm.md';algorithm.write_text('owner algorithm')
        b.workspace_init(self.root,create_records=True)
        self.assertEqual(record.read_text(),'user added history')
        self.assertEqual(algorithm.read_text(),'owner algorithm')
        with self.assertRaises(ValueError):b.workspace_init(self.root,records_existing='PROJECT_RECORDS.md',create_records=True)

    def test_workspace_new_cli_scaffolds_only_nested_partials(self):
        args=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),
              'workspace-init','--root',str(self.root),'--create-records']
        result=subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['directory'],'_boosterAI/_partials')
        self.assertEqual(report['index'],'_boosterAI/_partials/README.md')
        self.assertTrue(report['created'])
        self.assertTrue((self.root/'PROJECT_RECORDS.md').is_file())
        self.assertTrue((self.root/'_boosterAI/algorithm.md').is_file())
        self.assertTrue((self.root/'_boosterAI/_partials/README.md').is_file())
        self.assertFalse((self.root/'_partials').exists())

    def test_workspace_cli_preserves_existing_overview_and_both_partials(self):
        standard=self.root/'_boosterAI/_partials';standard.mkdir(parents=True)
        legacy=self.root/'_partials';legacy.mkdir()
        files={self.root/'existing-record.md':b'existing project record',
               self.root/'_boosterAI/algorithm.md':b'existing algorithm',
               self.root/'_boosterAI/README.md':b'existing workspace overview',
               standard/'README.md':b'existing standard index',
               standard/'piece.py':b'existing standard source',
               legacy/'README.md':b'existing legacy index',
               legacy/'piece.py':b'existing legacy source'}
        for path,content in files.items():path.write_bytes(content)
        before={path:(path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns) for path in files}
        args=[sys.executable,'-I','-S','-B',str(ROOT/'scripts/booster.py'),
              'workspace-init','--root',str(self.root),'--records-existing','existing-record.md']
        result=subprocess.run(args,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        report=json.loads(result.stdout)
        self.assertFalse(report['created'])
        self.assertEqual(report['legacy_location'],'_boosterAI/_partials')
        self.assertEqual(report['legacy_root_location'],'_partials')
        self.assertEqual(report['index'],'_boosterAI/_partials/README.md')
        for path,original in before.items():
            self.assertEqual((path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns),original)
    def test_cli_real_process(self):
        p=self.root/'plan.json';p.write_text(json.dumps(plan()))
        result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/booster.py'),'validate',str(p)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout);self.assertTrue(json.loads(result.stdout)['valid'])

if __name__=='__main__':unittest.main(verbosity=2)
