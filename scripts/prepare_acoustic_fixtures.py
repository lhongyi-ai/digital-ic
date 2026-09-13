#!/usr/bin/env python3
"""Export deterministic arithmetic fixtures; these are not trained machine models."""
import json
from pathlib import Path
from vibfpga.export import export_model
ROOT=Path(__file__).resolve().parents[1]
for encoding in ('linear','log4'):
    model=json.loads((ROOT/f'tests/fixtures/acoustic-{encoding}.json').read_text())
    assert model['verification_only'] is True
    export_model(model,ROOT/f'build/acoustic-fixture/{encoding}')
