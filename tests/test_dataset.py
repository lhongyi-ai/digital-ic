import io
import json
import numpy as np
from scipy.io import savemat
from vibfpga import dataset


def test_exact_record_split_and_subset():
    rows = dataset.records()
    assert len(rows) == 36
    assert len({r.record_id for r in rows}) == 36
    assert {r.split: sum(s.split == r.split for s in rows) for r in rows} == {"train":18,"validation":9,"test":9}
    assert all(r.sample_rate_hz == 12000 and r.channel == "DE" for r in rows)
    assert all(r.outer_position == "6:00" for r in rows if r.class_name == "outer_race")
    assert not {97,98,99,100}.intersection(r.record_id for r in rows)
    assert {r.load_hp for r in rows if r.split == "train"} == {0,1}
    assert {r.load_hp for r in rows if r.split == "validation"} == {2}
    assert {r.load_hp for r in rows if r.split == "test"} == {3}


def test_wrong_first_mat_variable_cannot_leak_neighbor_record(tmp_path):
    record = dataset.Record(99,0,"test_fixture","none",2,"validation","X099_DE_time")
    stream = io.BytesIO()
    savemat(stream,{"X098_DE_time":np.array([999.,999.]),"X099_DE_time":np.array([1.,2.,3.])})
    payload = stream.getvalue()
    (tmp_path/"99.mat").write_bytes(payload)
    (tmp_path/"manifest.json").write_text(json.dumps({"records":[{"record_id":99,"sha256":dataset.sha256(payload)}]}))
    np.testing.assert_array_equal(dataset.load_record(tmp_path,record),[1.,2.,3.])


def test_raw_gain_never_reads_validation_or_test(monkeypatch):
    observed = []
    def mock_load(directory,record):
        assert record.split == "train"
        observed.append(record.record_id)
        return np.array([-2.,1.])
    monkeypatch.setattr(dataset,"load_record",mock_load)
    result = dataset.fit_raw_scale("unused")
    assert len(observed) == 18
    assert result["gain"] == 16350.0


def test_windows_stay_inside_disjoint_records(monkeypatch):
    rows = [dataset.Record(1,0,"inner_race",".007",0,"train","X001_DE_time"),
            dataset.Record(2,1,"outer_race",".007",2,"validation","X002_DE_time")]
    monkeypatch.setattr(dataset,"records",lambda:rows)
    monkeypatch.setattr(dataset,"load_record",lambda directory,record:np.arange(13)+record.record_id)
    frames,y,meta,clipping = dataset.load_windows("unused","train",{"gain":1},n=4)
    assert frames.tolist() == [[1,2,3,4],[5,6,7,8],[9,10,11,12]]
    assert [m["sample_start"] for m in meta] == [0,4,8]
    assert all(m["record_id"] == 1 for m in meta)
    assert clipping[0]["discarded_tail_samples"] == 1
