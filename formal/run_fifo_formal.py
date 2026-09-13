"""Run the committed bounded checks; never substitute simulation for formal."""
import argparse
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from build_support import input_hashes, require_unchanged
TASKS = [f"{mode}_d{depth}" for mode in ("bmc", "cover") for depth in (1, 3, 4)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks", nargs="*", choices=TASKS)
    args = parser.parse_args()
    evidence = ROOT / "build/formal/fifo_results.json"
    evidence.unlink(missing_ok=True)
    source_hashes = input_hashes([ROOT/"rtl/core/sync_fifo.sv", ROOT/"formal/fifo_harness.sv", ROOT/"formal/fifo.sby", Path(__file__).resolve()])
    results = []
    for task in args.tasks or TASKS:
        destination = ROOT / "build/formal" / f"fifo_{task}"
        command = ["sby", "-f", "-d", str(destination), "fifo.sby", task]
        result = subprocess.run(command, cwd=ROOT / "formal", check=False)
        status_file = destination / "status"
        status = status_file.read_text().strip() if status_file.exists() else "MISSING"
        results.append({"task": task, "bound": 64, "width": 16,
                        "depth": int(task.rsplit("d", 1)[1]),
                        "status": status, "returncode": result.returncode})
        assert result.returncode == 0 and status.split()[0] == "PASS", results[-1]
    evidence = ROOT / "build/formal/fifo_results.json"
    require_unchanged(source_hashes)
    evidence.write_text(json.dumps({"source_sha256":source_hashes,"scope": "bounded safety and reachable covers, not unbounded proof",
                                   "results": results}, indent=2) + "\n")
    print(evidence)


if __name__ == "__main__":
    main()
