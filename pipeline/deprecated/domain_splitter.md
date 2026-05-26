# Domain Splitter Agent

## ⚠️ BEFORE ANYTHING ELSE — Your upload file is:

```
/home/jimbob/Dev/AWS_Dev/data/java_upload.json
```

**Read this file first using the Read tool. Do NOT use any other file,
do NOT infer a file from IDE context, open tabs, or environment variables.
If this path looks wrong, stop and ask the user to correct it.**

---

## Task

Given an existing upload JSON file, inspect the domains it contains, derive slugs
for each one, generate `split_*_domains.py` and `merge_*_domains.py` scripts, and
run the split script to produce the per-domain files.

---

## Step 1 — Read and inspect the upload file

Use the Read tool to open the upload JSON file. For each domain in `data.domains`,
record:
- Its index (0-based position in the array)
- `data.name` — the full display name (e.g., `"AI/ML — Data Preparation"`)
- Number of terms (`len(terms)`)

---

## Step 2 — Derive slugs

For each domain, derive a slug from the display name using these rules:

1. Take the part **after** ` — ` (the subdomain label only, not the prefix).
2. Lowercase everything.
3. Replace spaces with underscores.
4. Abbreviate if the result would be over ~15 characters:

| Long form | Slug |
|-----------|------|
| `management` | `mgmt` |
| `preparation` | `prep` |
| `architectural` | `arch` |
| `foundations` | drop — use the primary noun only (e.g., `"Math Foundations"` → `math`) |
| `"X and Y"` | drop the connector — use primary concept (e.g., `"Migration and Transfer"` → `migration`) |
| `"IaC and DevOps"` | `iac_devops` |

5. Acronyms that are already short (`NLP`, `MLOps`, `IaC`) → just lowercase: `nlp`, `mlops`, `iac`.

**Write out your proposed slug list before generating any files:**

```
Index  Display Name                        Slug
  00   AI/ML — Architecture                architecture
  01   AI/ML — Data Preparation            data_prep
  ...
```

If any slug is ambiguous, note your reasoning.

---

## Step 3 — Determine file and directory names

From the upload file path, derive the following:

| Name | Rule | Example |
|------|------|---------|
| **stem** | Part before `_upload` in the filename | `ai_ml_upload-fix.json` → `ai_ml` |
| **stem_nodash** | stem with underscores removed | `ai_ml` → `aiml` |
| **output_dir** | `data/{stem}_domains/` next to the upload file | `data/ai_ml_domains/` |
| **split script** | `split_{stem_nodash}_domains.py` inside output_dir | `split_aiml_domains.py` |
| **merge script** | `merge_{stem_nodash}_domains.py` inside output_dir | `merge_aiml_domains.py` |
| **source ref** | relative path from output_dir to upload file | `"../{filename}"` |

---

## Step 4 — Create the output directory

Use the Bash tool to create the output directory if it does not already exist:

```bash
mkdir -p /home/jimbob/Dev/AWS_Dev/data/{stem}_domains
```

---

## Step 5 — Write the split script

Write `{output_dir}/split_{stem_nodash}_domains.py` using the Write tool.
Follow this exact pattern, substituting your derived values:

```python
#!/usr/bin/env python3
"""
Split {upload_filename} into {N} per-sub-domain files for incremental definition cleanup.
Run once to create domain_00_{slug0}.json … domain_{NN}_{slugN}.json.
"""
import json, os

SLUGS = [
    "{slug0}",
    "{slug1}",
    # ... one entry per domain, in order
]

def main():
    data_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(data_dir, "..", "{upload_filename}")

    with open(src) as f:
        data = json.load(f)

    domains = data["domains"]
    assert len(domains) == len(SLUGS), f"Expected {len(SLUGS)} domains, got {len(domains)}"

    for i, (domain, slug) in enumerate(zip(domains, SLUGS)):
        out_path = os.path.join(data_dir, f"domain_{i:02d}_{slug}.json")
        payload = {
            "domain_index": i,
            "domain_name": domain["data"]["name"],
            "term_count": len(domain["terms"]),
            "terms": domain["terms"],
        }
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"  {i:02d}. {domain['data']['name']:40s} → {os.path.basename(out_path)}  ({len(domain['terms'])} terms)")

    print(f"\nCreated {len(domains)} domain files in {data_dir}/")

if __name__ == "__main__":
    main()
```

