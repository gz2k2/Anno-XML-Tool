## Changelog


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