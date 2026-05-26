#!/usr/bin/env python3
"""Build clean upload files for all languages from per-domain _fix.json files.

For each language, reads domain metadata from the (dirty) existing upload file
and replaces the terms arrays with the cleaned terms from domain_NN_*_fix.json.
Writes language_upload-clean.json in the data/ directory.
"""

import glob
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

LANGUAGES = [
    ("java",   "java_domains",   "java_upload.json"),
    ("aws",    "aws_domains",    "aws_upload.json"),
    ("ai_ml",  "ai_ml_domains",  "ai_ml_upload.json"),
    ("cpp",    "cpp_domains",    "cpp_upload.json"),
    ("python", "python_domains", "python_upload.json"),
]


def build_language(lang: str, subdir: str, src_filename: str) -> None:
    src_path = os.path.join(BASE, src_filename)
    out_path = os.path.join(BASE, src_filename.replace("_upload.json", "_upload-clean.json"))
    subdir_path = os.path.join(BASE, subdir)

    with open(src_path) as f:
        source = json.load(f)

    domains = source["domains"]
    fix_files = sorted(glob.glob(os.path.join(subdir_path, "domain_*_fix.json")))

    # Build index→fix_data map
    fix_map: dict[int, dict] = {}
    for ff in fix_files:
        m = re.match(r"domain_(\d+)_", os.path.basename(ff))
        if m:
            idx = int(m.group(1))
            with open(ff) as f:
                fix_map[idx] = json.load(f)

    merged = {"domains": []}
    total_terms = 0
    for i, domain in enumerate(domains):
        if i not in fix_map:
            print(f"  WARNING: {lang} domain {i} has no fix file — using original (dirty) terms")
            merged["domains"].append(domain)
            total_terms += len(domain.get("terms", []))
        else:
            clean_terms = fix_map[i].get("terms", [])
            merged["domains"].append({
                "node_type": domain["node_type"],
                "data": domain["data"],
                "terms": clean_terms,
            })
            total_terms += len(clean_terms)

    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"  {lang}: {len(merged['domains'])} domains, {total_terms} terms → {os.path.basename(out_path)}")


def main() -> None:
    print("Building clean upload files...\n")
    for lang, subdir, src in LANGUAGES:
        build_language(lang, subdir, src)
    print("\nDone.")


if __name__ == "__main__":
    main()
