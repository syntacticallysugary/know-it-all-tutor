#!/usr/bin/env python3
"""Generate 8 per-domain AI/ML cleanup prompts from the shared template."""

import importlib.util
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "_tmpl", Path(__file__).parent.parent / "template.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
TEMPLATE = _mod.TEMPLATE

DOMAINS = [
    (0, "architecture", "AI/ML — Architecture", 14),
    (1, "training", "AI/ML — Training", 15),
    (2, "inference", "AI/ML — Inference", 13),
    (3, "evaluation", "AI/ML — Evaluation", 14),
    (4, "data_prep", "AI/ML — Data Preparation", 12),
    (5, "nlp", "AI/ML — NLP", 11),
    (6, "mlops", "AI/ML — MLOps", 12),
    (7, "math", "AI/ML — Math Foundations", 13),
]

BASE = "/home/jimbob/Dev/AWS_Dev"
DATA_DIR = "data/ai_ml_domains"


def main():
    out_dir = os.path.dirname(os.path.abspath(__file__))
    for idx, slug, display_name, term_count in DOMAINS:
        content = TEMPLATE.format(
            idx=idx,
            slug=slug,
            display_name=display_name,
            term_count=term_count,
            base=BASE,
            data_dir=DATA_DIR,
        )
        out_path = os.path.join(out_dir, f"domain_{idx:02d}_{slug}.md")
        with open(out_path, "w") as f:
            f.write(content)
        print(f"  Written: domain_{idx:02d}_{slug}.md  ({term_count} terms)")
    print(f"\nGenerated {len(DOMAINS)} prompt files in {out_dir}/")


if __name__ == "__main__":
    main()
