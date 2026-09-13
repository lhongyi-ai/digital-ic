#!/usr/bin/env python3
"""Display or export authoritative project choices from any working directory."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vibfpga.project_profile import main

if __name__ == "__main__":
    main()
