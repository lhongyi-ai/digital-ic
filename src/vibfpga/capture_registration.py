"""Register operator-labelled SEN1 captures; preserve every attempted import."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .project_profile import ROOT, load_profile, resolve_path
from .sensor import analyze_capture, sensor_log_to_csv

PHYSICAL = "physical_adxl345"
FIXTURE = "synthetic_pipeline_fixture"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value, *, exclusive=False):
    with Path(path).open("x" if exclusive else "w") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def capture_contract(root=ROOT):
    profile = load_profile("sen1-spectrum", root=root)
    template = json.loads((Path(root) / "data/field/manifest.template.json").read_text())
    if (template["odr_hz"], template["clock_hz"], template["axis"]) != (profile["sample_rate_hz"], profile["clock_hz"], profile["axis"]):
        raise ValueError("field manifest template and SEN1 profile disagree")
    return {k: template[k] for k in ("odr_hz", "clock_hz", "axis", "class_names")}


def validate_assignment(value, contract):
    if value.get("schema_version") != 1 or value.get("source_kind") not in (PHYSICAL, FIXTURE):
        raise ValueError("assignment requires schema 1 and explicit physical or synthetic source_kind")
    for key in ("record_id", "state", "session_id", "installation_id", "apparatus", "planned_utc"):
        label = value.get(key)
        if not isinstance(label, str) or not label.strip() or "REPLACE" in label.upper():
            raise ValueError(f"missing real operator label: {key}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value["record_id"]):
        raise ValueError("record_id must use 1..96 letters/digits/dots/underscores/hyphens")
    if value.get("state") not in contract["class_names"] or value.get("split") not in ("train", "validation", "test"):
        raise ValueError("state and preassigned split must match the field contract")
    if value.get("label") != contract["class_names"].index(value["state"]):
        raise ValueError("state and numeric label disagree")


def plan_capture(destination, *, record_id, state, split, session_id, installation_id, apparatus, source_kind, root=ROOT):
    contract = capture_contract(root)
    assignment = dict(schema_version=1, planned_utc=datetime.now(timezone.utc).isoformat(),
                      record_id=record_id, state=state, split=split, session_id=session_id,
                      installation_id=installation_id, apparatus=apparatus, source_kind=source_kind,
                      label=contract["class_names"].index(state) if state in contract["class_names"] else -1,
                      operator_attestation="Labels and split assigned by the operator before acquisition; sensor bytes do not prove physical provenance.")
    validate_assignment(assignment, contract)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_json(destination, assignment, exclusive=True)
    return assignment


def append_record(manifest_path, record, assignment, contract, attempt):
    """Lock, preserve old bytes in the audit, append, then atomically replace JSON."""
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.with_suffix(manifest_path.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if manifest_path.exists():
            previous = manifest_path.read_bytes()
            (attempt / "manifest_before.json").write_bytes(previous)
            manifest = json.loads(previous)
        else:
            previous = None
            manifest = {"schema_version": 1, "source_kind": assignment["source_kind"], **contract,
                        "apparatus": assignment["apparatus"], "records": []}
        required = {"schema_version": 1, "source_kind": assignment["source_kind"], **contract,
                    "apparatus": assignment["apparatus"]}
        for key, expected in required.items():
            if manifest.get(key) != expected:
                raise ValueError(f"manifest {key} differs from assignment/profile; physical and synthetic records cannot mix")
        for old in manifest["records"]:
            for key in ("record_id", "path", "sha256", "source_log_sha256"):
                if old.get(key) == record[key]:
                    raise ValueError(f"duplicate capture {key}")
            for key in ("session_id", "installation_id"):
                if old.get(key) == record[key] and old.get("split") != record["split"]:
                    raise ValueError(f"{key} leaks across preassigned splits")
        manifest["records"].append(record)
        # Each accepted attempt keeps an immutable snapshot as well as the journal.
        snapshot = attempt / "manifest_after.json"
        write_json(snapshot, manifest, exclusive=True)
        handle, temporary = tempfile.mkstemp(prefix=".manifest-", suffix=".json", dir=manifest_path.parent)
        try:
            with os.fdopen(handle, "wb") as output:
                output.write(snapshot.read_bytes())
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, manifest_path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return {"manifest_before_sha256": hashlib.sha256(previous).hexdigest() if previous is not None else None,
                "manifest_after_sha256": digest(snapshot), "manifest_records": len(manifest["records"])}


def register_capture(log_path, assignment_path, manifest_path, attempts_dir, *, allow_fixture=False, root=ROOT):
    attempts_dir = Path(attempts_dir)
    attempts_dir.mkdir(parents=True, exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="attempt_", dir=attempts_dir)).resolve()
    audit = {"schema_version": 1, "status": "started", "started_utc": datetime.now(timezone.utc).isoformat(),
             "attempt_dir": str(attempt), "source_log": str(Path(log_path).resolve()),
             "manifest": str(Path(manifest_path).resolve()), "formal_real_data_eligible": False,
             "physical_provenance": "operator declaration; not inferred from log bytes"}
    write_json(attempt / "attempt.json", audit, exclusive=True)
    try:
        contract = capture_contract(root)
        assignment_bytes = Path(assignment_path).read_bytes()
        (attempt / "assignment.json").write_bytes(assignment_bytes)
        assignment = json.loads(assignment_bytes)
        validate_assignment(assignment, contract)
        fixture = assignment["source_kind"] == FIXTURE
        if fixture and not allow_fixture:
            raise ValueError("synthetic registration requires --allow-fixture and a separate fixture manifest")
        audit.update(source_kind=assignment["source_kind"], assignment_sha256=hashlib.sha256(assignment_bytes).hexdigest())
        blob = Path(log_path).read_bytes()
        source = attempt / "source.bin"
        source.write_bytes(blob)
        audit["source_log_sha256"] = digest(source)
        csv = attempt / "capture.csv"
        meta = sensor_log_to_csv(blob, csv)
        meta.update(source_kind=assignment["source_kind"], assignment_sha256=audit["assignment_sha256"])
        write_json(csv.with_suffix(".json"), meta)
        audit.update(csv_sha256=digest(csv), sidecar_sha256=digest(csv.with_suffix(".json")))
        quality = analyze_capture(csv, odr=contract["odr_hz"], clock_hz=contract["clock_hz"], axis=contract["axis"])
        write_json(attempt / "quality.json", quality, exclusive=True)
        if not quality["psd_valid_uniform_sampling_assumption"]:
            raise ValueError("capture has gaps or service/hardware errors")
        if abs(quality["service_interval_cycles"]["mean"] / (contract["clock_hz"]/contract["odr_hz"]) - 1) > 0.05:
            raise ValueError("mean service rate differs from configured ODR by >5%")
        minimum = 256 if fixture else 30 * contract["odr_hz"]
        if quality["record"]["samples"] < minimum:
            raise ValueError(f"capture needs at least {minimum} samples")
        manifest_path = Path(manifest_path).resolve()
        record = {k: assignment[k] for k in ("record_id", "state", "label", "split", "session_id", "installation_id")}
        record.update(path=os.path.relpath(csv, manifest_path.parent), sha256=audit["csv_sha256"],
                      sidecar_sha256=audit["sidecar_sha256"], source_log_sha256=audit["source_log_sha256"],
                      assignment_sha256=audit["assignment_sha256"], registration_attempt=os.path.relpath(attempt, manifest_path.parent))
        audit.update(append_record(manifest_path, record, assignment, contract, attempt))
        audit.update(status="accepted", record_id=record["record_id"], formal_real_data_eligible=not fixture)
    except (OSError, ValueError, KeyError, TypeError) as error:
        audit.update(status="rejected", error=str(error))
    audit["finished_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(attempt / "attempt.json", audit)
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="save labels and split before acquisition; never overwrite an assignment")
    for name in ("output", "record-id", "state", "split", "session-id", "installation-id", "apparatus", "source-kind"):
        plan.add_argument("--" + name, required=True)
    register = sub.add_parser("register", help="decode and quality-check an already-read SEN1 binary; no device access")
    for name in ("log", "assignment", "manifest"):
        register.add_argument("--" + name, required=True)
    register.add_argument("--attempts-dir", default="data/field/registration_attempts")
    register.add_argument("--allow-fixture", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan_capture(resolve_path(args.output), record_id=args.record_id, state=args.state, split=args.split,
                                  session_id=args.session_id, installation_id=args.installation_id, apparatus=args.apparatus,
                                  source_kind=args.source_kind)
        else:
            result = register_capture(resolve_path(args.log), resolve_path(args.assignment), resolve_path(args.manifest),
                                      resolve_path(args.attempts_dir), allow_fixture=args.allow_fixture)
        print(json.dumps(result, indent=2))
        return 2 if result.get("status") == "rejected" else 0
    except (OSError, ValueError) as error:
        parser.exit(2, f"capture registration error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
