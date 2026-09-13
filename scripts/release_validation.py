"""Validate the active release reports without depending on paused area tuning."""
import json
from pathlib import Path

from build_support import require_unchanged, require_xml_passed, sha


def validate_current_release(root):
    root = Path(root)
    records = []
    def read(relative):
        path = root/relative
        value = json.loads(path.read_text())
        records.append({"path": relative, "sha256": sha(path)})
        return value
    def bound(value, key):
        hashes=value.get(key)
        if not isinstance(hashes,dict) or not hashes:
            raise RuntimeError(f"Current release requires original {key} bindings")
        require_unchanged({str(root/name): checksum for name,checksum in hashes.items()})
    def simulator(directory):
        require_xml_passed(root/directory/"results.xml")
        receipt=read(f"{directory}/build_manifest.json")
        bound(receipt["manifest"],"input_sha256")
    for depth in (1,3,4):simulator(f"build/fifo_d{depth}")
    for mode,half in ((0,6),(3,6),(1,6),(2,6),(0,1),(3,1)):
        simulator(f"build/spi_master_m{mode}_h{half}")
    for rate in ("0a","0c","0d"):simulator(f"build/spi_sensor_m3_h6_r{rate}")
    for index in range(4):simulator(f"build/calibration_{index}")
    simulator("build/core_l4_artifacts/arithmetic")
    simulator("build/core_l4_quant_boundary")
    for lanes in (1,4):
        for tag in ("artifacts","model_neighbor"):
            base=f"build/core_l{lanes}_{tag}"
            simulator(base)
            report=read(f"{base}/regression.json")
            if report.get("status")!="passed" or report.get("frames",0)<1000:
                raise RuntimeError("Full 1000-frame core release regression required")
            dsp=f"build/core_dsp_l{lanes}_{tag}"
            simulator(dsp)
            directed=read(f"{dsp}/regression.json")
            if directed.get("status")!="passed" or directed.get("frames",0)<10:
                raise RuntimeError("All 10 DSP directed frames are required")
            paced=read(f"{base}/fixed_rate/fixed_rate.json")
            bound(read(f"{base}/fixed_rate/build_manifest.json")["manifest"],"input_sha256")
            if any(paced.get(name,{}).get("status")!="passed" for name in ("normal","overload_and_recovery")) or paced["normal"].get("output_frames",0)<1000:
                raise RuntimeError("Full 1000-frame paced release and overload recovery required")
    for name in ("flash_system","flash_system_neighbor","flash_system_neighbor_full_scan","sensor_spectrum"):
        simulator(f"build/{name}")
    for case in ("nominal","overflow","spectrum","spectrum_storage","spectrum_overlap","spectrum_short"):
        simulator(f"build/sensor_system_{case}")
    for name in ("board_l1","board_l4","board_neighbor_l1","board_neighbor_l4","sensor_board_800hz_spectrum"):
        base=f"build/{name}"
        report=read(f"{base}/report.json")
        bound(report,"input_sha256")
        timing=read(f"{base}/timing.json")
        if (not report.get("place_route_completed") or report.get("bitstream_sha256")!=sha(root/base/"board.bin")
            or not timing.get("fmax") or any(row["achieved"]<row["constraint"] for row in timing["fmax"].values())
            or not timing.get("utilization") or any(row["used"]>row["available"] for row in timing["utilization"].values())):
            raise RuntimeError(f"Current passing complete board build required: {base}")
    sva=read("build/sva_smoke/result.json")
    bound(sva,"source_sha256")
    if not sva.get("positive_pass") or not sva.get("negative_control_detected"):
        raise RuntimeError("SVA positive and negative controls required")
    fifo=read("build/formal/fifo_results.json")
    bound(fifo,"source_sha256")
    if len(fifo["results"])!=6 or any(r["returncode"]!=0 or not r["status"].startswith("PASS") for r in fifo["results"]):
        raise RuntimeError("Six bounded FIFO safety/cover checks required")
    replay=read("build/replay_fifo_upgrade/report.json")
    bound(replay,"source_sha256")
    if not replay.get("passed"):raise RuntimeError("Actual replay FIFO bounded check required")
    return {"status":"passed", "reports":records, "historical_field_l4_area_tuning":"excluded; no new capacity or optimization claim"}
