# Victoria 3 Modding Tool — Agent Guide

## What this project is

A Python/tkinter desktop GUI tool (`Source Code.pyw`, ~12,000 lines) that generates Paradox Script `.txt` files for Victoria 3 mods. It is **not** a mod — it writes mod files. There is no build system, no test runner, no package structure, and no web framework. The single source file is the entire codebase.

Two classes live in `Source Code.pyw`:
- `Vic3Logic` — all parsing, file I/O, and game-logic. All new backend logic goes here.
- `V3MTApp` — all tkinter UI. All new UI goes here.

Config lives at `V3MT/config.json` (`mod_path`, `vanilla_path`). Read with `utf-8-sig → utf-8` fallback everywhere.

## Before you touch any code

**Grep first, read second.** The file is ~12 k lines. Always locate the relevant method(s) with `Grep` before opening large sections with `Read`.

```
Grep pattern="def method_name" path="Source Code.pyw" output_mode="content"
```

**Use standalone `.py` patch scripts for every multi-line edit.** The Edit tool fails silently on tab-count mismatches. Write a script, run it, verify it prints `SUCCESS`, then delete it.

- Use anchor-based extraction when tab counts are uncertain:
  ```python
  si = content.find(anchor_start)
  ei = content.find(anchor_end, si) + len(anchor_end)
  content = content[:si] + new_block + content[ei:]
  ```
- Guard every replacement: `if old in content: ... else: print("ERROR: anchor not found")`
- Inspect exact whitespace with `repr(lines[i])` before building replacement strings.
- No `→` in `print()` on Windows (cp1252 error) — use `->` instead.

## Long operations

Any operation that touches files must run in a **daemon thread** — the UI freezes otherwise. Follow the existing pattern in `V3MTApp` (see `threading.Thread(..., daemon=True).start()`).

## Paradox Script conventions

- Entity key prefixes: `building_`, `law_`, `je_`, `pmg_`
- Country tags: 3-letter UPPERCASE (`ENG`, `PRU`)
- History files use `?=` safe assignment: `COUNTRIES = { c:TAG ?= { ... } }`
- Generated filenames: `99_auto_TAG.txt`, `TAG - Name.txt`, `auto_TAG_l_english.yml`
- Validate output by running the tool and inspecting files against `testmod/` reference files — there are no automated tests.
- Branches are named by character/feature (e.g. `artoria`, `alter`, `castoria`).

## Military system (Vic3 1.13.0+)

**Armies** — unchanged. Units are `combat_unit = { type = unit_type:X state_region = s:STATE count = N }`.

**Fleets** — new. Units are `ship = { type = ship_type:X count = N }` (no `state_region`). Ship types: `ship_type_ship_of_the_line`, `ship_type_frigate`, `ship_type_early_ironclad`. Named individual ships use `create_ship = { type = ... fleet = scope:... name = ... }` at country level.

**Generals/Admirals** — each formation holds at most 1; extras go to an idle pool (the game handles overflow). Link pattern:
```
create_character = { template = TAG_name save_scope_as = gen_scope ... }
scope:gen_scope = { transfer_to_formation = scope:fm_scope }
```

**`home_region`** (1.13+) — present on `create_character` blocks directly OR on the character's template in `common/character_templates/country_TAG.txt`. Use `get_character_home_region(template_name)` to look it up at runtime.

**Strategic regions** — never hardcode. `find_strategic_region(state_key)` reads from `common/strategic_regions/` at runtime (mod then vanilla).

### General/Admiral transfer cases (inside `process_military_extraction_multi_pass`)

| Case | Condition | Action |
|------|-----------|--------|
| 1 | Country survives, formation still has troops/ships | No action — general stays. |
| 2 | Country survives, formation emptied | Repoint `transfer_to_formation` to any surviving same-type formation in the same country. Log a warning if none exists. |
| 3 | Country ceases to exist (`get_all_owned_states` returns empty — checked AFTER `transfer_ownership_batch` has already updated state files) | For every `create_character`: get `home_region`, call `scan_state_region_owners` to find current owner, move to `stolen_generals_army/fleet` if owner == `new_tag`, otherwise warn for manual fix. Always remove the char block and its `scope:gen = { ... }` link from `inner_reconstructed`. |

After the if/else, `new_inner_parts = [inner_reconstructed]` and `emptied_formation_scopes.clear()` run unconditionally (required so Case 3 output is actually written).

### Key military methods

| Method | Purpose |
|--------|---------|
| `process_military_extraction_multi_pass` | Per-file workhorse — extracts units and generals, handles all 3 transfer cases. |
| `inject_new_formation` | Nested helper — merges units into existing formation or creates a new one; attaches generals to `first_fm_scope`. |
| `clean_military_smart` | Orchestrates `process_military_extraction_multi_pass` across all files; decides force-move vs. partial-move. |
| `find_strategic_region` | Runtime lookup of a state's strategic region from `common/strategic_regions/`. |
| `get_character_home_region` | Looks up `home_region` for a character template from `common/character_templates/`. |
| `scan_state_region_owners` | Returns list of bare tags that own land in a given state (reads mod + vanilla). |
| `get_all_owned_states` | Returns list of states owned by a tag (mod only — reflects post-transfer state). |

## Building ownership system

Four categories on `Vic3Logic` drive `get_ownership_block` and `fix_building_ownership`:

- `CAT_A_STATE` — always state ownership (`government_administration`, `railway`, `port`, etc.)
- `CAT_B_SELF` — self-referential ownership (mines, extraction, `art_academy`)
- `CAT_C_URBAN` — financial district ownership (all manufacturing)
- `CAT_D_RURAL` — manor house ownership (farms, plantations)

Buildings outside all four categories (monuments, canals, `manor_house`, `financial_district`, company HQs) must never have ownership generated — the `known_type` guard in `fix_building_ownership` handles this.

`fix_building_ownership(block_content, owner_tag, state_name, old_tag=None, full_annex=False)`:
- `full_annex=True` → country ceases to exist; update all ownership refs unconditionally.
- `full_annex=False` → country still exists; revert cross-state refs back to `old_tag`.

## Memory files

Detailed reference notes live in `.claude/projects/.../memory/project_overview.md`. Read that file at the start of any session for full rule details. Update it when rules or methods change.
