#!/usr/bin/env python3
"""Install the tested macOS ARM64 environment inside this project.

This downloads software, does not access USB, and does not install system-wide.
On other platforms install a matching OSS CAD Suite manually and source env.sh.
"""
import hashlib
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request
import venv

ROOT=Path(__file__).resolve().parents[1]
RELEASE="2026-09-05"
URL=f"https://github.com/YosysHQ/oss-cad-suite-build/releases/download/{RELEASE}/oss-cad-suite-darwin-arm64-20260905.tgz"
SHA="17fdfe2043e8a6271c14f29de2ae592feec1f63c2eb53edbd316350b4c6b901a"
if platform.system()!="Darwin" or platform.machine()!="arm64":
    raise SystemExit("This lock targets macOS ARM64. Install the equivalent OSS CAD Suite for your platform, then use scripts/env.sh.")
if not (ROOT/".venv/bin/python").exists():venv.create(ROOT/".venv",with_pip=True)
subprocess.run([str(ROOT/".venv/bin/python"),"-m","pip","install","-r",str(ROOT/"requirements.lock.txt")],check=True)
directory=ROOT/".tools"
directory.mkdir(exist_ok=True)
if not (directory/"oss-cad-suite/bin/yosys").exists():
    archive=directory/"oss-cad-suite.tgz"
    urllib.request.urlretrieve(URL,archive)
    digest=hashlib.sha256()
    with archive.open("rb") as file:
        for block in iter(lambda:file.read(1024*1024),b""):digest.update(block)
    if digest.hexdigest()!=SHA:raise ValueError("Toolchain archive SHA256 mismatch")
    with tarfile.open(archive) as file:file.extractall(directory,filter="data")
    archive.unlink()
print("Environment ready. Source scripts/env.sh, then run make verify.")
