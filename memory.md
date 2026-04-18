# memory.md — Victoria 3 Modding Tool

> Context document for AI agents. Covers `Source Code.pyw` (~13.3k lines, single-file Tkinter app).
> Authoritative line numbers verified against commit on branch `castoria`. Grep before trusting any line number if edits have landed since.

---

## 1. High-Level Overview

- **What it is:** Desktop GUI tool that *generates Paradox Script `.txt` files* for Victoria 3 mods. It is **not** a mod — it writes files into a user-selected mod directory.
- **Stack:** Python 3 + Tkinter (stdlib) + optional Pillow/NumPy for the map painter.
- **Shape:** Single `.pyw` file. No package structure, no build system, no tests. Validation is manual: run the tool, inspect output, load the mod in-game.
- **Entry point:** `Source Code.pyw:13347` — `if __name__ == "__main__": App().mainloop()`
- **Persistence:** `V3MT/config.json` stores `mod_path` and `vanilla_path`. Backups auto-zipped to `{mod_path}/.vic3_modtool_backups/` when enabled.
- **Repo layout:** `Source Code.pyw` (source), `V3MT/` (built exe + config), `testmod/` (reference Paradox files, NOT a test suite), `build/`, `dist/`, `V3MT.spec` (PyInstaller).

---

## 2. Class Map (file/module responsibilities)

All classes live in `Source Code.pyw`.

| Class | Line | Kind | Responsibility |
|---|---:|---|---|
| `Vic3Logic` | 25 | Core engine | All file I/O, parsing, and mod generation. Owns `StateManager`, `stop_event`, `log` callback, and mod/vanilla paths. Contains ~150 methods. |
| `DemographicsMixer` | 7373 | UI widget (`ttk.Frame`) | Editable table of culture/religion/percent rows, reused in Create-Country and Pop-History panes. Supports locked rows. |
| `StateObject` | 7614 | Data container | One Victoria 3 state: provinces, hubs (city/port/farm/mine/wood), naval_exit, impassable/prime lands, arable_land. |
| `StateManager` | 7631 | Registry/loader | Populates `states: Dict[STATE_ID, StateObject]` and `province_owner_map: Dict[hex, STATE_ID]` from `map/data/state_regions/*`. Mod paths override vanilla. |
| `App` | 8848 | Tk root window | Owns `Vic3Logic`, `log_queue`, and the ~10+ swappable UI panes. Spawns daemon threads for long ops. **Note:** class name is `App`, not `V3MTApp` (some older docs are wrong). |
| `Vic3ProvincePainter` | 12418 | `tk.Toplevel` | Visual province/state/political map editor. Needs PIL. Queues transfers, applies them in batch. |

```
┌─────────────────────────────────────────────────────────────┐
│ App (tk.Tk)                                                 │
│  ├─ logic: Vic3Logic                                        │
│  │   ├─ state_manager: StateManager                         │
│  │   │   └─ states: {STATE_ID -> StateObject}               │
│  │   ├─ stop_event: threading.Event                         │
│  │   └─ log: callback -> App.log_queue                      │
│  ├─ log_queue: queue.Queue  (thread -> UI bridge)           │
│  ├─ content_frame: swapped by show_*_ui()                   │
│  └─ spawns Vic3ProvincePainter on demand                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Module-Level Constants

On `Vic3Logic` (lines 26–28) — used by state-creation / economic templates:

```python
CAT_A_STATE  = [gov admin, construction, university, barrack, port, conscription]          # 6
CAT_B_SELFO  = [iron/coal mine, logging, fishing wharf, whaling, textile mill]              # 6
CAT_C_RURAL  = [17 agricultural buildings: wheat, rice, coffee, tea, opium, ...]
```

No other module-level config dicts. Runtime config lives in `V3MT/config.json`.

---

## 4. Key Logic Flows

### 4a. Create New Country
```
User fills form  ->  App.show_create_ui()  ->  App.run_create_logic()   [daemon thread]
                                                        │
                                                        ▼
                                 Vic3Logic.create_country_files(...)        line 643
                                   ├─ perform_auto_backup()                 (if enabled)
                                   ├─ write  common/country_definitions/99_auto_{TAG}.txt
                                   ├─ write  localization/english/auto_{TAG}_l_english.yml
                                   ├─ write  common/history/countries/{TAG} - {Name}.txt
                                   ├─ get_extended_history_data(old_tag)    line 462
                                   ├─ (optional) write coat of arms file
                                   └─ ensure_country_history_exists(...)
```

### 4b. State Ownership Transfer
```
App.run_transfer_logic()   [daemon]
    └─ Vic3Logic.perform_transfer_sequence()              line 2450
         ├─ scan_state_region_owners()      (detect current owners)
         ├─ ensure_country_history_exists(new_tag, donor_tag, states)
         ├─ transfer_ownership_batch()                    line 1679
         │    └─ rewrites common/history/countries/{tag}_history.txt
         ├─ process_military_extraction_multi_pass()      line 1752
         │    (groups by strategic region, moves units)
         ├─ clean_trade_history()                         line 1061
         └─ prune_references()                            ~line 2419
