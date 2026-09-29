#!/usr/bin/env python3
"""Runs the balance sim (scripts/dev/balance_sim.gd) fast: every class/pet
variant in its own headless Godot at once, each sped up, then merges them.

    python3 tools/balance.py                   # everything
    python3 tools/balance.py --only warrior,magician:fire --levels 20,50
    python3 tools/balance.py --fights 6        # steadier numbers, still quick

Writes user://balance.json as the sim always did (the old one is kept as
balance_prev.json) and prints levels an hour per class and level, with the
change since the last run. Fights are random: with the default 4 fights a
monster, a row moves ~10% run to run; use --fights 8 before trusting a small
difference.

The sim's clock is physics time, so --scale changes how long it takes, not the
numbers (checked 20x, 60x, 120x). If the machine can't keep up, the fights
just run slower; the summary says what speed they reached.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GODOT = os.environ.get("GODOT", "/Applications/Godot.app/Contents/MacOS/Godot")


def user_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Godot/app_userdata/Emberfall")
    if os.name == "nt":
        return os.path.join(os.environ["APPDATA"], "Godot", "app_userdata", "Emberfall")
    return os.path.expanduser("~/.local/share/godot/app_userdata/Emberfall")


def variants():
    """The sim's VARIANTS, read from the script so the two can't disagree."""
    src = open(os.path.join(ROOT, "scripts/dev/balance_sim.gd")).read()
    block = src[src.index("const VARIANTS"):src.index("const FIGHTS")]
    return re.findall(r'\["(\w+)", "(\w*)"\]', block)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", default="", help="classes or class:pet, comma separated")
    ap.add_argument("--levels", default="", help="e.g. 20,50")
    ap.add_argument("--fights", type=int, default=4, help="fights per monster (3 monsters a level)")
    ap.add_argument("--scale", type=int, default=120, help="game seconds per real second")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2), help="Godot processes at once")
    args = ap.parse_args()

    wanted = [v for v in variants() if not args.only or v[0] in args.only.split(",") or "%s:%s" % v in args.only.split(",")]
    if not wanted:
        sys.exit("nothing matches --only %s" % args.only)
    tmp = tempfile.mkdtemp(prefix="balance_")
    started = time.time()
    queue = list(wanted)
    running = {}  # variant -> (process, out path, log path)
    done = {}
    while queue or running:
        while queue and len(running) < args.jobs:
            v = queue.pop(0)
            tag = "%s_%s" % v if v[1] else v[0]
            out = os.path.join(tmp, tag + ".json")
            log = os.path.join(tmp, tag + ".log")
            env = dict(os.environ, BALANCE_ONLY="%s:%s" % v, BALANCE_OUT=out, BALANCE_SCALE=str(args.scale),
                       BALANCE_FIGHTS=str(args.fights), BALANCE_LEVELS=args.levels)
            proc = subprocess.Popen([GODOT, "--headless", "--path", ROOT, "--", "--autotest", "--only=balance"],
                                    env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
            running[v] = (proc, out, log)
        time.sleep(0.5)
        for v in list(running):
            proc, out, log = running[v]
            if proc.poll() is not None:
                del running[v]
                done[v] = (out, log)
                print("  %-22s done  (%d of %d, %.0f s)" % ("%s %s" % v, len(done), len(wanted), time.time() - started), flush=True)

    rows, speeds = [], []
    config = {}
    for v in wanted:
        out, log = done[v]
        text = open(log).read()
        m = re.search(r"fights ran at x(\d+)", text)
        if m:
            speeds.append(int(m.group(1)))
        if not os.path.exists(out):
            print("!! %s %s wrote nothing; its log: %s" % (v[0], v[1], log))
            continue
        data = json.load(open(out))
        rows += data["rows"]
        config = data["config"]
    config["fights"] = args.fights
    config["scale"] = args.scale

    path = os.path.join(user_dir(), "balance.json")
    prev = {}
    if os.path.exists(path):
        old = json.load(open(path))
        prev = {(r["class"], r["pet"], r["level"]): r for r in old.get("rows", [])}
        os.replace(path, os.path.join(user_dir(), "balance_prev.json"))
    with open(path, "w") as f:
        json.dump({"rows": rows, "config": config}, f, indent=1)

    levels = sorted({r["level"] for r in rows})
    print("\nlevels an hour (change since the last run in brackets; deaths after a slash)")
    print("%-20s" % "" + "".join("%13s" % ("L%d" % l) for l in levels))
    for v in wanted:
        line = "%-20s" % ("%s %s" % v).strip()
        for l in levels:
            r = next((r for r in rows if (r["class"], r["pet"], r["level"]) == (v[0], v[1], l)), None)
            if r is None:
                line += "%13s" % "-"
                continue
            cell = "%.2f" % r["levels_per_hour"]
            p = prev.get((v[0], v[1], l))
            if p:
                cell += "(%+.1f)" % (r["levels_per_hour"] - p["levels_per_hour"])
            if r["deaths"]:
                cell += "/%d" % r["deaths"]
            line += "%13s" % cell
        print(line)
    print("\n%d rows, %d fights each, x%d, %d jobs: %.0f s. Wrote %s" % (len(rows), args.fights * 3, args.scale, args.jobs, time.time() - started, path))
    if speeds:
        print("Speed reached: x%d to x%d (asked x%d). Below the ask the machine is the limit: the numbers are the same, it only takes longer." % (min(speeds), max(speeds), args.scale))


if __name__ == "__main__":
    main()
