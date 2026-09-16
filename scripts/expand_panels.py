"""Incrementally expand a draft scenario up to a target panel count.

Thin CLI that forwards to `py.scenario.writer.expand_panels` with bounded
scene hints. Designed to be invoked by the Web API through `process_runner`.

Usage:
    python scripts/expand_panels.py --scenario-id abc12345 --target-count 6
    python scripts/expand_panels.py --scenario-id abc12345 --target-count 6 \\
        --scene-hint "Panel 4: rooftop chase" --scene-hint "Panel 5: face-off"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py.scenario.writer import expand_panels, RevisionFallback


def main() -> int:
    parser = argparse.ArgumentParser(description="Expand a draft scenario with extra panels via LLM")
    parser.add_argument("--scenario-id", required=True, help="Canonical scenario ID (8 chars hex)")
    parser.add_argument("--target-count", type=int, required=True, help=f"Desired final panel count (3..6)")
    parser.add_argument("--scene-hint", action="append", default=[], help="Optional per-panel hint (repeatable)")
    parser.add_argument("--json-result", action="store_true", help="Print machine-readable result last")
    parser.add_argument("--out", help="Optional override output path")
    args = parser.parse_args()

    candidates = list(Path("data/scenarios").glob(f"**/{args.scenario_id}.json"))
    if not candidates:
        raise SystemExit(f"Scenario file for {args.scenario_id} not found in data/scenarios")
    scenario_path = candidates[0]

    current = json.loads(scenario_path.read_text(encoding="utf-8"))
    if current.get("id") != args.scenario_id:
        raise SystemExit(
            f"--scenario-id {args.scenario_id!r} does not match record id {current.get('id')!r}"
        )

    if current.get("status") != "draft":
        # Expansion is only meaningful on draft — approved/rendered scenarios
        # should be revised instead.
        result = {
            "ok": False,
            "error": f"Expansion requires draft status, got {current.get('status')!r}",
            "code": "EXPANSION_REQUIRES_DRAFT",
        }
        if args.json_result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"❌ {result['error']}", file=sys.stderr)
        return 1

    try:
        updated = expand_panels(
            current,
            target_count=args.target_count,
            scene_hints=args.scene_hint or None,
        )
    except RevisionFallback as fallback:
        # Graceful: leave scenario unchanged, surface warnings.
        result = {
            "ok": True,
            "fallback": True,
            "id": current.get("id"),
            "panels_unchanged": True,
            "reason": fallback.reason,
            "warnings": fallback.warnings,
        }
        if args.json_result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"⚠️  Expansion fallback ({fallback.reason}); panels unchanged.", file=sys.stderr)
            for w in fallback.warnings:
                print(f"   • {w}", file=sys.stderr)
        return 0
    except Exception as error:
        result = {"ok": False, "error": str(error), "code": "EXPANSION_FAILED"}
        if args.json_result:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"❌ {error}", file=sys.stderr)
        return 1

    # Write atomically back to the same file (status remains draft)
    out_path = Path(args.out) if args.out else scenario_path
    out_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")

    result = {
        "ok": True,
        "id": updated["id"],
        "status": updated["status"],
        "panel_count": len(updated["panels"]),
        "added_panels": updated["expansion_history"][-1]["added_panels"],
        "path": str(out_path),
    }
    if args.json_result:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(
            f"✅ Expanded → {out_path} ({len(updated['panels'])} panels, "
            f"added: {result['added_panels']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
