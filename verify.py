#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py — Independent Verification of the Stacks Project Relational Audit
=============================================================================
Recomputes the nulmeting cone and the healed cone from the proof graph.

The ledger holds 337 contracts. Sixty-eight of them were already registered
when the nulmeting stood at 839 open transfers and a cone of 8,630. The other
269 seal Shell 1. Seeding the baseline with all 337 tags mixes those two
generations and inflates the cone to 9,628.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PATCH_FILE = BASE_DIR / "patches" / "stacks_34_chapters_closure.patch"

# Wave 11, 5 Nov 2026 15:05 CET. Contracts stamped earlier are the 68 already
# on the ledger. Contracts from this instant on are the 269 Shell 1 seals.
NULMETING_UTC = "2026-11-05T14:00:00+00:00"

EXPECTED = {
    "contracts": 337,
    "pre_baseline_contracts": 68,
    "shell1_seals": 269,
    "shell1_open": 0,
    "shell2": 287,
    "shell3": 283,
    "open_residual": 570,
    "baseline_seeds": 839,
    "edges": 39027,
    "baseline_cone": 8630,
    "healed_cone": 7848,
    "freed": 782,
    "patch_files": 34,
    "patch_hunks": 337,
}


def cascade(parents: dict, seeds: set) -> int:
    visited = set(seeds)
    queue = deque(seeds)
    while queue:
        cur = queue.popleft()
        for parent in parents.get(cur, ()):
            if parent not in visited:
                visited.add(parent)
                queue.append(parent)
    return len(visited)


def main() -> int:
    t0 = time.time()
    print("=" * 78)
    print(" STACKS PROJECT RELATIONAL DEPENDENCY AUDIT -- INDEPENDENT VERIFICATION")
    print(" Baseline: Stacks Project commit a04446e5 (Columbia University)")
    print(" Method  : Relational Double-Entry Ledger (Stevin - Ijiri - Ellerman)")
    print("=" * 78)

    errors: list[str] = []

    def expect(name: str, got, want) -> None:
        mark = "OK" if got == want else "FAIL"
        print(f"    [{mark}] {name}: {got}")
        if got != want:
            errors.append(f"{name}: got {got}, want {want}")

    contracts_file = DATA_DIR / "contracts.json"
    schillen_file = DATA_DIR / "schillen.json"
    edges_file = DATA_DIR / "graph_edges.json"
    for path in (contracts_file, schillen_file, edges_file, PATCH_FILE):
        if not path.exists():
            print(f"[FAIL] Missing {path}")
            return 1

    contracts = json.loads(contracts_file.read_text(encoding="utf-8"))
    schillen = json.loads(schillen_file.read_text(encoding="utf-8"))
    edges = json.loads(edges_file.read_text(encoding="utf-8"))

    for contract in contracts:
        stamp = contract.get("tijd", "")
        if not (isinstance(stamp, str) and stamp.endswith("+00:00") and "T" in stamp):
            errors.append(f"unstamped contract {contract.get('tag')}")

    early = [c for c in contracts if c["tijd"] < NULMETING_UTC]
    late = [c for c in contracts if c["tijd"] >= NULMETING_UTC]
    early_tags = {c["tag"] for c in early}
    late_tags = {c["tag"] for c in late}
    shell_counts = Counter(schillen.values())
    open_now = set(schillen)

    print("\n[1] LITERATURE CONTRACTS")
    expect("contracts", len(contracts), EXPECTED["contracts"])
    expect("already on the ledger at the nulmeting", len(early), EXPECTED["pre_baseline_contracts"])
    expect("Shell 1 seals since the nulmeting", len(late), EXPECTED["shell1_seals"])
    expect("distinct Shell 1 tags", len(late_tags), EXPECTED["shell1_seals"])
    if early_tags & late_tags:
        errors.append("a tag is both pre-baseline and a Shell 1 seal")
    if early_tags & open_now or late_tags & open_now:
        errors.append("a sealed tag is still in the open residual")

    print("\n[2] RESIDUAL SHELLS")
    expect("Shell 1 still open", shell_counts.get("SCHIL1_CANON", 0), EXPECTED["shell1_open"])
    expect("Shell 2 didactic", shell_counts.get("SCHIL2_DIDACTISCH", 0), EXPECTED["shell2"])
    expect("Shell 3 frontier", shell_counts.get("SCHIL3_FRONTIER", 0), EXPECTED["shell3"])
    expect("open transfers", len(open_now), EXPECTED["open_residual"])

    raw_patch = PATCH_FILE.read_bytes()
    if raw_patch.startswith((b"\xff\xfe", b"\xfe\xff")):
        errors.append("patch is UTF-16; git apply needs UTF-8")
        patch_text = ""
    else:
        patch_text = raw_patch.decode("utf-8")
    if patch_text.startswith("\ufeff"):
        errors.append("patch carries a BOM")
    if "\u251c" in patch_text or "\ufffd" in patch_text:
        errors.append("patch contains mojibake")
    patch_files = sum(1 for line in patch_text.splitlines() if line.startswith("diff --git "))
    patch_hunks = sum(1 for line in patch_text.splitlines() if line.startswith("@@"))

    print("\n[3] LATEX PATCH")
    print(f"    - File                       : {PATCH_FILE.name}")
    print(f"    - Size                       : {len(raw_patch) / 1024:.1f} KB")
    expect("chapters in the patch", patch_files, EXPECTED["patch_files"])
    expect("hunks in the patch", patch_hunks, EXPECTED["patch_hunks"])

    parents = defaultdict(set)
    for src, tgt in edges:
        if src and tgt:
            parents[tgt].add(src)

    baseline_seeds = open_now | late_tags
    cascade_baseline = cascade(parents, baseline_seeds)
    cascade_now = cascade(parents, open_now)
    freed = cascade_baseline - cascade_now

    print(f"\n[4] CASCADE ({len(edges):,} proof edges, {time.time() - t0:.3f}s)")
    expect("proof edges", len(edges), EXPECTED["edges"])
    expect("baseline seeds (570 + 269)", len(baseline_seeds), EXPECTED["baseline_seeds"])
    expect("baseline cone", cascade_baseline, EXPECTED["baseline_cone"])
    expect("healed cone", cascade_now, EXPECTED["healed_cone"])
    expect("theorems freed", freed, EXPECTED["freed"])

    print("\n" + "=" * 78)
    if errors:
        print(f" VERIFICATION RESULT: [FAILED] {len(errors)} CHECK(S)")
        for err in errors:
            print(f"    - {err}")
        print("=" * 78)
        return 1

    print(" VERIFICATION RESULT: [PASSED] CONE RECOMPUTED FROM THE GRAPH")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
