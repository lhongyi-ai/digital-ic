"""Synthetic artifacts exercise the authorization gate; never evidence of FPGA runs."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('portability_release',Path(__file__).resolve().parents[1]/'scripts/portability_release.py')
g=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(g)

class PortabilityGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        self.base=self.root/g.BASE;self.base.mkdir(parents=True)
        self.put('rtl/core/known_spectral_core.sv','synthetic core')
        for name in ('run_known_hardware.py','audit_known_hardware.py','portability_release.py'):
            self.put('scripts/'+name,'synthetic script')
        self.models={m:self.put(f'artifacts/acoustic-known-release-v1/id{m}/model.json',{'fixture':True,'id':m}) for m in ('00','02','04','06')}
        names={f'artifacts/acoustic-known-release-v1/id{m}/model.json':g.sha(p) for m,p in self.models.items()}
        freeze=self.put('artifacts/acoustic-known-deployment-v1/freeze.json',{'sha256':names})
        result=self.put('artifacts/acoustic-known-final-v1/results.json',{'passed':True,'groups':{'fixture':{'passed':True}},'deployment_sha256':g.sha(freeze)})
        audit=self.put('artifacts/acoustic-known-final-v1/audit.json',{'passed':True,'results_sha256':g.sha(result)})
        entries={}
        for name in [*names,str(freeze.relative_to(self.root)),str(result.relative_to(self.root)),str(audit.relative_to(self.root))]:
            archive=self.root/g.BASE/'baseline/files'/name;archive.parent.mkdir(parents=True,exist_ok=True);archive.write_bytes((self.root/name).read_bytes())
            entries[name]={'sha256':g.sha(archive),'archive':str(archive.relative_to(self.root))}
        manifest=self.put(str(g.BASE/'baseline/manifest.json'),{'files':entries})
        self.records={m:[{'name':f'{m}-record{i}','npy_sha256':str(i)} for i in range(7 if m=='00' else 2)] for m in self.models}
        self.put(str(g.BASE/'protocol.json'),{'baseline_manifest_sha256':g.sha(manifest),'models':{m:g.sha(p) for m,p in self.models.items()},'records':self.records,'part':'xc7a35tcpg236-1','goals':{'amd_delay_reduction_min':.1,'ice40_delay_regression_max':.02,'cycles_increase_max':.01}})
        self.index={}
        for slot in g.required_slots():
            r={'passed':True,'bindings':{'rtl/core/known_spectral_core.sv':g.sha(self.root/'rtl/core/known_spectral_core.sv')}}
            parts=slot.split('-')
            if slot not in ('ram-contract','edge-contract','flash-fixture'):
                r['quant_pipeline']=int(parts[1]=='C')
                if parts[2]!='small':
                    m=parts[2];l=int(parts[3][1:]);r.update(machine=m,lanes=l,model_sha256=g.sha(self.models[m]))
            if slot.startswith(('native-','xsim-','flash-C-')) and not slot.endswith('small'):
                count=7 if slot.startswith('native-') and m=='00' else 2
                if slot.startswith('flash-') or slot=='xsim-C-00-l1':count=1
                r.update(windows=count*156,samples=count*159744,records=self.records[m][:count],intermediate_checks=count*156,dropped_samples=0)
            if slot.startswith('native-'):
                inc=512 if r['quant_pipeline'] else 0
                r.update(sample_period_cycles=1500 if l==1 else 750,backpressure_cycles=0,
                         stages=[dict(pre=100,dft=100000,power=100,nn=1000+inc,total=101200+inc) for _ in range(7)])
            if slot.startswith('ice-'):
                r.update(seed=int(parts[4][1:]),abc_dff=True,nominal_clock_hz=12000000,fmax={'clk':{'achieved':14.,'constraint':13.2}},utilization={'LC':{'used':100,'available':5280}})
            if slot.startswith(('amd-','xsim-')):
                r.update(returncode=0,vivado='2024.2',vivado_build='5239630')
            if slot.startswith('amd-'):
                r.update(part='xc7a35tcpg236-1',clock_period_ns=20,io_delay_ns=2,blackboxes=0,bram_count=1,
                         timing=dict(internal_delay_ns=10. if parts[1]=='B' else 8.,wns_ns=10.,tns_ns=0.,hold_wns_ns=.1,hold_tns_ns=0.,unconstrained_paths=0))
            if slot.startswith('xsim-'):
                r['completion_marker']=True
                if not slot.endswith('small'):
                    inc=512 if r['quant_pipeline'] else 0
                    r['stages']=[dict(pre=100,dft=100000,power=100,nn=1000+inc,total=101200+inc) for _ in range(count)]
            if slot.startswith('flash-C-'):r.update(actual_spi_transport=True,actual_rtl_core=True,fixture=False,period=1500 if l==1 else 750,result=dict(errors=0,protocol_errors=0,generated=159744,accepted=159744))
            if slot=='ram-contract':r.update(contract='spram16k',backends=['reference','amd'])
            if slot=='edge-contract':r.update(cases=['rne','saturation','stall','reset_quant','frame_id','back_to_back'])
            if slot=='flash-fixture':r.update(fixture=True)
            path=self.put('build/fixture/'+slot+'/report.json',r)
            if slot.startswith('ice-'):
                board=self.put(str((path.parent/'board.bin').relative_to(self.root)),'synthetic bitstream')
                r['bitstream_sha256']=g.sha(board);self.put(str(path.relative_to(self.root)),r)
            self.index[slot]=str(path.relative_to(self.root))
        self.put(str(g.BASE/'evidence-index.json'),self.index)
    def put(self,name,content):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(content) if isinstance(content,(dict,list)) else content);return p
    def change(self,slot,fn):
        path=self.root/self.index[slot];r=json.loads(path.read_text());fn(r);self.put(str(path.relative_to(self.root)),r)
    def test_valid_fixture_release_rechecks_all_evidence(self):
        release=g.check_release(self.root);path=self.put(str(g.BASE/'release.json'),release)
        self.assertEqual(g.verify_manifest(path,self.root),release)
    def test_missing_report_never_freezes(self):
        (self.root/self.index['xsim-C-06-l4']).unlink()
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_model_tamper_rejected(self):
        self.models['02'].write_text('tampered')
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_archived_dependency_tamper_rejected(self):
        p=self.root/g.BASE/'baseline/files/artifacts/acoustic-known-final-v1/audit.json';p.write_text('{}')
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_source_tamper_rejected(self):
        (self.root/'rtl/core/known_spectral_core.sv').write_text('tampered')
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_bitstream_tamper_rejected(self):
        (self.root/self.index['ice-C-00-l4-s1']).with_name('board.bin').write_text('tampered')
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_report_tamper_after_freeze_rejected(self):
        path=self.put(str(g.BASE/'release.json'),g.check_release(self.root))
        self.change('native-C-00-l4',lambda r:r.update(windows=1))
        with self.assertRaises(g.GateError):g.verify_manifest(path,self.root)
    def test_missing_boundary_scenario_rejected(self):
        self.change('edge-contract',lambda r:r['cases'].remove('reset_quant'))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_wrong_cycles_rejected(self):
        self.change('native-C-00-l4',lambda r:r['stages'][0].update(nn=1513))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_characterization_baseline_may_miss_target(self):
        self.change('amd-B-00-l4',lambda r:r['timing'].update(wns_ns=-1.,tns_ns=-100.,hold_wns_ns=-.1,hold_tns_ns=-1.))
        self.assertTrue(g.check_release(self.root)['passed'])
    def test_characterization_baseline_must_still_be_constrained(self):
        self.change('amd-B-00-l4',lambda r:r['timing'].update(unconstrained_paths=1))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_failed_timing_and_no_improvement_rejected(self):
        for value in (-.1,):
            self.change('amd-C-00-l4',lambda r:r['timing'].update(wns_ns=value))
            with self.assertRaises(g.GateError):g.check_release(self.root)
        self.change('amd-C-00-l4',lambda r:r['timing'].update(wns_ns=1.,internal_delay_ns=9.5))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_mismatched_dataset_and_pipeline_rejected(self):
        self.change('native-C-00-l4',lambda r:r.update(quant_pipeline=0))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_xsim_stage_mismatch_even_with_same_total_rejected(self):
        def change(r):
            r['stages'][0]['pre'] += 1
            r['stages'][0]['nn'] -= 1
        self.change('xsim-C-02-l4',change)
        with self.assertRaisesRegex(g.GateError,'Vivado/native stage mismatch'):g.check_release(self.root)
    def test_xsim_missing_stage_receipt_rejected(self):
        self.change('xsim-C-00-l1',lambda r:r.update(stages=[]))
        with self.assertRaisesRegex(g.GateError,'Missing Vivado stage receipts'):g.check_release(self.root)
    def test_single_mac_synthesis_mapping_required(self):
        self.change('amd-C-00-l1',lambda r:r.pop('bram_count'))
        with self.assertRaisesRegex(g.GateError,'AMD RAM mapping failed'):g.check_release(self.root)
    def test_single_mac_synthesis_blackbox_rejected(self):
        self.change('amd-C-00-l1',lambda r:r.update(blackboxes=1))
        with self.assertRaisesRegex(g.GateError,'AMD RAM mapping failed'):g.check_release(self.root)
    def test_wrong_record_list_rejected(self):
        self.change('xsim-C-02-l4',lambda r:r['records'][0].update(name='holdout-record'))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_bad_cadence_rejected(self):
        self.change('native-C-00-l4',lambda r:r.update(sample_period_cycles=800))
        with self.assertRaises(g.GateError):g.check_release(self.root)
    def test_new_build_not_in_release_rejected(self):
        path=self.put(str(g.BASE/'release.json'),g.check_release(self.root))
        unrelated=self.put('build/unfrozen/report.json',{'passed':True,'quant_pipeline':1})
        with self.assertRaises(g.GateError):g.verify_manifest(path,self.root,unrelated)
    def test_path_traversal_rejected(self):
        with self.assertRaises(g.GateError):g.project_path(self.root,'../outside')

class VivadoUtilizationTest(unittest.TestCase):
    text = """Table of Contents
