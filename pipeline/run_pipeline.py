#!/usr/bin/env python3
"""Run the full definition cleanup pipeline for a domain upload file.

Usage:
  python3 pipeline/run_pipeline.py data/java_upload-fix.json
  python3 pipeline/run_pipeline.py data/ai_ml_upload-fix.json

Steps:
  1. Derive slugs and generate split + merge scripts (if not already present)
  2. Split the upload file into per-domain JSON files
  3. Run the cleanup agent (Sparky / Qwen3.5-35B) on each domain in sequence
  4. Merge all cleaned domains back into the upload file

Completed domains are skipped automatically — safe to re-run after failures.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.agent import run_pipeline

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    run_pipeline(Path(sys.argv[1]))
