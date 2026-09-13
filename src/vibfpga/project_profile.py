"""Lightweight project choices; numerical definitions stay in the model JSON."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[2]


def resolve_path(value, root=ROOT):
    path = Path(value)
    return (path if path.is_absolute() else Path(root) / path).resolve()


def load_profile(name="cwru-neighbor3", *, root=ROOT, config=None):
    root = Path(root).resolve()
    config = resolve_path(config or "configs/project-profiles.json", root)
    catalog = json.loads(config.read_text())
    if catalog.get("schema_version") != 1 or name not in catalog.get("profiles", {}):
        raise ValueError(f"unknown profile or schema: {name}")
    profile = dict(catalog["profiles"][name])
    if profile.get("lanes") not in (1, 4) or profile.get("n") not in (256, 1024):
        raise ValueError("profile requires supported lanes and window length")
    if profile.get("kind") not in ("cwru_classifier", "sensor_measurement", "field_fixture"):
        raise ValueError("unsupported profile kind")
    expected_geometry = (1024, 12000) if profile["kind"] == "cwru_classifier" else (256, 800)
    if (profile["n"], profile.get("sample_rate_hz")) != expected_geometry:
        raise ValueError("profile window length/sample rate mismatch with selected system")
    if profile["kind"] != "cwru_classifier" and (profile.get("axis") not in ("x", "y", "z") or profile.get("clock_hz") != 12000000):
        raise ValueError("sensor profiles require an explicit axis and 12 MHz clock")
    if profile["kind"] == "cwru_classifier" and profile.get("clock_source") not in ("external12", "hfosc12"):
        raise ValueError("CWRU board profile requires an explicit supported clock source")
    for key in ("model", "vectors", "manifest", "run_dir", "board_config"):
        if key in profile:
            profile[key] = str(resolve_path(profile[key], root))
    model = json.loads(Path(profile["model"]).read_text())
    for key, expected in profile.get("model_requirements", {}).items():
        if model.get(key) != expected:
            raise ValueError(f"profile/model mismatch for {key}: expected {expected!r}, got {model.get(key)!r}")
    if model.get("n") != profile["n"]:
        raise ValueError("profile/model window length mismatch")
    if "sample_rate_hz" in model and model["sample_rate_hz"] != profile["sample_rate_hz"]:
        raise ValueError("profile/model sample rate mismatch")
    if profile["kind"] == "sensor_measurement" and not model.get("not_for_classification"):
        raise ValueError("SEN1 requires the measurement coefficient model")
    if profile["kind"] == "field_fixture" and (model.get("source_kind") != "synthetic_pipeline_fixture"
            or model.get("training_status") != "synthetic_fixture_not_for_deployment"):
        raise ValueError("fixture profile cannot imply a real trained field model")
    if profile.get("axis") and "axis" in model and profile["axis"] != model["axis"]:
        raise ValueError("profile/model axis mismatch")
    profile.update(name=name, project_root=str(root), model_sha256=hashlib.sha256(Path(profile["model"]).read_bytes()).hexdigest(),
                   model_training_status=model.get("training_status"), feature_mode=model.get("feature_mode", "single_bin"),
                   real_field_model_trained=False, metadata_verified=True,
                   frozen_artifacts_verified=False, hardware_evidence_checked=False)
    return profile


def command_list(profile):
    """Export commands for review. Never execute a build, train, evaluate or USB call."""
    p = profile
    python = str(Path(p["project_root"]) / ".venv/bin/python")
    script = lambda name: str(Path(p["project_root"]) / "scripts" / name)
    if p["kind"] == "cwru_classifier":
        commands = [[python, script("build_core.py"), "--model", p["model"], "--lanes", str(p["lanes"]), "--frames", "10"],
                    [python, script("build_board.py"), "--model", p["model"], "--lanes", str(p["lanes"]), "--clock-source", p["clock_source"]]]
    elif p["kind"] == "sensor_measurement":
        commands = [[python, script("build_sensor.py"), "--rate", str(p["sample_rate_hz"]), "--axis", str("xyz".index(p["axis"]))]]
    else:
        commands = [[python, script("field_status.py"), "verify", "--output", p["run_dir"]],
                    [python, script("build_field.py"), "--model", p["model"], "--lanes", str(p["lanes"]), "--allow-fixture"]]
    return [shlex.join(command) for command in commands]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "commands", "export"))
    parser.add_argument("--profile", default="cwru-neighbor3")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--format", choices=("json", "shell"), default="json")
    parser.add_argument("--clock-source", choices=("external12", "hfosc12"), help="explicit CWRU board clock override for displayed/exported commands")
    args = parser.parse_args(argv)
    try:
        p = load_profile(args.profile, root=args.root, config=args.config)
        if args.clock_source:
            if p["kind"] != "cwru_classifier":
                raise ValueError("clock override currently applies only to the CWRU board profile")
            p["clock_source"] = args.clock_source
        if args.action == "commands":
            print("\n".join(command_list(p)))
        elif args.action == "export" and args.format == "shell":
            keys = ("name", "project_root", "model", "n", "sample_rate_hz", "lanes", "axis", "feature_mode", "clock_source")
            print("\n".join(f"export VIB_{key.upper()}={shlex.quote(str(p[key]))}" for key in keys if key in p))
        else:
            print(json.dumps(p, indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"profile error: {error}\n")


if __name__ == "__main__":
    main()
