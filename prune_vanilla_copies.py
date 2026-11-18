"""One-off: delete files in a mod that are identical to the vanilla file at the same relative path.

Use on a mod that got a full vanilla copy, before switching it to "Use vanilla files (no full copy)".
The game loads vanilla's file when the mod lacks it, so removing an identical copy changes nothing in game.

Identical = same bytes, or for .txt/.yml same text after ignoring BOM, line endings and trailing whitespace.
Skipped: .metadata/, anything under the mod's replace_paths (vanilla is not loaded there).

Dry run by default. --apply makes a backup copy of the mod first, then deletes and removes empty folders.
--no-backup skips that copy (use when the mod is tracked in git).

  python prune_vanilla_copies.py "<mod folder>" "<Victoria 3 folder or its game folder>"
  python prune_vanilla_copies.py "<mod folder>" "<Victoria 3 folder>" --apply
"""
import argparse
import json
import os
import shutil
import sys

TEXT_EXT = {".txt", ".yml", ".gui", ".gfx", ".asset"}


def vanilla_base(path):
	g = os.path.join(path, "game")
	return g if os.path.isdir(g) else path


def replace_paths(mod):
	try:
		with open(os.path.join(mod, ".metadata", "metadata.json"), encoding="utf-8-sig") as f:
			meta = json.load(f)
		rps = (meta.get("game_custom_data", {}) or {}).get("replace_paths", []) or []
		return [str(p).replace("\\", "/").strip("/").lower() for p in rps]
	except Exception:
		return []


def norm_text(b):
	if b.startswith(b"\xef\xbb\xbf"):
		b = b[3:]
	return b.replace(b"\r\n", b"\n").rstrip()


def identical(a, b):
	with open(a, "rb") as fa, open(b, "rb") as fb:
		da, db = fa.read(), fb.read()
	if da == db:
		return True
	if os.path.splitext(a)[1].lower() in TEXT_EXT:
		return norm_text(da) == norm_text(db)
	return False


def main():
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	ap.add_argument("mod")
	ap.add_argument("vanilla")
	ap.add_argument("--apply", action="store_true", help="actually delete (after backing up the mod)")
	ap.add_argument("--no-backup", action="store_true", help="skip the _prebackup copy (e.g. the mod is in git)")
	args = ap.parse_args()

	mod = os.path.abspath(args.mod)
	base = vanilla_base(os.path.abspath(args.vanilla))
	if not os.path.isdir(mod) or not os.path.isdir(os.path.join(base, "common")):
		sys.exit(f"ERROR: bad paths. mod={mod} vanilla game folder={base}")
	rps = replace_paths(mod)

	dupes, kept, total_bytes = [], 0, 0
	for root, _, files in os.walk(mod):
		for f in files:
			p = os.path.join(root, f)
			rel = os.path.relpath(p, mod)
			rel_u = rel.replace("\\", "/").lower()
			if rel_u.startswith(".metadata/") or any(rel_u == r or rel_u.startswith(r + "/") for r in rps):
				kept += 1
				continue
			vp = os.path.join(base, rel)
			if os.path.isfile(vp) and identical(p, vp):
				dupes.append(p)
				total_bytes += os.path.getsize(p)
			else:
				kept += 1

	print(f"Identical to vanilla: {len(dupes)} files ({total_bytes / 1048576:.1f} MB). Kept: {kept}.")
	for p in dupes[:40]:
		print("  " + os.path.relpath(p, mod))
	if len(dupes) > 40:
		print(f"  ... and {len(dupes) - 40} more")

	if not args.apply:
		print("Dry run. Re-run with --apply to delete.")
		return

	if not args.no_backup:
		i = 1
		while os.path.exists(f"{mod}_prebackup_{i}"):
			i += 1
		backup = f"{mod}_prebackup_{i}"
		print(f"Backing up to {backup} ...")
		shutil.copytree(mod, backup)

	for p in dupes:
		os.remove(p)
	for root, dirs, files in os.walk(mod, topdown=False):
		if root != mod and not os.listdir(root):
			os.rmdir(root)
	print(f"Deleted {len(dupes)} files. Now tick 'Use vanilla files (no full copy)' for this mod in the tool.")


if __name__ == "__main__":
	main()
