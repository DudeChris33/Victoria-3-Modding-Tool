# Victoria 3 Modding Tool (V3MT)

A desktop GUI (Python / tkinter) that **writes Paradox Script mod files for Victoria 3**. It is not a mod itself: you point it at a mod folder and it creates, edits and cleans up the `.txt` / `.yml` files inside it, so you don't have to hand-edit hundreds of interlinked history, military, building and localization files.

The main job of the tool is **redrawing the map** (transferring states between countries, creating new countries and new states) while keeping everything that refers to those states consistent: buildings and their ownership, armies and fleets, generals and admirals, trade routes, diplomacy, power blocs, companies, capitals and so on.

> **Always work on a copy or enable Auto-backup.** The tool rewrites many files at once. Use `Backup Current Mod` or tick `Auto-backup` (see below) before running large operations.

---

## Contents

1. [Requirements](#requirements)
2. [Running the tool](#running-the-tool)
3. [First-time setup](#first-time-setup)
4. [The main window](#the-main-window)
5. [Feature guide](#feature-guide)
   - [Mod Manager](#mod-manager)
   - [Transfer States](#transfer-states)
   - [Create Country](#create-country)
   - [Military Manager](#military-manager)
   - [Modify Country](#modify-country)
   - [Diplomacy](#diplomacy)
   - [Powerbloc Manager](#powerbloc-manager)
   - [Religion / Culture](#religion--culture)
   - [State Manager](#state-manager)
   - [Journal / Event Manager](#journal--event-manager)
   - [Custom States](#custom-states)
   - [Visual Map Painter](#visual-map-painter)
6. [What gets cleaned up automatically](#what-gets-cleaned-up-automatically)
7. [Files the tool writes](#files-the-tool-writes)
8. [Tips and troubleshooting](#tips-and-troubleshooting)
9. [Building a standalone executable](#building-a-standalone-executable)
10. [Project layout / contributing](#project-layout--contributing)

---

## Requirements

- Windows, Python 3.10+ (tkinter ships with the standard Windows installer).
- A Victoria 3 install. The tool reads the **vanilla** `game` folder to look up data your mod doesn't override (strategic regions, state regions, definitions, etc.), e.g.
  `C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game`
- Optional but strongly recommended: **Pillow** and **NumPy**. They power the Visual Map Painter. Without them the rest of the tool still works, but the map-based buttons are hidden or disabled.

```bash
pip install pillow numpy
```

## Running the tool

```bash
python "Source Code.pyw"
```

or double-click `Source Code.pyw` (runs without a console window). A prebuilt `dist/V3MT/V3MT.exe` can be produced with PyInstaller (see [Building](#building-a-standalone-executable)).

## First-time setup

1. Launch the tool.
2. Either:
   - Click **Mod Manager → Create Mod** to scaffold a brand-new mod (you'll be offered to copy the vanilla files into it), **or**
   - Type/browse a path into **Mod Directory** to use an existing mod folder (the folder that contains `common/`, `history/`, `map_data/`, `localization/` ...).
3. When the tool first needs the vanilla game files it will ask you to locate the Victoria 3 `game` folder. This is remembered.

Your mod path and vanilla path are saved to a small `config.json` and restored on next launch.

> **Important:** most operations work on files that must exist in the *mod* folder. If a file only exists in vanilla, the tool copies/overrides it into your mod when it needs to change it. Copying the vanilla files into a new mod up front (`Mod Manager → Create Mod → Yes`) gives the most predictable results, especially for transfers, since the tool's military and building clean-up scans the mod's files.

## The main window

```
+--------------------------------------------------------------+
| Global Configuration      [Mod Manager] [Backup] [Auto-backup]|
| Mod Directory: [....................................] Browse |
+--------------------------------------------------------------+
| Transfer States | Create Country | Military | Modify | Diplomacy      <- row 1
| Powerbloc | Religion/Culture | State Manager | Journal/Event | Custom States  <- row 2
+--------------------------------------------------------------+
|  (the panel for the selected feature appears here)           |
|                                              [ Execute ]     |
+--------------------------------------------------------------+
| Execution Log  (info / warnings / errors / success, colour-coded)
+--------------------------------------------------------------+
```

- **Global Configuration bar** – mod directory, **Mod Manager**, **Backup Current Mod**, and the **Auto-backup** checkbox.
- **Navigation buttons** – each switches the central panel to a feature.
- **Execute button** (bottom right of the panel) – its label and action change per feature (e.g. "Execute Transfer", "Create & Transfer"). Some panels have their own buttons and hide it.
- **Execution Log** – everything the tool does is reported here. **Read the warnings (orange)**: they point at things the tool couldn't resolve automatically and that need a manual fix. Errors are red, successes green.

Long operations run on a background thread, so the window stays responsive. Wait for `Done.` / a success message in the log before starting the next action.

### Backups

- **Backup Current Mod** copies the mod folder next to itself as `<modname>_backup_1`, `_backup_2`, ... (never overwrites an earlier one).
- **Auto-backup** (checkbox) keeps a single rolling copy, `<modname>_autobackup`, refreshed before each write operation. It is off by default. Good for undoing the last action, but it is overwritten each time, so also take a numbered backup before big sessions.

---

## Feature guide

### Mod Manager

Open from the header bar. **Create New Mod** takes a mod name and a parent folder, creates the mod skeleton (including `.metadata`), makes it the active mod, and offers to copy vanilla game files into it.

### Transfer States

Moves state ownership from one country to another and fixes everything that depends on it.

| Field | Meaning |
|-------|---------|
| **New Owner Tag** | 3-letter tag receiving the states (e.g. `GBR`). Case does not matter. |
| **States** | Space-separated state names (e.g. `aquitaine ile_de_france`). Hidden in Full Annexation. |
| **Old Owner Tag(s)** | Who is losing the states. Hidden in Auto mode. |

Transfer modes:

- **Auto (All Owners)** – the tool detects who currently owns each listed state (all owners of a split state) and takes it for the new tag. You only list the states and the new owner.
- **Targeted (Split State)** – only take the states' land that belongs to the specified old tag(s). Useful when a state is shared between several countries. Tick **Blacklist (exclude)** to invert it: take land from *everyone except* the listed tags.
- **Full Annexation** – give the new tag **every state** owned by the listed old tag(s). The old country ceases to exist, so all references to it are updated or removed (diplomacy, power blocs, etc.).

Extras:

- **Open Visual Map Painter** – pick the states by clicking on the map instead of typing them. See [Visual Map Painter](#visual-map-painter).
- **Import States File...** – point at a `states` history file (e.g. from another mod). The tool diffs it against your current mod, lists the ownership changes it finds, and lets you execute them as a batch.

Click **Execute Transfer** to run. What happens, in order:

1. Detect the previous owners and (if needed) create a history file for the new tag.
2. Rewrite state ownership (`create_state`, `add_homeland`, owned provinces ...) and fix **building ownership** (see the rules below).
3. Ensure railway tech where the recipient needs it and clean trade history of the transferred states.
4. Move/clean **military formations** (armies and fleets) and handle **generals/admirals**.
5. Fix `set_capital` for countries that lost their capital state.
6. Validate character links and prune orphans.

### Create Country

Creates a new country tag and gives it states in one step.

- **New Country Tag, Name, Adjective** – the tag (3 chars), display name and adjective (localization is generated).
- **Taken From (Old Tag)** – the country the new one is carved out of. Unset fields (culture, religion, wealth, literacy, tech, laws...) **default to the old tag's values**.
- **Capital State** – the new country's capital (a state it will own).
- **Full Annexation** – the new country takes *all* of the old tag's states (the old one disappears). Otherwise list the **Other States** (must be owned by the old tag) in addition to the capital.
- **Tier / Type** – read from your game definitions (e.g. `kingdom`, `principality`; `recognized`, `unrecognized`, `colonial`).
- **Pick Color** – map colour (the tool also compares against existing country colours).
- **Cultures** and **Religion** – optional; defaults to the old tag's primary culture/religion.
- **Population Settings** – starting wealth and literacy effects (default: inherited).

Click **Create & Transfer**. It generates the country definition, localization, history file and common files, then runs the full [Transfer](#transfer-states) sequence for the states.

### Military Manager

Create and edit armies and fleets (Victoria 3 1.13+ format).

- **Create Military Formation** – country tag, formation name, target state (defaults to the capital if empty/invalid), type **Army** or **Navy**, and unit counts. Armies use `combat_unit` entries tied to a state region; fleets use `ship = { type = ship_type:... count = N }`.
- **Manage Existing Formations** – enter a tag, click **Load Formations**, pick one from the list, then **Update Formation** (rename / change unit counts) or **Delete Formation**.

During state transfers the tool handles military automatically: units stationed in transferred states are moved with them, and each general/admiral is handled by these cases:

| Case | Condition | Result |
|------|-----------|--------|
| 1 | Country survives; formation still has units | General stays |
| 2 | Country survives; formation emptied | General re-pointed to another surviving formation of the same type, or a warning is logged |
| 3 | Country ceases to exist | Character moved to the new owner's `stolen_generals_army/fleet` pool if they now own the home region; otherwise a warning asks for a manual fix |

### Modify Country

Enter a tag and click **Load Data**, edit, then save.

- **Country Identity** – name, adjective, colour, etc.
- **Culture & Religion** – edit primary cultures and religion. The **Population Conversion Tool** converts the country's existing pops to a chosen culture/religion (by mode and value).
- **Internal Politics** – government, economic system, trade policy, power structure laws, and capital state.
- **Ruler Designer** – first/last name, interest group and ideology of the ruler character.
- **Population Settings** – starting wealth/literacy; **Copy Settings** from another country; **Distribute New Total** rescales the country's total population across its states.

### Diplomacy

Enter a tag and **Load Data** to see its subject relationships (overlord/subject) and hostile/truce entries.

- **Remove Selected** deletes a pact.
- **Add New Relationship** – pick the target tag, pact type and category, then **Create**.
- **Set Relations** – set the numeric relations value between two tags.

### Powerbloc Manager

Create, modify or remove power blocs. Pick an existing bloc (or start new) and edit its tag/name/adjective, colour, **principles** (+/Remove) and **members** (+/Remove; subjects are automatically made members). **Create / Modify** saves; **Remove Power Bloc** deletes it and cleans up membership references.

### Religion / Culture

Two tabs:

- **Create Culture** – key, display name, colour, religion, heritage, language, traditions, graphics, ethnicities and name lists. **Save New Culture** writes the definition and localization.
- **Create Religion** – key, name, colour, heritage, icon. **Save New Religion**.

New cultures/religions then appear in the Create Country / Modify Country / State Manager dropdowns.

### State Manager

Load a state by name, then edit:

- **Homelands** – add/remove cultures that treat the state as a homeland; **Save**.
- **Buildings** – list, **Add**, **Remove**, **Update** level. Ownership blocks are generated according to the building-ownership rules (below).
- **Resources** – tabs for **Capped** (mines/forestry), **Arable** (farms) and **Discoverable** (oil/gold etc.); add, update, remove, then **Save Resources**.
- **Population** – a **Demographics Mixer** (sliders that rebalance culture/religion shares, then **Apply Changes**), or **Manual Edit**: set total population, edit an individual pop block, or do a full culture/religion conversion for the state.

### Journal / Event Manager

- **Journal Manager** – load or create journal entries (`je_*`): activation, completion and reward conditions are built with the `+` / `-` lists. Saved with localization and optionally added to a country's history.
- **Event Manager** – define events (namespace, id, title, description, flavor, image) and add **Options** (buttons) each with modifiers and effects. Includes a **Modifier Manager** to create reusable modifiers.

### Custom States

An entry point for the map editor in **custom-state mode**: create brand-new states or reshape existing ones by moving provinces between them. See below.

### Visual Map Painter

Requires Pillow + NumPy. It renders the province map from the game files in a zoomable window.

Controls: left-click to select, right-click as described per mode, middle-mouse drag to pan, mouse wheel / `+` `-` buttons to zoom.

**Transfer mode** (opened from Transfer States): enter a **Paint Tag**, click states (or switch to **Province Selector** to pick individual provinces for splitting states), then **Execute Pending**. **Reload Data** re-reads files from disk.

**Custom State mode** (opened from Custom States):

1. *Modify an existing state* – right-click a state to set it as the **Target**; left-click provinces to take them; press **Transfer Selected to Target**.
2. *Create a new state* – left-click the provinces you want, press **Create New State**, then enter a name and owner tag. Province lists, state region, strategic region, history and localization are generated.
3. **Clear Selection** resets; **Export Selected** exports the chosen provinces.

---

## What gets cleaned up automatically

When ownership changes, the tool also touches:

- **State history** – owners, homelands, province lists, `create_state` blocks.
- **Buildings** – ownership is regenerated per the rules below.
- **Military** – armies/fleets, generals and admirals (see Military Manager).
- **Trade** – trade history and trade routes involving transferred states/countries.
- **Companies, treaties, lobbies, power blocs** – references to annexed countries are removed or reassigned.
- **Diplomacy** – pacts/relations referencing a country that no longer exists are commented out or removed.
- **Capitals** – `set_capital` for countries that lost their capital.
- **Character links** – orphaned commanders pruned.

### Building ownership rules

Buildings are placed in one of four categories, which decide who owns them:

| Category | Ownership | Examples |
|----------|-----------|----------|
| A | State/government | government administration, railway, port |
| B | Self | mines, extraction, art academy |
| C | Financial district | all manufacturing |
| D | Manor house | farms, plantations |

Other buildings (monuments, canals, manor houses, financial districts, company HQs) never get ownership generated.

---

## Files the tool writes

| Output | Naming |
|--------|--------|
| Country history | `history/countries/TAG - Name.txt` |
| Generated common files | `99_auto_TAG.txt` |
| Localization | `auto_TAG_l_english.yml` |
| Backups | `<mod>_backup_N`, `<mod>_autobackup` (siblings of the mod folder) |
| Tool config | `config.json` (`mod_path`, `vanilla_path`) |

Conventions: country tags are 3 uppercase letters (`ENG`, `PRU`); entity prefixes are `building_`, `law_`, `je_`, `pmg_`; history files use safe assignment (`c:TAG ?= { ... }`).

## Tips and troubleshooting

- **Check the log.** Orange warnings mean a manual fix is needed (e.g. a general whose home region is now owned by a third country).
- **State names** are the state keys without the `STATE_` prefix, lowercase (e.g. `aquitaine`). The tool normalizes common typos/prefixes.
- **Nothing happens / "path" errors** – make sure the Mod Directory is set and exists, and that the vanilla path is valid.
- **Map painter is greyed out or missing** – install Pillow and NumPy.
- **Window seems frozen** – operations run in the background; watch the log until it prints `Done.`.
- **Verify results in-game** (or against a reference mod) after big changes. There are no automated tests; the tool's output is validated by inspection.
- Keep your own version control or backups of the mod; this tool edits files in place.

## Building a standalone executable

```bash
pip install pyinstaller pillow numpy
python -m PyInstaller --noconfirm --clean --onedir --windowed --name V3MT "Source Code.pyw"
```

The result is in `dist/V3MT/`.

## Project layout / contributing

Everything lives in one file, `Source Code.pyw`:

- `Vic3Logic` – all parsing, file I/O and game logic. New backend logic goes here.
- `V3MTApp` / `App` – all tkinter UI. New UI goes here.
- `DemographicsMixer`, `StateManager`, `ImportStatesDiffDialog`, `Vic3ProvincePainter` – supporting widgets/dialogs.

Notes for contributors: file operations must run in a daemon thread so the UI doesn't freeze; read config and game files with `utf-8-sig` falling back to `utf-8`; see `CLAUDE.md` for the detailed conventions (military system, building ownership, patching workflow).
