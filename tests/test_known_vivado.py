import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from known_vivado_support import manifest,verify,dump,valid_run_id,validate_result
class PackageTests(unittest.TestCase):
    def test_tampering_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'rtl.sv').write_text('original');m=manifest(p);verify(p,m)
            (p/'rtl.sv').write_text('changed')
            with self.assertRaises(ValueError):verify(p,m)
            (p/'rtl.sv').unlink()
            with self.assertRaises(ValueError):verify(p,m)
    def test_paths(self):
        for name in ('../bad','a;rm','bad/dir',''):
            with self.assertRaises(ValueError):valid_run_id(name)
        with self.assertRaises(ValueError):verify('.',{'../private':'hash'})
    def test_nonzero_and_partial_never_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);dump(p/'status.json',{'exit_code':1})
            with self.assertRaises(RuntimeError):validate_result(p,'sim')
            dump(p/'status.json',{'exit_code':0});(p/'run.log').write_text('incomplete');dump(p/'outputs.json',manifest(p))
            with self.assertRaises(RuntimeError):validate_result(p,'sim')
            (p/'run.log').write_text('vivado v2024.2\nSW Build 5239630\nVIVADO_PORTABILITY_COMPLETE');dump(p/'simulation.json',{'passed':False});dump(p/'outputs.json',manifest(p))
            with self.assertRaises(RuntimeError):validate_result(p,'sim')
            dump(p/'simulation.json',{'passed':True});dump(p/'outputs.json',manifest(p));self.assertTrue(validate_result(p,'sim')['passed'])
            (p/'simulation.json').write_text('{}')
            with self.assertRaises(ValueError):validate_result(p,'sim')
if __name__=='__main__':unittest.main()
