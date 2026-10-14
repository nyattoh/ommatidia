#!/usr/bin/env python3
"""CLI utility to generate and verify dataset and protocol seal manifests."""

import argparse
import json
from pathlib import Path
import sys

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ommatidia.seal import (
    SealMismatchError,
    create_seal_manifest,
    verify_seal_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify or create protocol and dataset seals.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    create_parser = subparsers.add_parser("create", help="Create seal manifest from protocol and dataset files")
    create_parser.add_argument("--protocol", type=Path, default=Path("research/PROTOCOL.md"), help="Path to PROTOCOL.md")
    create_parser.add_argument("--datasets", type=Path, nargs="*", default=[], help="Dataset files to seal")
    create_parser.add_argument("--out", type=Path, default=Path("research/seal_manifest.json"), help="Output manifest path")

    verify_parser = subparsers.add_parser("verify", help="Verify files against an existing seal manifest")
    verify_parser.add_argument("--manifest", type=Path, default=Path("research/seal_manifest.json"), help="Path to seal manifest")

    args = parser.parse_args()

    if args.subcommand == "create":
        if not args.protocol.exists():
            print(f"Error: Protocol file not found: {args.protocol}", file=sys.stderr)
            return 1

        manifest = create_seal_manifest(
            protocol_path=args.protocol,
            dataset_paths=args.datasets,
            manifest_output_path=args.out,
        )
        print(f"Seal manifest successfully generated at {args.out}")
        print(f"Protocol hash: {manifest['protocol']['hash']}")
        return 0

    elif args.subcommand == "verify":
        if not args.manifest.exists():
            print(f"Error: Manifest file not found: {args.manifest}", file=sys.stderr)
            return 1

        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
            results = verify_seal_manifest(data, base_dir=Path.cwd())
            print("Seal verification passed successfully.")
            for key, ok in results.items():
                print(f"  {key}: {'OK' if ok else 'FAIL'}")
            return 0
        except SealMismatchError as exc:
            print(f"SEAL VERIFICATION FAILED: {exc}", file=sys.stderr)
            return 2


if __name__ == "__main__":
    sys.exit(main())
