#!/usr/bin/env python3
"""Domain generation worker — run locally against Qwen to build quiz domain data.

Usage:
  python -m pipeline.domain_gen.worker "Rust"
  python -m pipeline.domain_gen.worker "Roman History" --hints "focus on the Republic era"
  python -m pipeline.domain_gen.worker "Networking" --terms 60 --output data/networking_upload.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .orchestrator import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    """CLI entry point for the domain generation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate quiz domain data using Qwen on the local network.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "topic",
        help="Domain topic, e.g. 'Rust' or 'Roman History'",
    )
    parser.add_argument(
        "--hints",
        default="",
        help="Optional focus hints passed to the decomposition prompt",
    )
    parser.add_argument(
        "--terms",
        type=int,
        default=50,
        help="Total term target across all subdomains (default: 50)",
    )
    parser.add_argument(
        "--output",
        help="Output JSON path (default: data/<topic_slug>_upload.json)",
    )
    parser.add_argument(
        "--url",
        default="https://192.168.1.105/lite/v1",
        help="LLM API base URL (default: lite service at 192.168.1.105)",
    )
    parser.add_argument(
        "--model",
        default="thinker1",
        help="Model identifier (default: thinker1)",
    )
    args = parser.parse_args()

    topic_slug = args.topic.lower().replace(" ", "_")
    output_path = Path(args.output or f"data/{topic_slug}_upload.json")

    print(f"Topic:        {args.topic}")
    print(f"Target terms: {args.terms}")
    print(f"Output:       {output_path}")
    print(f"Endpoint:     {args.model} @ {args.url}")
    print()

    try:
        decomposition, upload_json = run_pipeline(
            topic=args.topic,
            hints=args.hints,
            total_terms=args.terms,
            base_url=args.url,
            model=args.model,
        )
    except json.JSONDecodeError as exc:
        sys.exit(f"Failed to parse subdomain decomposition as JSON: {exc}")
    except Exception as exc:
        sys.exit(f"Pipeline failed: {exc}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(upload_json, indent=2))

    total_terms = sum(len(d["terms"]) for d in upload_json["domains"])
    total_subdomains = len(upload_json["domains"])
    print(f"\nDone: {total_terms} terms across {total_subdomains} subdomains")
    print(f"Written: {output_path}")


if __name__ == "__main__":
    main()
