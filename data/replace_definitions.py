#!/usr/bin/env python3
"""
Replace domain definitions in production by deleting existing domains and
re-uploading from a cleaned *_upload-fix.json file.

Requires: batch_upload Lambda must have category/short_reference in
optional_term_fields (patched in src/lambda_functions/batch_upload/handler.py).

Usage:
  export JWT="<cognito-id-token>"
  python3 data/replace_definitions.py <key>           # use shorthand key
  python3 data/replace_definitions.py <path>          # use file path directly
  python3 data/replace_definitions.py <key> --dry-run # preview only

Keys:
  aws                 aws_upload-fix.json                     (11 domains, 123 terms)
  aiml                ai_ml_upload-fix.json                    (8 domains, 104 terms)
  cpp                 cpp_upload-fix.json                     (10 domains,  94 terms)
  java                java_upload-fix.json                    (11 domains, 104 terms)
  python              python_upload-fix.json                  (13 domains, 112 terms)
  python-builtins     python_builtin_functions_upload-fix.json (2 domains,  89 terms)
  python-decorators   python_decorators_upload-fix.json        (1 domain,   10 terms)
  typescript          typescript_upload-fix.json               (9 domains,  82 terms)

How to get your JWT:
  Open the app in a browser → DevTools (F12) → Network tab →
  click any API request → Request Headers → Authorization value.
  It starts with "eyJ...". Copy the whole value.

Requires: pip install requests
"""
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed.  Run: pip install requests")
    sys.exit(1)

API_BASE = "https://3kuv3v3u89.execute-api.us-east-1.amazonaws.com/prod"

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Shorthand key → fix file (relative to DATA_DIR)
FIX_FILES = {
    "aws":               "aws_upload-fix.json",
    "aiml":              "ai_ml_upload-fix.json",
    "cpp":               "cpp_upload-fix.json",
    "java":              "java_upload-fix.json",
    "python":            "python_upload-fix.json",
    "python-builtins":   "python_builtin_functions_upload-fix.json",
    "python-decorators": "python_decorators_upload-fix.json",
    "typescript":        "typescript_upload-fix.json",
}


def resolve_fix_file(arg: str) -> str:
    """Return absolute path to fix file given a key or path."""
    if arg in FIX_FILES:
        return os.path.join(DATA_DIR, FIX_FILES[arg])
    # Treat as a direct path (absolute or relative to cwd)
    path = os.path.abspath(arg)
    if os.path.exists(path):
        return path
    print(f"Error: unknown key or file not found: '{arg}'")
    print(f"\nKnown keys: {', '.join(FIX_FILES)}")
    sys.exit(1)


def api_get(url: str, headers: dict) -> dict:
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"Error: GET {url} returned {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)
    return resp.json()


def api_delete(url: str, headers: dict) -> None:
    resp = requests.delete(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"Error: DELETE {url} returned {resp.status_code}")
        print(resp.text[:300])
        sys.exit(1)


def api_post(url: str, headers: dict, payload: dict) -> dict:
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code not in (200, 201):
        print(f"Error: POST {url} returned {resp.status_code}")
        print(resp.text[:1000])
        sys.exit(1)
    return resp.json()


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    positional = [a for a in args if not a.startswith("--")]

    if not positional:
        print(__doc__)
        sys.exit(1)

    fix_file = resolve_fix_file(positional[0])

    jwt = os.environ.get("JWT", "").strip()
    if not jwt:
        print("Error: JWT environment variable not set.")
        print("  export JWT='eyJ...'")
        sys.exit(1)

    auth_header = jwt if jwt.startswith("Bearer ") else f"Bearer {jwt}"
    headers = {"Authorization": auth_header, "Content-Type": "application/json"}

    with open(fix_file) as f:
        fix_data = json.load(f)

    domains_to_replace = fix_data.get("domains", [])
    target_names = [d["data"]["name"] for d in domains_to_replace]
    total_terms = sum(len(d.get("terms", [])) for d in domains_to_replace)

    print(f"=== Replace Definitions ===")
    print(f"Source  : {os.path.basename(fix_file)}")
    print(f"Domains : {len(target_names)}")
    print(f"Terms   : {total_terms}")
    print(f"Dry run : {dry_run}")
    print()

    # --- Step 1: Fetch current domains ---
    print("Fetching current domains from API...")
    body = api_get(f"{API_BASE}/domains", headers)
    existing_domains = body.get("data", {}).get("domains", [])
    domain_map = {d["name"]: d["id"] for d in existing_domains}
    print(f"Found {len(existing_domains)} domains in DB.\n")

    # --- Step 2: Delete matching domains ---
    print("Step 1 — Delete existing domains (terms cascade automatically):")
    deleted = []
    not_found = []

    for name in target_names:
        if name in domain_map:
            domain_id = domain_map[name]
            if dry_run:
                print(f"  [dry] Would delete: {name}")
            else:
                api_delete(f"{API_BASE}/domains/{domain_id}", headers)
                print(f"  ✓  Deleted: {name}")
                deleted.append(name)
        else:
            print(f"  …  Not in DB (will be created fresh): {name}")
            not_found.append(name)

    if dry_run:
        print(f"\n[dry-run] Would delete {len(target_names) - len(not_found)} domains,")
        print(f"          then upload {len(domains_to_replace)} domains / {total_terms} terms.")
        print("Re-run without --dry-run to apply.")
        return

    print(f"\nDeleted {len(deleted)}, {len(not_found)} not previously in DB.\n")

    # --- Step 3: Batch re-upload ---
    print("Step 2 — Upload fixed definitions via /batch/upload:")
    result_body = api_post(
        f"{API_BASE}/batch/upload",
        headers,
        {"batch_data": fix_data},
    )
    result = result_body.get("data", {})
    print(f"  ✓  Upload complete:")
    print(f"     Domains created : {result.get('domains_created', '?')}")
    print(f"     Terms created   : {result.get('terms_created', '?')}")
    print(f"     Domains skipped : {result.get('domains_skipped', '?')}")
    for msg in result.get("processing_summary", []):
        print(f"     {msg}")


if __name__ == "__main__":
    main()
