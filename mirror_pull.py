#!/usr/bin/env python3
"""
mirror_pull.py  –  Pull *only the changed files* from Dropbox backup
into your local Unreal project, skipping cache/build folders.

Usage:
    python mirror_pull.py "D:\\DropBox\\GameDev\\Projects\\DishonoredDead" \
                          "D:\\GameDev\\Projects\\DishonoredDead"
"""
import argparse, filecmp, os, shutil, sys, time
from pathlib import Path

EXCLUDE_DIRS = {
    "DerivedDataCache",
    "Intermediate",
    os.path.join("Saved", "Cooked"),
    "Binaries",
}

def should_skip(rel_path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in rel_path.parts)

def mirror(src: Path, dst: Path):
    rel = src.relative_to(source_root)
    if should_skip(rel):
        return

    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)

        # Delete files/folders removed from the backup (rare but safe)
        dst_items = set(p.name for p in dst.iterdir()) if dst.exists() else set()
        src_items = set(p.name for p in src.iterdir())
        for orphan in dst_items - src_items:
            orphan_path = dst / orphan
            if orphan_path.is_dir():
                shutil.rmtree(orphan_path, ignore_errors=True)
            else:
                orphan_path.unlink(missing_ok=True)

        # Recurse
        for child in src.iterdir():
            mirror(child, dst / child.name)

    else:  # file
        if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
            shutil.copy2(src, dst)

def parse_args():
    p = argparse.ArgumentParser(description="Mirror Dropbox ▶ Local")
    p.add_argument("backup_path", help="Dropbox backup folder")
    p.add_argument("local_project", help="Local working project folder")
    return p.parse_args()

if __name__ == "__main__":
    args        = parse_args()
    source_root = Path(args.backup_path).expanduser().resolve()
    dest_root   = Path(args.local_project).expanduser().resolve()

    if not source_root.exists():
        sys.exit(f"❌ Backup folder not found: {source_root}")
    if not dest_root.exists():
        sys.exit(f"❌ Local project folder not found: {dest_root}")

    t0 = time.time()
    mirror(source_root, dest_root)
    print(f"✅ Pull complete → {dest_root}\n   Time: {time.time()-t0:.1f}s")
