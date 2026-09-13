"""Map requirements to generated evidence; missing results remain NOT_RUN."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCENARIOS = {
    "FIFO-RESET": ["reset_empty", "reset_nonempty"],
    "FIFO-BOUNDARY": ["empty_read_blocked", "full_write_blocked"],
    "FIFO-EXCHANGE": ["full_pop_push"],
    "FIFO-STALL": ["output_stall", "input_gap"],
    "FIFO-ORDER": ["push", "pop", "wraparound_traffic"],
}


def main():
    simulation_file = ROOT / "build/fifo_scenario_coverage.json"
    runs = json.loads(simulation_file.read_text())["runs"] if simulation_file.exists() else []
    requirements = []
    for requirement, scenarios in SCENARIOS.items():
        matching = [run for run in runs if run["width"] == 16 and
                    all(run["scenario_counts"].get(key, 0) > 0 for key in scenarios)]
        requirements.append({"requirement": requirement, "scenarios": scenarios,
                             "simulation": "PASS" if {r["depth"] for r in matching} >= {1, 3, 4}
                             else "NOT_RUN_OR_INCOMPLETE"})
    formal = []
    for mode in ("bmc", "cover"):
        for depth in (1, 3, 4):
            status = ROOT / "build/formal" / f"fifo_{mode}_d{depth}" / "status"
            formal.append({"task": f"{mode}_d{depth}", "bound": 64,
                           "status": status.read_text().strip() if status.exists() else "NOT_RUN"})
    smoke = ROOT / "build/sva_smoke/result.json"
    report = {"requirements": requirements, "formal": formal,
              "sva_smoke": json.loads(smoke.read_text()) if smoke.exists() else {"status": "NOT_RUN"},
              "limits": ["Scenario counters are not line, branch, toggle, or FSM coverage.",
                         "Formal BMC covers only 64 sampled clock steps for the tested parameters.",
                         "No CDC, JTAG, ASIC signoff, board, sensor, or power claim is made."]}
    path = ROOT / "build/fifo_verification_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