```

### 4c. Visual Map Click -> Queued Transfer
```
click on provinces.png  ->  on_map_click()   (~line 12800)
    -> PIL pixel lookup -> hex code
    -> province_owner_map[hex] -> STATE_ID
    -> pending_transfers.append((state, old_tag, new_tag))
  [Apply] button -> threads apply_pending_transfers() -> transfer_ownership_batch()
```

### 4d. Async Log Pump (every 100ms)
```
worker thread                        main (Tk) thread
-------------                        ----------------
self.log("msg") ─┐
                 └─> log_queue.put ──> App.process_log_queue()   line ~10599
                                         └─ drain queue -> append to scrolledtext
                                         └─ after(100, process_log_queue)
```

---

## 5. State & Important Attributes

### `Vic3Logic`
| Attr | Purpose |
|---|---|
| `mod_path` | User-selected mod root. Most methods no-op if empty. |
| `vanilla_path` | Optional vanilla game root; read-only fallback source. |
| `auto_backup_enabled` | Bool; triggers zip backup before destructive writes. |
| `stop_event` | `threading.Event()`. Long loops check `is_set()` for graceful cancel. |
| `state_manager` | `StateManager` instance; reloaded when paths change. |
| `log` | Callback injected by `App`; pushes to `log_queue`. |

### `StateManager`
| Attr | Purpose |
|---|---|
| `states` | `{STATE_ID: StateObject}` from `map/data/state_regions/*` (mod overrides vanilla). |
| `province_owner_map` | `{hex: STATE_ID}` reverse lookup for painter / province-level ops. |

Priority trick: path list is iterated **reversed** so mod path loads last and overwrites vanilla entries (line ~7650).

### `App`
| Attr | Purpose |
|---|---|
| `logic` | Single `Vic3Logic` instance, created at init. |
| `log_queue` | Thread-safe bridge for worker -> UI messages. |
| `is_processing` | Bool re-entry guard (not atomic, but single-UI-thread safe). |
| `path_var`, `vanilla_path_var` | `StringVar` bound to Entry widgets; persisted to `config.json`. |
| `cr_rgb` | Randomized RGB seed for Create-Country color preview. |
| `content_frame` | Replaced by `clear_content()` / `show_*_ui()` to swap panes. |
| `mode` | Current pane key, e.g. `"TRANSFER"`, `"CREATE_COUNTRY"`. |

---

## 6. External Integrations

- **Tkinter** (stdlib): core UI; `ttk`, `filedialog`, `colorchooser`, `messagebox`, `simpledialog`, `scrolledtext`.
- **Pillow (`PIL`) + NumPy**: *optional*. Guarded by `try/except ImportError` at top of file; `PIL_AVAILABLE` flag. Only the map painter (`Vic3ProvincePainter`) requires them.
- **Filesystem only.** No subprocess, no network, no DB.
- **Threading**: `threading.Thread` + `queue.Queue` for background work.

---

## 7. Threading Model

- Main thread: Tk event loop.
- Worker threads (all `daemon=True`) for:
  - `copy_vanilla_files` (mod bootstrap)
  - `run_army_logic` / `run_navy_logic`
  - `run_transfer_logic`, `run_create_logic`
  - map painter image load
- **Sync primitives:**
  - `log_queue` (Queue) — drained on the UI thread via `after(100, process_log_queue)`.
  - `stop_event` (Event) — polled inside long loops.
  - `is_processing` bool — blocks re-entry; adequate because only the UI thread toggles it.
- **Rule:** any method that walks files, zips backups, or rewrites many .txt files MUST run on a worker thread. If you call `Vic3Logic` directly from a UI callback, it will freeze Tk.

---

## 8. File I/O Map

Directories under `mod_path` (read & write), with vanilla equivalents under `vanilla_path/game/...` (read-only fallback):

| Path | Used for |
|---|---|
| `common/country_definitions/` | tag, color, tier, cultures, religion, capital |
| `common/history/countries/` | ownership, politics, laws, institutions, techs |
| `common/history/population/` | pops per state (culture, religion, literacy, wealth) |
| `common/history/military_formations/` | armies, navies |
| `common/history/characters/` | rulers, commanders |
| `common/strategic_regions/` | region groupings for military extraction |
| `common/cultures/`, `common/religions/`, `common/power_blocs/` | optional new content |
| `localization/english/` | `*_l_english.yml` locale strings |
| `map/data/state_regions/` (or `map_data/state_regions/`) | state geometry & provinces |
| `map_data/provinces.png` | province color -> hex for painter (PIL) |
| `V3MT/config.json` | paths (project-local, NOT in mod dir) |
| `{mod_path}/.vic3_modtool_backups/*.zip` | auto backups |

### Encoding pattern (repeated everywhere)
```python
try:
    with open(p, 'r', encoding='utf-8-sig') as f: content = f.read()
except Exception:
    with open(p, 'r', encoding='utf-8') as f: content = f.read()
```
Writes generally use `utf-8-sig`. Keep this pattern on new I/O paths.

---

## 9. Parsing Helpers

### `Vic3Logic.find_block_content(text, start_index)` — line 997
Matches balanced `{ ... }` around `start_index`:
- Tracks brace depth.
- Ignores braces inside `"..."` strings.
- Ignores braces after `#` comments.
- Returns `(open_idx, close_idx+1)` or `(None, None)`.

Typical use:
```python
m = re.search(r"STATE_TEXAS\s*=\s*\{", content)
s, e = self.find_block_content(content, m.end() - 1)
block = content[s:e]
```

### Recurring regex patterns
- `^\s*TAG\s*=` — assignment at line start (use `re.MULTILINE`).
- `(STATE_[A-Za-z0-9_]+)\s*=\s*\{` — state block header.
- `provinces\s*=\s*\{...\}` — province list.
- `owner\s*=\s*c:?\w+` — ownership line.
- `create_pop\s*=\s*\{...\}` — population block.
- `color\s*=\s*(hsv360|hsv|rgb)?\s*\{\s*X\s+Y\s+Z\s*\}` — colors; code handles 0–1 vs 0–255 and HSV/HSV360 conversion (lines 141–164).

---

## 10. Paradox Script Conventions (enforced when writing)

- Country tags: 3-letter UPPERCASE (`ENG`). `format_tag_clean()` strips leading `c:` and uppercases.
- State keys: `STATE_*`, spaces -> `_`. `normalize_state_key()` enforces this.
- Safe assignment in history files: `COUNTRIES = { c:TAG ?= { ... } }` (the `?=` is intentional).
- Generated filenames: `99_auto_{TAG}.txt`, `{TAG} - {Name}.txt`, `auto_{TAG}_l_english.yml`.
- Entity-name prefixes: `building_`, `law_`, `je_`, `pmg_`.

---

## 11. Edge Cases & Pitfalls

1. **Empty `mod_path`** — many methods silently no-op. Always set mod path before running logic.
2. **Missing `vanilla_path`** — map painter and military extraction degrade gracefully; confirm via `PIL_AVAILABLE` and path checks before assuming either works.
3. **UTF-8 BOM** — handle with the try/except pair above. Don't assume a single encoding.
4. **Tag prefix ambiguity** — `"c:ENG"` vs `"ENG"`. Always run through `format_tag_clean()`.
5. **State key ambiguity** — `"s:texas"` / `"TEXAS"` / `"STATE_TEXAS"`. Always run through `normalize_state_key()`.
6. **Mod-vs-vanilla precedence** — `StateManager` loads vanilla first, mod last (reversed iteration), so mod wins. Preserve this order if refactoring.
7. **UI freeze** — never call heavy `Vic3Logic` methods directly from a Tk callback. Thread them and log via `log_queue`.
8. **String/comment edge case** in `find_block_content`: escaped quotes are handled via `text[i-1] != '\\'` (line 1016) — imperfect but adequate for Paradox.
9. **Orphaned references** — deleting/transferring a country can leave dangling commander/formation refs; `perform_transfer_sequence` prunes them (~line 2419).
10. **Auto-backup side effect** — `create_country_files` calls `perform_auto_backup()` when enabled; it can be slow on large mods. Expect zip I/O.
11. **`StateManager` staleness** — it is reloaded by `set_mod_path` / `set_vanilla_path`. If you mutate state_region files mid-session, call `load_state_regions()` again.

---

## 12. Startup Sequence

```
python "Source Code.pyw"
    └─ App.__init__()                                   line 8848
        ├─ Vic3Logic(log_message)                        line 8858
        │   └─ StateManager(self)                        line 36
        │       └─ load_state_regions()                  line 7637
        ├─ _build_ui()  (scrollable nav + content_frame)
        ├─ load_config()  (reads V3MT/config.json)
        ├─ after(100, process_log_queue)                 (starts log pump)
        └─ show_transfer_ui()  (default pane)            line 9038
```

---

## 13. Fast Navigation Cheat-Sheet

- New feature that reads/writes Paradox files -> add a method to `Vic3Logic` (line 25–7372).
- New UI pane -> add `show_X_ui()` on `App`, thread the action via `run_X_logic()`.
- New widget reused across panes -> consider subclassing `ttk.Frame` like `DemographicsMixer`.
- Need state data -> `self.logic.state_manager.states[STATE_ID]`.
- Need to log from a thread -> `self.log("...")` (injected on `Vic3Logic`) — it goes through the queue.
- Grep first, read second: the file is too large to scan linearly.
