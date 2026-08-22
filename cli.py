#!/usr/bin/env python3
"""
Age of Enteland — CLI

Usage:
    python3 cli.py plan --level 2 --level-file path/to/level2.json --out level2_actions.txt
    python3 cli.py run  --level 2 --level-file path/to/level2.json --actions level2_actions.txt

`plan` runs the heuristic GreedySolver end-to-end and writes the submission
JSON (`{"actions": [...]}`) to --out, plus a human-readable log alongside it.

`run` replays an existing actions file (e.g. one you hand-wrote, or want to
re-verify) through the Simulator and prints the resulting log/summary — use
this to sanity-check a submission before uploading it, exactly as the
challenge's own engine will.
"""
import argparse
import json
import sys

from enteland.state import Level
from enteland.simulator import Simulator
from enteland.solver import GreedySolver
from enteland import scoring


def summarize(result, level_number, label=""):
    print(f"\n=== {label} ===")
    print(f"Final tick: {result.final_tick}")
    print(f"Final Enteloot: {result.final_enteloot:.0f}")
    print(f"Items sold (count): {result.total_sold}")
    inv = {k: v for k, v in result.final_inventory.items() if v}
    print(f"Held inventory: {inv if inv else '(empty)'}")
    built = result.upgrades_built()
    print(f"Upgrades built: {built if built else '(none)'}")
    est = scoring.estimate_score(result, level_number)
    print(f"Estimated score (proxy, NOT the official formula): {est:.0f}")
    ok = sum(1 for r in result.to_log_rows() if r["status"] == "ok")
    invalid = sum(1 for r in result.to_log_rows() if r["status"] == "invalid")
    skipped = sum(1 for r in result.to_log_rows() if r["status"] == "skipped_tick_limit")
    print(f"Actions: {ok} ok, {invalid} invalid, {skipped} skipped (tick limit)")


def cmd_plan(args):
    level = Level.load(args.level_file, level_number=args.level)
    solver = GreedySolver(level, args.level, verbose=args.verbose)
    actions, result = solver.run()
    summarize(result, args.level, label=f"PLAN level {args.level}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"actions": actions}, f, indent=2)
    print(f"\nWrote {len(actions)} actions to {args.out}")

    if args.log:
        with open(args.log, "w", encoding="utf-8") as f:
            for row in result.to_log_rows():
                f.write(json.dumps(row) + "\n")
        print(f"Wrote per-action log to {args.log}")


def cmd_run(args):
    level = Level.load(args.level_file, level_number=args.level)
    with open(args.actions, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or not isinstance(payload.get("actions"), list):
        print("Submission rejected outright: top-level 'actions' key missing or not an array. Score = 0.")
        sys.exit(1)
    sim = Simulator(level)
    result = sim.run(payload["actions"])
    summarize(result, args.level, label=f"RUN level {args.level} ({args.actions})")
    if args.log:
        with open(args.log, "w", encoding="utf-8") as f:
            for row in result.to_log_rows():
                f.write(json.dumps(row) + "\n")
        print(f"Wrote per-action log to {args.log}")


def main():
    p = argparse.ArgumentParser(description="Age of Enteland engine/solver CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("plan", help="run the heuristic solver and write a submission file")
    pp.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4])
    pp.add_argument("--level-file", required=True)
    pp.add_argument("--out", required=True, help="path to write the actions .txt (JSON) to")
    pp.add_argument("--log", default=None, help="optional path to write a per-action JSONL log")
    pp.add_argument("--verbose", action="store_true")
    pp.set_defaults(func=cmd_plan)

    pr = sub.add_parser("run", help="replay an actions file through the simulator")
    pr.add_argument("--level", type=int, required=True, choices=[1, 2, 3, 4])
    pr.add_argument("--level-file", required=True)
    pr.add_argument("--actions", required=True, help="path to a .txt/.json actions submission")
    pr.add_argument("--log", default=None, help="optional path to write a per-action JSONL log")
    pr.set_defaults(func=cmd_run)

    pk = sub.add_parser("package", help="package python source files into a submission zip")
    pk.add_argument("--out", default="submission.zip", help="path to zip file")
    pk.set_defaults(func=cmd_package)

    args = p.parse_args()
    args.func(args)


def cmd_package(args):
    import zipfile
    import os
    zip_path = args.out
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk("enteland"):
            if "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    full = os.path.join(root, file)
                    zf.write(full, arcname=full)
        for extra in ["cli.py", "resources.json"]:
            if os.path.exists(extra):
                zf.write(extra, arcname=extra)
    print(f"Created submission ZIP at {zip_path}")


if __name__ == "__main__":
    main()
