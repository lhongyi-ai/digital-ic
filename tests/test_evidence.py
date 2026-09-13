import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("collect_evidence",Path(__file__).resolve().parents[1]/"scripts/collect_evidence.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_report_reader_does_not_convert_missing_empty_or_failed_to_pass(tmp_path):
    path=tmp_path/"results.xml"
    assert module.xml_summary(path)["status"]=="missing"
    for text in ("<testsuites/>",'<testsuite failures="1"><testcase/></testsuite>',
                 "<testsuite><testcase><failure/></testcase></testsuite>",
                 "<testsuite><testcase><skipped/></testcase></testsuite>"):
        path.write_text(text)
        assert module.xml_summary(path)["status"]=="failed"
    path.write_text("<testsuite><testcase/></testsuite>")
    assert module.xml_summary(path)["status"]=="passed"
    path.write_text("unfinished <")
    assert module.xml_summary(path)["status"]=="invalid"


def test_build_hash_binding_catches_changes_and_missing_required_inputs(tmp_path):
    path=tmp_path/"core.sv"
    path.write_text("original rtl")
    report={"input_sha256":{"core.sv":module.digest(path)}}
    assert module.verify_input_hashes(report,tmp_path,["core.sv"])["status"]=="passed"
    assert module.verify_input_hashes(report,tmp_path,["core.sv","weights.hex"])["status"]=="failed"
    path.write_text("changed rtl")
    result=module.verify_input_hashes(report,tmp_path,["core.sv"])
    assert result["status"]=="failed" and result["mismatches"]==["core.sv"]
    path.unlink()
    assert module.verify_input_hashes(report,tmp_path)["status"]=="failed"
    assert module.verify_input_hashes({},tmp_path)["status"]=="unavailable"