3. Memory
9. Black Boxes
10. Instantiated Netlists

3. Memory
---------
| Site Type | Used | Fixed |
| Block RAM Tile | 5.5 | 0 |
| RAMB36/FIFO* | 1 | 0 |
| RAMB18 | 9 | 0 |
| Slice LUTs | 1739 | 0 |
| Slice Registers | 1308 | 0 |
| DSPs | 7 | 0 |

9. Black Boxes
--------------
+----------+------+
| Ref Name | Used |
+----------+------+

10. Instantiated Netlists
-------------------------
+----------+------+
| Ref Name | Used |
+----------+------+
"""
    def synthetic_report(self,root):
        # Fixture data only: checks normalization, never presented as tool evidence.
        path=root/'build/run/report.json';path.parent.mkdir(parents=True)
        package=path.parent/'package';results=path.parent/'results';package.mkdir();results.mkdir()
        core=root/'rtl/core/known_spectral_core.sv';core.parent.mkdir(parents=True);core.write_text('fixture')
        bindings={'rtl/core/known_spectral_core.sv':g.sha(core)}
        (package/'config.tcl').write_text('fixture')
        (package/'package.json').write_text(json.dumps(dict(bindings=bindings,params={},records=[])))
        (results/'run.log').write_text('Vivado v2024.2 SW Build 5239630\nVIVADO_PORTABILITY_COMPLETE')
        (results/'utilization.rpt').write_text(self.text)
        report=dict(passed=True,bindings=bindings,tool='Vivado',version='2024.2',params={},mode='synthesis',result={},
                    input_sha256={'config.tcl':g.sha(package/'config.tcl')},
                    output_sha256={name:g.sha(results/name) for name in ('run.log','utilization.rpt')})
        path.write_text(json.dumps(report));return path,report
    def test_raw_mapping_normalized_for_synthesis(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path,_=self.synthetic_report(root)
            report=g.validate_report(root,path)
            self.assertEqual(report['blackboxes'],0);self.assertEqual(report['bram_count'],10)
    def test_mapping_alias_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path,report=self.synthetic_report(root)
            report['blackboxes']=1;path.write_text(json.dumps(report))
            with self.assertRaisesRegex(g.GateError,'mapping report mismatch'):g.validate_report(root,path)
    def test_unbound_utilization_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();path,report=self.synthetic_report(root)
            report['output_sha256'].pop('utilization.rpt');path.write_text(json.dumps(report))
            with self.assertRaisesRegex(g.GateError,'not hash-bound'):g.validate_report(root,path)
    def test_actual_style_empty_blackbox_section_is_explicit_zero(self):
        result=g.parse_vivado_utilization(self.text)
        self.assertEqual(result['blackboxes'],0)
        self.assertEqual(result['bram_count'],10)
        self.assertEqual(result['bram_tiles'],5.5)
        self.assertEqual(result['lut'],1739)
    def test_blackbox_rows_are_counted(self):
        text=self.text.replace('10. Instantiated Netlists\n-------------------------', '| mystery_ram | 2 |\n\n10. Instantiated Netlists\n-------------------------')
        self.assertEqual(g.parse_vivado_utilization(text)['blackboxes'],2)
    def test_absent_blackbox_section_is_not_zero(self):
        text=self.text[:self.text.index('9. Black Boxes\n--------------')]
        with self.assertRaisesRegex(g.GateError,'Missing explicit Black Boxes'):g.parse_vivado_utilization(text)
    def test_mismatched_bram_counts_rejected(self):
        with self.assertRaisesRegex(g.GateError,'Inconsistent'):g.parse_vivado_utilization(self.text.replace('| RAMB18 | 9 |','| RAMB18 | 8 |'))
    def test_missing_bram_counts_rejected(self):
        with self.assertRaisesRegex(g.GateError,'Missing explicit RAMB18'):g.parse_vivado_utilization(self.text.replace('| RAMB18 | 9 | 0 |',''))
    def test_malformed_blackbox_section_rejected(self):
        text=self.text.replace('| Ref Name | Used |','| invalid | table |')
        with self.assertRaisesRegex(g.GateError,'Malformed Black Boxes'):g.parse_vivado_utilization(text)

if __name__=='__main__':unittest.main()