---

## Step 6 — Write the merge script

Write `{output_dir}/merge_{stem_nodash}_domains.py` using the Write tool.
Follow this exact pattern:

```python
#!/usr/bin/env python3
"""
Checkpoint reporter and merger for {display_prefix} domain definition cleanup.

Usage:
  python3 merge_{stem_nodash}_domains.py           # report status
  python3 merge_{stem_nodash}_domains.py --merge   # merge all {N} completed domains into {upload_filename}
"""
import json, os, sys

DOMAINS = [
    (0,  "{slug0}",  "{display_name_0}"),
    (1,  "{slug1}",  "{display_name_1}"),
    # ... one tuple per domain: (index, slug, display_name)
]

def main():
    do_merge = "--merge" in sys.argv
    data_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(data_dir, "..", "{upload_filename}")
    out_path = src_path  # overwrite in place

    with open(src_path) as f:
        source = json.load(f)

    print("=== {display_prefix} Domain Cleanup Checkpoint ===\n")

    completed, errors, pending = [], [], []

    for idx, slug, display_name in DOMAINS:
        fix_path = os.path.join(data_dir, f"domain_{idx:02d}_{slug}_fix.json")
        if os.path.exists(fix_path):
            try:
                with open(fix_path) as f:
                    fix_data = json.load(f)
                terms = fix_data.get("terms", [])
                expected = len(source["domains"][idx]["terms"])
                if len(terms) != expected:
                    raise ValueError(f"expected {expected} terms, got {len(terms)}")
                print(f"  ✓  {idx:02d}. {display_name:40s} ({len(terms)} terms)")
                completed.append((idx, slug, fix_path, fix_data))
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"  ✗  {idx:02d}. {display_name:40s} (ERROR: {e})")
                errors.append((idx, slug, str(e)))
        else:
            print(f"  …  {idx:02d}. {display_name:40s} (pending)")
            pending.append((idx, slug))

    total = len(DOMAINS)
    print(f"\n{len(completed)}/{total} done  |  {len(errors)} errors  |  {len(pending)} pending")

    if pending:
        next_idx, next_slug = pending[0]
        print(f"\nNext prompt to run:  domain_{next_idx:02d}_{next_slug}.md")

    if errors:
        print("\nFix errors before merging:")
        for idx, slug, msg in errors:
            print(f"  domain_{idx:02d}_{slug}_fix.json — {msg}")

    if not do_merge:
        if len(completed) == total and not errors:
            print(f"\nAll {total} domains complete. Run with --merge to update {'{upload_filename}'}")
        return

    if errors or pending:
        print("\nCannot merge: not all domains are complete and error-free.")
        sys.exit(1)

    print(f"\nMerging all {total} domains into {'{upload_filename}'} ...")
    merged = {"domains": []}
    for idx, slug, fix_path, fix_data in completed:
        original = source["domains"][idx]
        merged["domains"].append({
            "node_type": original["node_type"],
            "data": original["data"],
            "terms": fix_data["terms"],
        })

    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)

    total_terms = sum(len(d["terms"]) for d in merged["domains"])
    print(f"Written: {out_path}  ({total_terms} terms across {len(merged['domains'])} domains)")

if __name__ == "__main__":
    main()
```

---

## Step 7 — Run the split script

Use the Bash tool to run the split script:

```bash
cd /home/jimbob/Dev/AWS_Dev && source venv/bin/activate && python3 data/{stem}_domains/split_{stem_nodash}_domains.py
```

---

## Step 8 — Report

State:
- The upload file processed
- The output directory created
- The {N} domain files written (list each: index, slug, domain name, term count)
- The split and merge script names
- Any warnings (e.g., slug choices that were ambiguous)
