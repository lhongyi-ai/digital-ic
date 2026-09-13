"""Positive and negative control: unsupported/disabled assertions must not pass."""
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_support import run_verilator_build, configure_verilator_environment, input_hashes, require_unchanged
BUILD = ROOT / "build/sva_smoke"


def main():
    configure_verilator_environment()
    BUILD.mkdir(parents=True, exist_ok=True)
    evidence = BUILD / "result.json"
    evidence.unlink(missing_ok=True)
    version = subprocess.check_output(["verilator", "--version"], text=True).strip()
    source_hashes = input_hashes([ROOT/"formal/sva_smoke.sv", Path(__file__).resolve()])
    command = ["verilator", "--binary", "--timing", "--assert", "-Wno-fatal",
               "--top-module", "sva_smoke", "--Mdir", str(BUILD),
               str(ROOT / "formal/sva_smoke.sv")]
    with (BUILD / "compile.log").open("w") as stream:
        run_verilator_build(command, BUILD, "sva_smoke", stdout=stream)
    good = subprocess.run([str(BUILD / "Vsva_smoke")], capture_output=True, text=True)
    bad = subprocess.run([str(BUILD / "Vsva_smoke"), "+FAIL"], capture_output=True, text=True)
    (BUILD / "positive.log").write_text(good.stdout + good.stderr)
    (BUILD / "negative.log").write_text(bad.stdout + bad.stderr)
    assert good.returncode == 0 and "SVA_SMOKE_PASS" in good.stdout
    assert bad.returncode != 0 and "SVA_INCREMENT_FAILURE" in bad.stdout + bad.stderr
    require_unchanged(source_hashes)
    evidence.write_text(json.dumps({"source_sha256":source_hashes,"verilator": version,
                                   "subset": "clocked assert property, disable iff, |=>, $past",
                                   "positive_pass": True,
                                   "negative_control_detected": True,
                                   "negative_returncode": bad.returncode}, indent=2) + "\n")
    print(evidence)


if __name__ == "__main__":
    main()
