#!/usr/bin/env python3
"""Generate 11 per-domain AWS cleanup prompts from the shared template."""

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
    (0, "compute", "AWS — Compute", 13),
    (1, "storage", "AWS — Storage", 12),
    (2, "networking", "AWS — Networking", 13),
    (3, "security", "AWS — Security", 13),
    (4, "databases", "AWS — Databases", 12),
    (5, "monitoring", "AWS — Monitoring", 10),
    (6, "ai_services", "AWS — AI Services", 10),
    (7, "migration", "AWS — Migration and Transfer", 8),
    (8, "cost_mgmt", "AWS — Cost Management", 10),
    (9, "arch_patterns", "AWS — Architectural Patterns", 11),
    (10, "iac_devops", "AWS — IaC and DevOps", 11),
]

BASE = "/home/jimbob/Dev/AWS_Dev"
DATA_DIR = "data/aws_domains"


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
