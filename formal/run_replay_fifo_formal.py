"""Bounded safety and reachable covers for the actual production replay FIFO."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "build/replay_fifo_upgrade"


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    results = []
    for task in ("bmc", "cover"):
        destination = DESTINATION / task
        result = subprocess.run(
            ["sby", "-f", "-d", str(destination), "replay_fifo.sby", task],
            cwd=ROOT / "formal", check=False,
        )
        status_file = destination / "status"
        status = status_file.read_text().strip() if status_file.exists() else "MISSING"
        results.append({"task": task, "bound": 64, "status": status,
                        "returncode": result.returncode})
    sources = ["rtl/upduino_replay.sv", "formal/replay_fifo_harness.sv", "formal/replay_fifo.sby"]
    report = {
        "scope": "actual replay_fifo, 49 payload bits, depth 2; bounded safety and reachable covers only",
        "environment": "reset on first sampled edge; later reset, input valid/data and output ready unconstrained",
        "not_claimed": ["unbounded proof", "liveness under arbitrary backpressure", "whole-system or physical-board correctness"],
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
        "results": results,
        "passed": all(r["returncode"] == 0 and r["status"].split()[0] == "PASS" for r in results),
    }
    (DESTINATION / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(DESTINATION / "report.json")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
