#!/usr/bin/env bash
# Source this file from bash or the default macOS zsh, from any directory.
# BASH_SOURCE is empty in zsh; using it there silently selected the parent folder.
if [ -n "${ZSH_VERSION:-}" ]; then
    VIB_PROJECT_ROOT="$(cd -- "$(dirname -- "${(%):-%x}")/.." && pwd)"
else
    VIB_PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
fi
export VIB_PROJECT_ROOT
export PATH="$VIB_PROJECT_ROOT/.venv/bin:$VIB_PROJECT_ROOT/.tools/oss-cad-suite/bin:$PATH"
export PYTHONPATH="$VIB_PROJECT_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export MPLCONFIGDIR="$VIB_PROJECT_ROOT/build/matplotlib"
export PYTHONPYCACHEPREFIX="$VIB_PROJECT_ROOT/build/pycache"
export XDG_CONFIG_HOME="$VIB_PROJECT_ROOT/build/xdg-config"
export XDG_DATA_HOME="$VIB_PROJECT_ROOT/build/xdg-data"

# The bundled Verilator wrapper and generated Makefiles require whitespace-free
# tool paths. Only these aliases live in temporary storage; project data stays put.
VIB_TOOL_ALIAS="$("$VIB_PROJECT_ROOT/.venv/bin/python" -c 'import sys; sys.path.insert(0, sys.argv[1]); from build_support import safe_alias; print(safe_alias(sys.argv[2]))' "$VIB_PROJECT_ROOT/scripts" "$VIB_PROJECT_ROOT/.tools/oss-cad-suite")"
export VERILATOR_ROOT="$VIB_TOOL_ALIAS/share/verilator"
export VERILATOR_BIN="$VIB_TOOL_ALIAS/libexec/verilator_bin"
