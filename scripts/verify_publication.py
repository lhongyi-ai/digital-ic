#!/usr/bin/env python3
"""Verify the English publication without training, inference, or hardware access."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]")
PRIVATE = re.compile(r"/Users/|\.chatgpt-projects/|/private/var/folders/|/var/folders/")
SECRETS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "openai_token": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "stripe_live_key": re.compile(r"\b[rs]k_live_[A-Za-z0-9]{20,}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_text(text: str, label: str, findings: list[dict]) -> None:
    if CJK.search(text):
        findings.append({"path": label, "issue": "non_English_CJK_text"})
    # This verifier contains the literal forbidden-path patterns by design.
    if label != "scripts/verify_publication.py" and PRIVATE.search(text):
        findings.append({"path": label, "issue": "private_local_path"})
    for rule, pattern in SECRETS.items():
        if pattern.search(text):
            findings.append({"path": label, "issue": rule})


def main() -> int:
    manifest_path = ROOT / "publication/manifest.json"
    anchor_path = ROOT / "publication/manifest.sha256"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    findings: list[dict] = []
    if anchor_path.read_text().split()[0] != digest(manifest_path):
        findings.append({"path": "publication/manifest.json", "issue": "manifest_anchor_mismatch"})
    declared_paths = [entry["path"] for entry in manifest["files"]]
    if len(declared_paths) != len(set(declared_paths)):
        findings.append({"path": "publication/manifest.json", "issue": "duplicate_manifest_path"})
    anchor_files = {"publication/manifest.json", "publication/manifest.sha256"}
    try:
        top = Path(subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, stderr=subprocess.DEVNULL,
            text=True).strip()).resolve()
        if top != ROOT:
            raise ValueError("Publication does not yet have its own Git repository")
        actual_paths = {p.decode() for p in subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT).split(b"\0") if p} - anchor_files
    except (OSError, ValueError, subprocess.CalledProcessError):
        # Before Git initialization, inspect the generated snapshot itself.
        actual_paths = {
            str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
            if p.is_file() and p.name != ".DS_Store" and not any(part in {".git", "__pycache__", ".pytest_cache"}
                                       for part in p.relative_to(ROOT).parts)
        } - anchor_files - {"publication/verification-latest.json"}
    for path in sorted(actual_paths - set(declared_paths)):
        findings.append({"path": path, "issue": "file_not_bound_by_manifest"})
    for path in sorted(set(declared_paths) - actual_paths):
        findings.append({"path": path, "issue": "declared_file_not_in_publication"})
    text_count = 0
    archive_count = 0
    for entry in manifest["files"]:
        label = entry["path"]
        path = ROOT / label
        if not path.is_file():
            findings.append({"path": label, "issue": "missing_file"})
            continue
        if digest(path) != entry["published_sha256"]:
            findings.append({"path": label, "issue": "published_hash_mismatch"})
        if CJK.search(label):
            findings.append({"path": label, "issue": "non_English_path"})
        with path.open("rb") as stream:
            prefix = stream.read(8192)
        if b"\0" not in prefix:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError:
                text = None
            if text is not None:
                text_count += 1
                inspect_text(text, label, findings)
                if path.suffix == ".json":
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        findings.append({"path": label, "issue": "invalid_JSON"})
                    else:
                        inspect_text(json.dumps(data, ensure_ascii=False), label, findings)
                elif path.suffix == ".py":
                    try:
                        ast.parse(text, filename=label)
                    except SyntaxError:
                        findings.append({"path": label, "issue": "invalid_Python"})
        if path.suffix in {".npz", ".pt", ".pth", ".zip"} and zipfile.is_zipfile(path):
            archive_count += 1
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    inspect_text(member.filename, label + ":archive-member", findings)
                    if member.filename.endswith((".json", ".txt")) and member.file_size < 1024 * 1024:
                        inspect_text(archive.read(member).decode("utf-8", errors="replace"), label + ":" + member.filename, findings)
    inspect_text(json.dumps(manifest, ensure_ascii=False), "publication/manifest.json", findings)
    result = {
        "passed": not findings,
        "files_checked": len(manifest["files"]),
        "text_files_checked": text_count,
        "archives_checked": archive_count,
        "findings": findings,
        "scope": "Publication integrity, text language, path hygiene, known credential patterns, and JSON/Python syntax; not a new engineering or hardware validation.",
    }
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
