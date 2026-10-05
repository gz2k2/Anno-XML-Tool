# Changelog

## 0.20.5-beta

### Added

- **Context menu in the property tree** (bottom left pane):
  - **Copy** – copies the text of the clicked cell (Property, Value or Text).
  - **Add to Value only Tags** / **Remove from Value only Tags** – marks a property as plain value, so it is no longer resolved as text or asset reference. Available on the *Property* column of entries that hold a value. Built-in tags are shown as *Built-in Value only Tag* and cannot be removed here.
  - **Add Tag to BUFFS / EFFECTS** / **Remove Tag from BUFFS / EFFECTS** – edits the *Buff/Effect XML tags* list (same list as in *Settings › XML Settings*). The Buffs/Effects pane updates immediately. The last remaining tag cannot be removed.
- **Copy** in the context menu of the asset table, References and Watchlist (next to *XML Export*).
- **`config_value_only.ini`:** stores user-defined value-only tags. They are merged with the built-in list and apply to Anno 117 and Anno 1800. Tags that are a text reference in a game (e.g. `LineID` in Anno 117) stay resolved there.
- **`config_buffs.ini`:** separate file for the Buff/Effect XML tags.

### Changed

- **Buff/Effect XML tags moved** from `config.ini` to `config_buffs.ini`. Existing tags are migrated automatically on first start and the `[Buffs]` section is removed from `config.ini`.
- **Context menus** open slightly to the right of the cursor, so the mouse can be moved straight down without touching the menu.
- **Disabled context menu entries** use the normal text color and are struck through instead of being greyed out, so they stay readable on dark themes.


### [0.20.2-beta] - 2026-10-02

#### Added
* **"Texts" Tab:** New tab to search for texts or GUIDs.
* **Configurable Font Size:** Added option to customize font size in Settings.

#### Fixed
* **GUID Comparison:** Improved the reliability of the GUID compare feature.
* **UI Fixes:** Resolved minor cosmetic issues.


**v0.14.2-beta**

- **Fixed**
  - minor cosmetic issues.


**v0.14.1-beta**

- **Changed**
  - **Optimized** GUID comparison.
  - **Improved** loading performance.
  - **Fixed** last used XML profile to load automatically on startup.


**v0.13.4-beta**

- **Added**
  - Theme selection under `Settings > General > Appearance` with live switching and persistence
  - Support for [qt-themes](https://pypi.org/project/qt-themes/) (Modern Dark/Light, One Dark Two, Atom One, Monokai, Dracula, Nord, Blender, GitHub, Catppuccin)
  - Built-in `Anno Dark` theme remains the default and stays available without any extra package
  - GUID Compare: line numbers with `+` / `-` / `~` change markers
  - GUID Compare: synchronized scrolling of both panes (vertical and horizontal)
  - GUID Compare: `Prev diff` / `Next diff` navigation and a summary of all changes
  - GUID Compare: `Ignore whitespace` option so pure indentation changes are not reported
  - XML base folders are now configured separately for `Anno 117` and `Anno 1800`

- **Changed**
  - `Settings` is now split into the sub-tabs `General` and `XML Settings`
  - Folder selectors group their entries by game
  - GUID Compare: differing lines are aligned side by side, changed words are highlighted within a line
  - GUID Compare: stronger diff colors for better readability, automatically adjusted to the active theme
  - GUID Compare: the toolbar is pinned to the top so both panes use the full remaining height
  - GUID lookup now streams the XML files instead of loading them completely, which noticeably reduces memory usage and speeds up large data sets
  - Searches from a previous request are cancelled when a new comparison is started

- **Fixed**
  - Crash when comparing GUIDs (`QThread: Destroyed while thread is still running`)
  - Referenced GUIDs inside an asset could be mistaken for the asset's own GUID
  - Defective XML files are skipped and reported in the engine log instead of failing silently
  - Anno 1800 compatibility


**v0.12.5-beta**
- **changed**
  - Enhanced the comparison tool for an improved diff view


**v0.12.2-beta**

- **Added**
  - Added a comparison tool for different game versions (requires `*.xml` files for each version)


**v0.11.2-beta**

- **Added**
  - Support for RdaConsole.exe (Gamefiles can now be extracted within the XML Tool)
  - Support for Anno 1800 Gamefiles