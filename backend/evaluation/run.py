"""
Empirical Evaluation CLI Runner for AI-Powered Cross-Language Knowledge Transfer Platform.

Usage:
    python -m backend.evaluation.run --domain cloud_computing --lang hi
    python -m backend.evaluation.run --domain biomedical_devices --lang hi --sample-size 20
"""

import argparse
import json
import sys
from pathlib import Path

from backend.services.eval_service import eval_service


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run empirical evaluation across B1 (generic MT), B2 (static glossary), and P (proposed pipeline)."
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="cloud_computing",
        choices=["cloud_computing", "biomedical_devices"],
        help="Domain to evaluate on.",
    )
    parser.add_argument(
        "--lang",
        "--target-lang",
        dest="target_lang",
        type=str,
        default="hi",
        help="Target language code (e.g., 'hi', 'ta', 'de', 'es').",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Optional number of sentences to sample (default: all).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to write summary JSON results.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print("AI-POWERED CROSS-LANGUAGE KNOWLEDGE TRANSFER PLATFORM")
    print("EMPIRICAL BENCHMARK EVALUATION HARNESS")
    print("=" * 70)
    print(f"Domain:      {args.domain}")
    print(f"Target Lang: {args.target_lang}")
    print(f"Sample Size: {args.sample_size or 'Full test split'}")
    print("Running comparative evaluation...")

    results = eval_service.run_comparative_evaluation(
        domain=args.domain,
        target_lang=args.target_lang,
        sample_size=args.sample_size,
    )

    print("\n" + "=" * 70)
    print(f"EVALUATION COMPLETE - Run ID: {results.get('eval_id')}")
    print(f"Run Directory: {results.get('run_dir')}")
    print("=" * 70)

    # Print summary table
    headers = [
        "Condition",
        "TSR (%)",
        "BLEU",
        "chrF++",
        "AUROC",
        "ECE",
        "Rev Vol %",
        "p50 (s)",
        "p95 (s)",
    ]
    col_fmt = "{:<24} {:>8} {:>7} {:>7} {:>7} {:>7} {:>10} {:>8} {:>8}"
    print(col_fmt.format(*headers))
    print("-" * 96)

    conditions = results.get("conditions", {})
    for cond_key, metrics in conditions.items():
        print(
            col_fmt.format(
                cond_key,
                f"{metrics.get('tsr', 0.0):.2f}",
                f"{metrics.get('bleu', 0.0):.2f}",
                f"{metrics.get('chrf', 0.0):.2f}",
                f"{metrics.get('auroc', 0.0):.3f}",
                f"{metrics.get('ece', 0.0):.3f}",
                f"{metrics.get('review_volume_percentage', 0.0):.1f}%",
                f"{metrics.get('latency_p50', 0.0):.3f}",
                f"{metrics.get('latency_p95', 0.0):.3f}",
            )
        )
    print("-" * 96)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Summary written to {out_path.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
