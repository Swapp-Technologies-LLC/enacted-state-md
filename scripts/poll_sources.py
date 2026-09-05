"""
poll_sources.py
Unified CLI Dispatcher for Deterministic Legislative Ingestion Pollers
Swapp Technologies LLC (Maryland)

Invariant: Zero model in the path (Rule 10). Hard generation rule only.
Exits non-zero with failing selector / URL if any required extraction fails.
"""

import sys
import argparse
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure scripts directory is in path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import poll_montgomery
import poll_anne_arundel

def main():
    parser = argparse.ArgumentParser(description="Deterministic Legislative Ingestion Poller Dispatcher")
    parser.add_argument(
        "--jurisdiction",
        choices=["all", "montgomery", "anne_arundel"],
        default="all",
        help="Jurisdiction to poll (default: all)"
    )
    args = parser.parse_args()

    total_ingested = 0
    errors = []

    if args.jurisdiction in ["all", "montgomery"]:
        try:
            print("\n=== Running Montgomery County Poller ===")
            total_ingested += poll_montgomery.poll()
        except Exception as e:
            errors.append(("montgomery", poll_montgomery.API_ENDPOINT, str(e)))

    if args.jurisdiction in ["all", "anne_arundel"]:
        try:
            print("\n=== Running Anne Arundel County Poller ===")
            total_ingested += poll_anne_arundel.poll()
        except Exception as e:
            errors.append(("anne_arundel", poll_anne_arundel.PORTAL_URL, str(e)))

    print("\n=======================================================")
    print(f"Deterministic Polling Run Completed.")
    print(f"Total new/updated records ingested: {total_ingested}")
    
    if errors:
        print(f"\nCRITICAL: {len(errors)} poller(s) failed during execution:", file=sys.stderr)
        for jur, url, err in errors:
            print(f"  [FAIL] Jurisdiction: {jur} | URL: {url} | Error: {err}", file=sys.stderr)
        print("Exiting with status code 1 to open issue. No model was used in the path.", file=sys.stderr)
        sys.exit(1)
    else:
        print("All pollers completed successfully with 0 errors.")
        sys.exit(0)

if __name__ == "__main__":
    main()
