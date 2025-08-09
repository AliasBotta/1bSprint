#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

def list_dirs(p: Path):
    return sorted([d.name for d in p.iterdir() if p.is_dir() and not d.name.startswith(".")])

def load_pairs(json_path: Path):
    try:
        with json_path.open() as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"[ERR] File not found: {json_path}")
    except json.JSONDecodeError as e:
        sys.exit(f"[ERR] Invalid JSON in {json_path}: {e}")
    return {
        (entry["aCommit"], entry["name"])
        for entry in data
        if isinstance(entry, dict) and "aCommit" in entry and "name" in entry
    }

def choose_from_list(title: str, items: list[str]) -> str:
    if not items:
        sys.exit(f"[ERR] No options found for {title}.")
    print(f"\nSelect {title}:")
    for i, it in enumerate(items, 1):
        print(f"  {i}) {it}")
    while True:
        choice = input(f"Enter number (1-{len(items)}): ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(items):
                return items[idx - 1]
        print("Invalid choice, try again.")

def discover(root: Path, student: str|None, owner: str|None, repo: str|None, side_label: str):
    # student
    if student is None:
        students = list_dirs(root)
        student = choose_from_list(f"{side_label} student (miner)", students)
    # owner
    owner_dir = root / student
    if owner is None:
        owners = list_dirs(owner_dir)
        owner = choose_from_list(f"{side_label} repo owner/organization", owners)
    # repo
    leaf_root = owner_dir / owner
    if repo is None:
        repos = list_dirs(leaf_root)
        repo = choose_from_list(f"{side_label} repository name", repos)
    return student, owner, repo

def resolve_dataset_path(root: Path, student: str, owner: str, repo: str) -> Path:
    return (root / student / owner / repo / "dataset.json").resolve()

def ensure_file(path: Path) -> None:
    if not path.exists():
        parent = path.parent
        hint = ""
        if parent.exists():
            contents = "\n  ".join(sorted(p.name for p in parent.iterdir()))
            hint = f"\n[HINT] Contents of {parent}:\n  {contents}"
        sys.exit(f"[ERR] File not found: {path}{hint}")

def main():
    ap = argparse.ArgumentParser(
        description="Compare two dataset.json files. Select GOLD and MINE independently from repoMinedTarget/<student>/<owner>/<repo>/dataset.json."
    )
    # GOLD side
    ap.add_argument("-g", "--gold", type=Path,
                    help="Path to GOLD dataset.json (skips GOLD selection).")
    ap.add_argument("--gold-root", type=Path, default=Path("repoMinedTarget"),
                    help="Root dir for GOLD selection (default: repoMinedTarget).")
    ap.add_argument("--gold-student", help="GOLD student/miner.")
    ap.add_argument("--gold-owner", help="GOLD owner/org.")
    ap.add_argument("--gold-repo", help="GOLD repo (leaf).")

    # MINE side
    ap.add_argument("-m", "--mine", type=Path,
                    help="Path to MINE dataset.json (skips MINE selection).")
    ap.add_argument("--mine-root", type=Path, default=Path("repoMinedTarget"),
                    help="Root dir for MINE selection (default: repoMinedTarget).")
    ap.add_argument("--mine-student", help="MINE student/miner.")
    ap.add_argument("--mine-owner", help="MINE owner/org.")
    ap.add_argument("--mine-repo", help="MINE repo (leaf).")

    # Back-compat convenience: 3 positionals fill the MINE triple
    ap.add_argument("positional", nargs="*", help="[mine_student] [mine_owner] [mine_repo] (optional)")

    args = ap.parse_args()

    # Prefill MINE with positionals if given
    pos = args.positional
    mine_student = args.mine_student or (pos[0] if len(pos) >= 1 else None)
    mine_owner   = args.mine_owner   or (pos[1] if len(pos) >= 2 else None)
    mine_repo    = args.mine_repo    or (pos[2] if len(pos) >= 3 else None)

    # GOLD path
    if args.gold:
        gold_path = args.gold.resolve()
    else:
        gold_root = args.gold_root.resolve()
        if not gold_root.exists():
            sys.exit(f"[ERR] GOLD root not found: {gold_root}")
        gs, go, gr = discover(gold_root, args.gold_student, args.gold_owner, args.gold_repo, "GOLD")
        gold_path = resolve_dataset_path(gold_root, gs, go, gr)

    # MINE path
    if args.mine:
        mine_path = args.mine.resolve()
    else:
        mine_root = args.mine_root.resolve()
        if not mine_root.exists():
            sys.exit(f"[ERR] MINE root not found: {mine_root}")
        ms, mo, mr = discover(mine_root, mine_student, mine_owner, mine_repo, "MINE")
        mine_path = resolve_dataset_path(mine_root, ms, mo, mr)

    print(f"[INFO] GOLD: {gold_path}")
    print(f"[INFO] MINE: {mine_path}")

    ensure_file(gold_path)
    ensure_file(mine_path)

    gold_set = load_pairs(gold_path)
    mine_set = load_pairs(mine_path)

    missing = gold_set - mine_set   # in GOLD but not in MINE
    extra   = mine_set - gold_set   # in MINE but not in GOLD
    matched = gold_set & mine_set

    print("\n=== Summary ===")
    print(f"Total in GOLD:         {len(gold_set)}")
    print(f"Total in MINE:         {len(mine_set)}")
    print(f"Total matched:         {len(matched)}")
    print(f"Missing (GOLD only):   {len(missing)}")
    print(f"Extra   (MINE only):   {len(extra)}")

    if missing:
        print("\n--- In GOLD but NOT in MINE ---")
        for commit, test in sorted(missing):
            print(f"({commit}, {test})")

    if extra:
        print("\n--- In MINE but NOT in GOLD ---")
        for commit, test in sorted(extra):
            print(f"({commit}, {test})")

if __name__ == "__main__":
    main()
