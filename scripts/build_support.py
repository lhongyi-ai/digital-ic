"""Content-bound simulator builds and independent regression output paths."""
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def add_run_arguments(parser):
    parser.add_argument("--build-root", type=Path, default=ROOT / "build",
                        help="Build/cache root (default: project build/)")
    parser.add_argument("--run-id", help="Isolate outputs in BUILD_ROOT/runs/ID; use a new ID for each run")


def run_path(args, name):
    base = args.build_root.resolve()
    if args.run_id:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id) or args.run_id in (".", ".."):
            raise ValueError("run-id must be a single safe name containing letters, digits, dots, underscores or hyphens")
        base = base / "runs" / args.run_id
    return base / name


def yosys_quote(path):
    """A filename in a Yosys command script, not shell syntax."""
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def input_hashes(paths):
    return {str(Path(p).resolve()): sha(p) for p in sorted(set(map(Path, paths)))}


def require_unchanged(hashes):
    if any(not Path(p).is_file() or sha(p) != digest for p, digest in hashes.items()):
        raise RuntimeError("A build input changed during execution; no successful evidence is valid")


def configure_verilator_environment():
    suite = ROOT / ".tools/oss-cad-suite"
    if suite.is_dir():
        alias = safe_alias(suite)
        os.environ["VERILATOR_ROOT"] = str(alias / "share/verilator")
        os.environ["VERILATOR_BIN"] = str(alias / "libexec/verilator_bin")


def tool_identity(name):
    if name == "verilator":
        configure_verilator_environment()
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"Required compiler tool not found: {name}")
    return {"path": str(Path(executable).resolve()), "sha256": sha(executable),
            "version": subprocess.check_output([executable, "--version"], text=True, stderr=subprocess.STDOUT).strip()}


def content_manifest(sources, parameters, build_args, *, includes=(), tool=None, options=None):
    paths = set(Path(p).resolve() for p in sources)
    search_dirs = [Path(p).resolve() for p in includes]
    # Bind nested includes; missing/nonliteral includes must never produce a cache hit.
    pending = list(paths)
    while pending:
        source = pending.pop()
        if source.suffix not in (".sv", ".v", ".svh", ".vh"):
            continue
        for line in source.read_text().splitlines():
            if not re.match(r"\s*`include\b", line):
                continue
            match = re.match(r'\s*`include\s+"([^"]+)"', line)
            if not match:
                raise ValueError(f"Cannot safely cache a nonliteral include in {source}: {line}")
            candidates = [source.parent / match[1], *(p / match[1] for p in search_dirs)]
            found = next((p.resolve() for p in candidates if p.is_file()), None)
            if found is None:
                raise FileNotFoundError(f"Unresolved include {match[1]} in {source}")
            if found not in paths:
                paths.add(found)
                pending.append(found)
    for name, value in parameters.items():
        if name.endswith("MODEL_DIR"):
            directory = Path(str(value).strip('"')).resolve()
            paths.update(p for p in directory.rglob("*") if p.is_file())
        elif name.endswith("FILE"):
            paths.add(Path(str(value).strip('"')).resolve())
    return {"schema_version": 1, "sources": [str(Path(p).resolve()) for p in sources],
            "input_sha256": input_hashes(paths), "parameters": parameters,
            "build_args": list(build_args), "includes": [str(p) for p in search_dirs],
            "toolchain": tool, "options": options or {}}


