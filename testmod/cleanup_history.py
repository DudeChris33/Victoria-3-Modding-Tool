#!/usr/bin/env python3
"""
AD1861 history file cleanup and stub generator.

Steps:
  1. Collect all country tags from common/history/states/00_states.txt.
  2. Delete files in characters/, countries/, population/ for tags NOT in the states file.
  3. Delete files in characters/ and countries/ for tags that ARE in the states file
     but are marked country_type = decentralized in common/country_definitions/.
  4. Create a stub countries file for each non-decentralized states tag that lacks one.
  5. Create a stub population file for each non-decentralized states tag that lacks one.
"""

import re
from pathlib import Path

MOD_ROOT = Path(__file__).parent

STATES_FILE    = MOD_ROOT / "common" / "history" / "states" / "00_states.txt"
CHARACTERS_DIR = MOD_ROOT / "common" / "history" / "characters"
COUNTRIES_DIR  = MOD_ROOT / "common" / "history" / "countries"
POPULATION_DIR = MOD_ROOT / "common" / "history" / "population"
DEFS_DIR       = MOD_ROOT / "common" / "country_definitions"
LOC_FILE       = MOD_ROOT / "localization" / "english" / "countries_l_english.yml"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def get_tags_from_states() -> set[str]:
    """Return all country tags referenced in the states history file."""
    text = STATES_FILE.read_text(encoding="utf-8")
    # Handles both:  country = c:RUS   and   country = "c:RUS"
    return {m.group(1) for m in re.finditer(r'country\s*=\s*"?c:([A-Z0-9]{2,5})"?', text)}


def get_decentralized_tags() -> set[str]:
    """Return all tags marked country_type = decentralized in country definitions."""
    decentralized: set[str] = set()

    for def_file in DEFS_DIR.glob("*.txt"):
        text = def_file.read_text(encoding="utf-8")
        current_tag: str | None = None
        brace_depth = 0
        block_lines: list[str] = []

        for raw_line in text.splitlines():
            stripped = raw_line.strip()

            if brace_depth == 0:
                # Skip comments and blank lines at top level
                if stripped.startswith("#") or not stripped:
                    continue
                m = re.match(r'^([A-Z0-9]{2,5})\s*=\s*\{', stripped)
                if m:
                    current_tag = m.group(1)
                    brace_depth = 1          # the opening { in "TAG = {"
                    block_lines = [stripped]
            else:
                block_lines.append(stripped)
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth == 0:
                    block_text = "\n".join(block_lines)
                    if "country_type = decentralized" in block_text:
                        decentralized.add(current_tag)
                    current_tag = None
                    block_lines = []

    return decentralized


def get_country_names() -> dict[str, str]:
    """Return a dict mapping TAG → display name from the English localization file.

    Matches lines like:  TAG:0 "Country Name"  or  TAG: "Country Name"
    Skips adjective keys (TAG_ADJ).
    """
    names: dict[str, str] = {}
    text = LOC_FILE.read_text(encoding="utf-8-sig")
    for m in re.finditer(r'^\s+([A-Z0-9]{2,5}):\d*\s+"([^"]+)"', text, re.MULTILINE):
        tag, name = m.group(1), m.group(2)
        if not tag.endswith("_ADJ"):
            names[tag] = name
    return names


def tag_from_filename(path: Path) -> str:
    """Extract the uppercase tag from filenames like 'rus - russia.txt' or 'RUS \u2013 Russia.txt'.

    Handles ASCII hyphen (-), en-dash (\u2013), and em-dash (\u2014) as separators.
    """
    m = re.match(r'^([A-Za-z0-9]{2,5})\s*[-\u2013\u2014]\s*', path.stem)
    if m:
        return m.group(1).upper()
    return path.stem.upper()


def files_by_tag(directory: Path) -> dict[str, Path]:
    """Map uppercase tag → Path for every .txt file in a directory."""
    return {tag_from_filename(p): p for p in directory.glob("*.txt")}


# ---------------------------------------------------------------------------
# Stub templates
# ---------------------------------------------------------------------------

def stub_country(tag: str) -> str:
    return f"COUNTRIES = {{\n\tc:{tag} ?= {{\n\t\t\n\t}}\n}}\n"


def stub_population(tag: str) -> str:
    return (
        f"POPULATION = {{\n"
        f"\tc:{tag} ?= {{\n"
        f"\t\teffect_starting_pop_wealth_low = yes\n"
        f"\t\teffect_starting_pop_literacy_baseline = yes\n"
        f"\t}}\n"
        f"}}\n"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== AD1861 history cleanup ===\n")

    state_tags       = get_tags_from_states()
    decentralized    = get_decentralized_tags()
    active_tags      = state_tags - decentralized   # in states AND not decentralized
    country_names    = get_country_names()

    print(f"Tags in states file      : {len(state_tags)}")
    print(f"Decentralized tags       : {len(decentralized)}")
    print(f"Active (non-decentralized): {len(active_tags)}\n")

    deleted: list[str] = []
    created: list[str] = []

    # ------------------------------------------------------------------
    # Step 2: delete files for tags NOT present in the states file
    # ------------------------------------------------------------------
    for directory in (CHARACTERS_DIR, COUNTRIES_DIR, POPULATION_DIR):
        for tag, path in files_by_tag(directory).items():
            if tag not in state_tags:
                path.unlink()
                deleted.append(f"{directory.name}/{path.name}")

    # ------------------------------------------------------------------
    # Step 3: delete characters & countries files for decentralized tags
    # ------------------------------------------------------------------
    for directory in (CHARACTERS_DIR, COUNTRIES_DIR):
        for tag, path in files_by_tag(directory).items():
            if tag in decentralized:
                path.unlink()
                deleted.append(f"{directory.name}/{path.name}")

    # ------------------------------------------------------------------
    # Step 4: create stub countries files for missing active tags
    # ------------------------------------------------------------------
    existing_country_tags = set(files_by_tag(COUNTRIES_DIR).keys())
    for tag in sorted(active_tags):
        if tag not in existing_country_tags:
            name = country_names.get(tag, "Unknown")
            out = COUNTRIES_DIR / f"{tag} - {name}.txt"
            out.write_text(stub_country(tag), encoding="utf-8")
            created.append(f"countries/{out.name}")

    # ------------------------------------------------------------------
    # Step 5: create stub population files for missing active tags
    # ------------------------------------------------------------------
    existing_pop_tags = set(files_by_tag(POPULATION_DIR).keys())
    for tag in sorted(active_tags):
        if tag not in existing_pop_tags:
            name = country_names.get(tag, "Unknown")
            out = POPULATION_DIR / f"{tag} - {name}.txt"
            out.write_text(stub_population(tag), encoding="utf-8")
            created.append(f"population/{out.name}")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print(f"Deleted {len(deleted)} files:")
    for f in sorted(deleted):
        print(f"  - {f}")

    print(f"\nCreated {len(created)} stub files:")
    for f in sorted(created):
        print(f"  + {f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
