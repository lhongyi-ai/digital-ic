#!/usr/bin/env python3
"""Compare measured simulator cycles and completed full-system route reports."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
rows=[]
for variant,core_suffix in (("single_bin","artifacts"),("neighbor3","model_neighbor")):
    group=[]
    for lanes in (1,4):
        directory=ROOT/"build"/f"board_{'neighbor_' if variant=='neighbor3' else ''}l{lanes}"
        core=ROOT/"build"/f"core_l{lanes}_{core_suffix}"
        paths=[directory/"report.json",directory/"timing.json",core/"regression.json"]
        if not all(p.exists() for p in paths):continue
        report,timing,regression=[json.loads(p.read_text()) for p in paths]
        cells=report["synthesis_cells"]
        cycles=regression.get("cycles",regression.get("stage_cycles"))
        if cycles is None:
            cycles=regression.get("reference_stage_cycles")
        row={"variant":variant,"lanes":lanes,"target_mhz":12,"model_sha256":report["model_sha256"],
             "lut4":cells.get("SB_LUT4",0),"registers":sum(v for k,v in cells.items() if k.startswith("SB_DFF")),
             "packed_logic_cells":timing["utilization"]["ICESTORM_LC"]["used"],
             "dsp":cells.get("SB_MAC16",0),"ebr":cells.get("SB_RAM40_4K",0),"spram":cells.get("SB_SPRAM256KA",0),
             "post_route_fmax_mhz":min(v["achieved"] for v in timing["fmax"].values()),
             "cycle_report":cycles,"raw_regression_path":str(paths[2].relative_to(ROOT)),
             "normal_window_ms":1024/12000*1000,"physical_measurement":False,"power":"not measured"}
        for candidate in (core/"fixed_rate/fixed_rate.json",core/"fixed_rate_32.json",core/"fixed_rate/fixed_rate_32.json"):
            if candidate.exists():row[candidate.stem]=json.loads(candidate.read_text())
        group.append(row)
    if len(group)==2 and group[0]["model_sha256"]!=group[1]["model_sha256"]:
        raise ValueError("Architecture comparison requires identical model hashes")
    rows.extend(group)
out=ROOT/"artifacts/reports/architecture.json"
out.write_text(json.dumps({"schema_version":1,"measurements":rows,
    "cycle_scope":"Core activity cycles exclude source acquisition, IDLE/FINISH handoff, output stalls and Flash/USB transfer. Fixed-rate timestamp tests separately measure end-to-end core latency.",
    "clock_scope":"nextpnr internal synchronous timing at 12 MHz; external electrical/SPI timing still requires board measurements.",
    "not_measured":["power","actual board latency","USB host Flash read/write time"]},indent=2)+"\n")
lines=["# Architecture comparison","","Resources come from place-and-route of the full replay system; cycles come from RTL simulation. At this historical stage, no hardware or power measurements had been made.","",
       "| Features | MAC | LUT4 | Registers | Packed LC / 5280 | DSP | EBR / 30 | SPRAM / 4 | Post-route estimated Fmax |",
       "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
for r in rows:
    lines.append(f"| {r['variant']} | {r['lanes']} | {r['lut4']} | {r['registers']} | {r['packed_logic_cells']} | {r['dsp']} | {r['ebr']} | {r['spram']} | {r['post_route_fmax_mhz']:.2f} MHz |")
lines += ["","| Features | MAC | DC removal/Hann | DFT | Power/quantization | MLP | Total active cycles | Active time at 12 MHz |",
          "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
for r in rows:
    c=r["cycle_report"]
    if c:
        lines.append(f"| {r['variant']} | {r['lanes']} | {c['cycles_pre']} | {c['cycles_dft']} | {c['cycles_power']} | {c['cycles_nn']} | {c['cycles_total']} | {c['cycles_total']/12000:.3f} ms |")
lines += ["","A separate 32-frame test records cycle-level timestamps. The following are actual simulation time differences, not estimates from theoretical throughput.", "",
          "| Features | MAC | First sample to output | Last sample to output | Output frame interval |",
          "| --- | ---: | ---: | ---: | ---: |"]
for r in rows:
    t=r.get("fixed_rate_32",{}).get("normal_timing_cycles",{})
    if t:
        lines.append(f"| {r['variant']} | {r['lanes']} | {t['first_sample_to_result_min']/12000:.3f} ms | {t['last_sample_to_result_min']/12000:.3f} ms | {t['output_interval_min']/12000:.3f} ms |")
lines += ["","The timestamp test uses FIFO depth 4; the full-board replay uses two slots to save resources. Both reach maximum occupancy 1 at normal cadence. The full Flash chain has separate simulation evidence; overload results must retain their own configurations and cannot be conflated."]
lines += ["","All comparisons use the same model, algorithm widths, and 12 MHz target clock. LUT4 counts differ from packed LC counts; assess UP5K capacity using LC.", "",
          "`cycles_total` sums the active cycles of DC removal/windowing, DFT, power/quantization, and neural-network stages. It excludes input wait, queuing, output backpressure, and Flash transfers. It is not the total latency from host input to host result.", "",
          "The fixed-cadence test produces one sample every 1000 clocks independently of ready. Replaying 1000 frames verifies sustained processing; it does not represent 1000 independent training/test recordings. Each window lasts 85.333 ms.", "",
          "Detailed stage cycles, fixed-cadence counters, and latency distributions are in architecture.json. Power is unmeasured; place-and-route success is neither a hardware test pass nor ASIC sign-off.",""]
(ROOT/"artifacts/reports/architecture.md").write_text("\n".join(lines))
print(out)