def manifest_key(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def safe_alias(path):
    """Give generated Makefiles a whitespace-free path without moving project data."""
    path = Path(path).resolve()
    if not any(char.isspace() for char in str(path)):
        return path
    base = Path(tempfile.gettempdir()) / f"vibfpga-paths-{os.getuid()}"
    base.mkdir(mode=0o700, exist_ok=True)
    alias = base / hashlib.sha256(str(path).encode()).hexdigest()[:20]
    try:
        alias.symlink_to(path, target_is_directory=True)
    except FileExistsError:
        if not alias.is_symlink() or alias.resolve() != path:
            raise RuntimeError(f"Compiler path alias collision: {alias}")
    return alias


def space_safe_commands(commands, paths):
    replacements = sorted(((str(Path(p).resolve()), str(safe_alias(p))) for p in paths), key=lambda row: -len(row[0]))
    return [[_replace_paths(str(arg), replacements) for arg in command] for command in commands]


def _replace_paths(value, replacements):
    for original, alias in replacements:
        value = value.replace(original, alias)
    return value


def require_xml_passed(path):
    tree = ET.parse(path)
    cases = list(tree.iter("testcase"))
    if not cases or any(list(tree.iter(tag)) for tag in ("failure", "error", "skipped")):
        raise RuntimeError(f"Fresh executed passing cocotb tests required: {path}")
    return len(cases)


def get_space_safe_runner():
    from cocotb_tools.runner import Verilator
    class SpaceSafeVerilator(Verilator):
        def _build_command(self):
            import cocotb_tools.config
            commands = super()._build_command()
            root = Path(os.environ.get("VERILATOR_ROOT", ROOT / ".tools/oss-cad-suite/share/verilator"))
            if root.is_dir():
                self.env["VERILATOR_ROOT"] = str(safe_alias(root))
            commands = space_safe_commands(commands, [ROOT, self.build_dir, cocotb_tools.config.share_dir,
                                                      cocotb_tools.config.libs_dir, *[p.value.parent for p in self._sources]])
            for command in commands:
                if Path(command[0]).name == "make":
                    command.append(f"CURDIR={safe_alias(self.build_dir)}")
            return commands
    return SpaceSafeVerilator()


class CachedRunner:
    """Cache compilation only; every test call runs and checks fresh XML.

    Compiler entries are locked, input/content validated and published only after
    success. Reports/coverage/test logs remain in the requested run directory.
    """
    def __init__(self, cache_root):
        self.runner = get_space_safe_runner()
        self.cache_root = Path(cache_root).resolve() / ".compiler-cache" / "verilator"

    def build(self, **kwargs):
        import cocotb_tools.config
        import cocotb_tools.runner
        (Path(kwargs["build_dir"]) / "build_manifest.json").unlink(missing_ok=True)
        parameters = kwargs.get("parameters", {})
        tool = {"verilator": tool_identity("verilator"), "cxx": tool_identity(os.environ.get("CXX", "c++")),
                "verilator_binary_sha256": sha(os.environ["VERILATOR_BIN"]) if os.environ.get("VERILATOR_BIN") else None,
                "verilator_include_sha256": input_hashes(p for p in Path(os.environ["VERILATOR_ROOT"]).joinpath("include").rglob("*") if p.is_file()) if os.environ.get("VERILATOR_ROOT") else {},
                "cocotb": importlib.metadata.version("cocotb"),
                "runner_sha256": sha(cocotb_tools.runner.__file__), "cache_helper_sha256": sha(__file__),
                "harness_sha256": sha(cocotb_tools.config.share_dir / "lib/verilator/verilator.cpp"),
                "vpi_sha256": sha(cocotb_tools.config.lib_name_path("vpi", "verilator")),
                "environment": {k: os.environ.get(k) for k in ("VERILATOR_ROOT", "VERILATOR_BIN", "CXX", "CC", "CFLAGS", "CXXFLAGS", "LDFLAGS", "CPPFLAGS", "MAKEFLAGS")}}
        self.manifest = content_manifest(kwargs["sources"], parameters, kwargs.get("build_args", []),
            includes=kwargs.get("includes", []), tool=tool,
            options={k: kwargs[k] for k in ("hdl_toplevel", "defines", "timescale", "waves", "hdl_library") if k in kwargs})
        self.key = manifest_key(self.manifest)
        self.compiled = self.cache_root / self.key
        self.compiled.mkdir(parents=True, exist_ok=True)
        ready = self.compiled / "complete.json"
        executable = self.compiled / kwargs["hdl_toplevel"]
        started = time.monotonic()
        with (self.compiled / "compile.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                stored = json.loads(ready.read_text())
                hit = stored["manifest"] == self.manifest and executable.is_file() and sha(executable) == stored["executable_sha256"]
            except (OSError, ValueError, KeyError):
                hit = False
            if not hit:
                ready.unlink(missing_ok=True)
                compile_args = {**kwargs, "build_dir": self.compiled, "always": True,
                                "log_file": self.compiled / "compile.log"}
                self.runner.build(**compile_args)
                require_unchanged(self.manifest["input_sha256"])
                write_json(ready, {"manifest": self.manifest, "executable_sha256": sha(executable)})
            require_unchanged(self.manifest["input_sha256"])
        self.receipt = {"compiler_cache_key": self.key, "compiler_cache_hit": hit,
                        "compiler_seconds": time.monotonic() - started, "compiler_directory": str(self.compiled),
                        "manifest": self.manifest, "test_results_reused": False}
        # Keep coverage's direct reuse helper compatible with historical build-dir.
        self.requested_build = Path(kwargs["build_dir"]).resolve()
        self.requested_build.mkdir(parents=True, exist_ok=True)
        write_json(self.requested_build / "build_manifest.json", self.receipt)
        print(f"Compiler cache {'HIT' if hit else 'MISS'} {self.key[:12]} ({self.receipt['compiler_seconds']:.3f}s)", flush=True)

    def test(self, **kwargs):
        output = Path(kwargs.get("test_dir", self.requested_build)).resolve()
        output.mkdir(parents=True, exist_ok=True)
        xml = Path(kwargs.get("results_xml", output / "results.xml"))
        if not xml.is_absolute():
            xml = output / xml
        xml.unlink(missing_ok=True)
        require_unchanged(self.manifest["input_sha256"])
        write_json(output / "build_manifest.json", self.receipt)
        self.runner.test(**{**kwargs, "build_dir": self.compiled, "hdl_toplevel_lang": "verilog", "results_xml": xml})
        require_xml_passed(xml)
        require_unchanged(self.manifest["input_sha256"])


def run_verilator_build(command, output, top, *, stdout=None):
    """Run native Verilator generation and Make separately for paths with spaces."""
    configure_verilator_environment()
    command = [arg for arg in command if arg != "--build"]
    if "--binary" in command:
        command.remove("--binary")
        command += ["--cc", "--exe", "--main"]
    command = space_safe_commands([command], [ROOT, output])[0]
    subprocess.run(command, check=True, cwd=ROOT, stdout=stdout, stderr=subprocess.STDOUT)
    subprocess.run(["make", "-j", "4", "-C", str(safe_alias(output)), "-f", f"V{top}.mk",
                    f"CURDIR={safe_alias(output)}"], check=True, cwd=ROOT, stdout=stdout, stderr=subprocess.STDOUT)


def cached_native_build(cache_root, output, sources, parameters, flags, command_factory, top):
    tool = {"verilator": tool_identity("verilator"), "cxx": tool_identity(os.environ.get("CXX", "c++")),
            "verilator_binary_sha256": sha(os.environ["VERILATOR_BIN"]) if os.environ.get("VERILATOR_BIN") else None,
            "verilator_include_sha256": input_hashes(p for p in Path(os.environ["VERILATOR_ROOT"]).joinpath("include").rglob("*") if p.is_file()) if os.environ.get("VERILATOR_ROOT") else {},
            "helper_sha256": sha(__file__), "environment": {k: os.environ.get(k) for k in
            ("VERILATOR_ROOT", "VERILATOR_BIN", "CXX", "CC", "CFLAGS", "CXXFLAGS", "LDFLAGS", "CPPFLAGS", "MAKEFLAGS")}}
    manifest = content_manifest(sources, parameters, flags, tool=tool, options={"top": top})
    key = manifest_key(manifest)
    compiled = Path(cache_root).resolve() / ".compiler-cache/native" / key
    compiled.mkdir(parents=True, exist_ok=True)
    ready, executable = compiled / "complete.json", compiled / f"V{top}"
    started = time.monotonic()
    with (compiled / "compile.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            stored = json.loads(ready.read_text())
            hit = stored["manifest"] == manifest and executable.is_file() and sha(executable) == stored["executable_sha256"]
        except (OSError, ValueError, KeyError):
            hit = False
        if not hit:
            ready.unlink(missing_ok=True)
            run_verilator_build(command_factory(compiled), compiled, top)
            require_unchanged(manifest["input_sha256"])
            write_json(ready, {"manifest": manifest, "executable_sha256": sha(executable)})
        require_unchanged(manifest["input_sha256"])
    receipt = {"compiler_cache_key": key, "compiler_cache_hit": hit, "compiler_seconds": time.monotonic() - started,
               "compiler_directory": str(compiled), "manifest": manifest, "test_results_reused": False}
    write_json(Path(output) / "build_manifest.json", receipt)
    print(f"Compiler cache {'HIT' if hit else 'MISS'} {key[:12]} ({receipt['compiler_seconds']:.3f}s)", flush=True)
    return executable, manifest["input_sha256"]
