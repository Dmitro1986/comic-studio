#!/usr/bin/env python3
"""CLI script for exporting comics to PDF or ZIP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from py.lib.export_helper import export_to_pdf, export_to_zip


def main():
    parser = argparse.ArgumentParser(description="Export comic to PDF or ZIP")
    parser.add_argument("--scenario-id", required=True, help="Scenario ID")
    parser.add_argument("--format", required=True, choices=["pdf", "zip"], help="Export format")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--json-result", action="store_true", help="Output JSON result")

    args = parser.parse_args()

    try:
        out_path = Path(args.output)
        if args.format == "pdf":
            export_to_pdf(args.scenario_id, out_path)
        else:
            export_to_zip(args.scenario_id, out_path)

        res = {"ok": True, "scenario_id": args.scenario_id, "format": args.format, "output_path": str(out_path)}
        if args.json_result:
            print(json.dumps(res))
        else:
            print(f"Exported {args.scenario_id} to {out_path}")
    except Exception as e:
        err_res = {"ok": False, "error": str(e)}
        if args.json_result:
            print(json.dumps(err_res))
        else:
            print(f"Error exporting comic: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
