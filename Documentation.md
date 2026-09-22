### Anno XML Viewer Documentation

#### English Version

---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

##### 1. Introduction

The **Anno XML Viewer** is a specialized tool for modders of the _Anno_ series. It allows high-performance browsing, searching, and analysis of game assets from assets.xml. The tool resolves text IDs into readable strings, maps relationships between assets, and helps inspect linked buffs, effects, templates, and XML structures.

**Anno 117 and Anno 1800 are supported side by side.** Both games use the same file names but map their contents differently, so each title has its own data profile. Folders, watchlists and text resolution rules are kept separate per game.

##### 2. Supported Games and Data Differences

| Aspect | Anno 117 | Anno 1800 |
| --- | --- | --- |
| Text key in texts\_\*.xml | `<Text><LineId>` | `<Text><GUID>` |
| Display name reference | `Text/OasisId` | the asset's own `Standard/GUID` |
| Inline display text | – | `LocaText/English/Text` |
| Extra data file | – | `properties.xml` |
| Technology name | `Tech/VisibleTechName` | – |

Consequences you will notice in the UI:

- In Anno 1800 an asset's GUID **is** its text key, so the display name is looked up directly with the GUID — no indirection.
- `LineID` is a genuine text reference in Anno 117, but an internal number in Anno 1800 and is therefore never resolved there.
- Plain quantities such as `<Amount>`, `<InactiveAmount>` and `<MaximumHitPoints>` reference nothing at all. They are shown as numbers and are no longer matched against the asset database.
- Only tags that are explicitly declared as text references are looked up in texts\_\*.xml; every other number in an asset stays a value.

**Game detection:** when a folder is loaded, the tool first checks which game list it was added to. If it is unknown, the folder content decides — the text key element used in texts\_\*.xml and the presence of properties.xml.

##### 3. Getting Started

- **Select Data Folder:** Open the **Settings** tab, switch to **XML Settings**, and use **Browse...** to add one or more folders containing your XML files. Folders are managed separately for **Anno 117 XML Files** and **Anno 1800 XML Files**. A folder must contain assets.xml; templates.xml and texts\_\*.xml are recommended for full functionality.
- **Choose Active Folder:** Use the XML path dropdown in the top bar to switch between saved XML folders. Entries are grouped by game with a highlighted group header. Switching the active folder reloads the data and switches the watchlist to that game.
- **Language:** Select the display language in the top bar. Set the default language in **Settings > General**.
- **Theme:** Choose a color scheme under **Settings > General > Appearance**. Changes apply immediately.
- **Loading:** The tool parses the data in the background. Check the **Engine Log** tab for progress and status messages, including which game profile was used.

##### 4. Core Features

###### Asset Editor & Search

- **Search Bar:** Enter one or more terms to find assets.
- Spaces use "AND" logic, for example farm sheep.
- A minus prefix excludes terms, for example farm -module.
- **Search Depth:** By default, the search checks GUID, display name, and template. Disable **Search only GUID Text** to search all XML text content inside assets. This is slower but more thorough.
- **Template Filter:** Click **Template Filter...** to select or deselect template categories. The popup includes a template search field plus **Select All** and **Deselect All** buttons.
- **Asset Table:** Shows GUID, display name, and template. Selecting a row updates the analysis panes.

###### Watchlist

- The **WATCHLIST** panel stores selected assets by GUID for quick access.
- **Anno 117 and Anno 1800 have separate watchlists.** The panel header shows which game's list is currently displayed and the list follows the game of the loaded XML folder.
- Use **+** to add the currently selected asset.
- Use **-** to remove the selected watchlist entry.
- Watchlist entries are saved per game in config.ini and restored on restart. A watchlist from an earlier version is migrated to the game of the folder that was active back then.

###### Analysis Panes

- **Property Tree:** Displays the \<Values\> section of the selected asset in a readable tree. GUIDs and text IDs are resolved into names where possible; pure quantities are left untouched.
- **XML View:** Shows the raw, formatted XML of the selected asset.
- **Buffs / Effects:** Shows linked assets referenced through configured buff/effect tags. Use the **Filter...** button to select which categories are shown. Which child element holds the referenced GUID is defined per game.
- **References:** Shows reverse-search results: assets that reference the currently selected GUID.

###### GUID Compare

The **GUID Compare** tab shows a single asset from two data folders side by side, which makes it easy to see what a patch changed. Each folder requires its own set of \*.xml files.

- **Select a GUID:** Enter it directly or pick an entry from the **Watchlist** dropdown.
- **Select Folders:** Choose the folder for the left and right pane. Both dropdowns list the same folders as the top bar, grouped by game.
- **Aligned Diff:** Both panes always show the same number of rows. Lines that exist only on one side are padded on the other so matching content stays on the same row.
- **Line Numbers and Markers:** The gutter shows the original line number of each line plus a marker: + for lines that exist only on this side, - for removed lines, and ~ for modified lines.
- **Word Highlighting:** Within a modified line, only the words that actually differ are highlighted.
- **Synchronized Scrolling:** Both panes scroll together, horizontally and vertically.
- **Navigation:** **Prev diff** and **Next diff** jump from one block of changes to the next. Consecutive changed lines count as a single block.
- **Ignore whitespace:** Enabled by default. Lines are compared without leading and trailing whitespace so pure indentation changes are not reported as differences.
- **Summary:** The status text next to the toolbar shows how many lines were changed and how many exist on only one side.
- **Theme-aware colors:** The diff palette is rebuilt from the editor background, so added/removed/changed rows stay readable on dark and light themes alike.
- The lookup streams the XML files instead of loading them completely, so even large assets.xml files can be searched without high memory usage. The source file of a match is added as a comment in the first line. Starting a new comparison cancels searches that are still running.

###### Templates

The **Templates** tab lists templates from templates.xml.

- Use the search field to filter templates.
- Selecting a template shows its formatted XML preview.

###### Structure Library

The **Structure Library** tab catalogs unique XML tag paths found in the loaded data.

- Use the search field to filter paths.
- Selecting a path shows a structural preview and known values for that path across the dataset.

###### Engine Log

The **Engine Log** tab displays background loading progress, parser messages, warnings, and errors. It reports which game profile a folder was loaded with, warns when a texts\_\*.xml contains no keys of the expected type (a sign that the folder is listed under the wrong game), reports the theme status at startup and lists XML files that were skipped because they could not be parsed.

###### Settings

The **Settings** tab stores application configuration and is divided into two sub-tabs.

**General**

- **Default Language:** Choose the language selected by default after loading.
- **Appearance:** Select the application theme. **Anno Dark (built-in)** is always available. If the optional package **qt-themes** is installed, additional color schemes such as Modern Dark/Light, One Dark Two, Atom One, Monokai, Dracula, Nord, Blender, GitHub, and Catppuccin are listed as well. The selection is applied immediately and restored on restart. If qt-themes cannot be used, the reason is shown next to the selector.
- **Game Folders:** Configure the Anno 117 and Anno 1800 installation folders used for gamefile extraction.
- **Save Settings:** Writes all settings to config.ini, then reloads the active XML folder.

**XML Settings**

- **Anno 117 XML Files:** Folder list for extracted Anno 117 data. Add folders with **Browse...** and remove them with **Remove Selected**.
- **Anno 1800 XML Files:** Same, for Anno 1800 data.
- **Buff/Effect XML tags:** Edit the tag list used to detect linked buffs and effects. The default list is the union of the tags both games use. Use **Add Tag** and **Remove Selected Tag** to manage entries. Double-click an entry to rename it.
- Changes to the folder lists take effect immediately in all dropdowns; **Save Settings** writes them to config.ini permanently.

###### Gamefile Extraction (RDA)

The **Settings > General** tab can extract XML gamefiles directly from installed game archives.

- Configure the respective Anno game folder, then select **Extract Anno 117 gamefiles** or **Extract Anno 1800 gamefiles** and choose an output folder.
- Anno 117 requires maindata/config.rda; Anno 1800 searches the game folder for data\*.rda archives. The archives are processed newest first, so a patched file is never overwritten by an older one, and only the extracted data/config tree is kept.
- RdaConsole.exe must be placed in the application directory. If it is missing, the tool displays a download link.
- Extraction runs in a separate process. A progress window remains visible throughout the operation; for Anno 1800 it identifies the archive currently being processed.
- Afterwards, add the output folder to the matching list under **Settings > XML Settings**.

###### Export

The **EXPORT XML** button saves the selected asset into a new XML file. It performs a recursive export: detected buffs and effects are included based on the active Buff/Effect filter, which makes it useful for creating standalone mod snippets.

###### Update Check

On startup the tool compares its own version with the published version file on GitHub. If a newer release exists, a dialog with a link is shown. The check runs in the background and never delays or blocks startup if no network connection is available. The **GitHub** button in the toolbar opens the project page directly.

#### Deutsche Version

---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

##### 1. Einleitung

Der **Anno XML Viewer** ist ein spezialisiertes Werkzeug fuer Modder der _Anno_-Serie. Er ermoeglicht schnelles Durchsuchen, Anzeigen und Analysieren von Game-Assets aus assets.xml. Das Tool loest Text-IDs in lesbare Texte auf, zeigt Beziehungen zwischen Assets und hilft beim Pruefen von Buffs, Effekten, Templates und XML-Strukturen.

**Anno 117 und Anno 1800 werden parallel unterstuetzt.** Beide Spiele verwenden dieselben Dateinamen, ordnen ihre Inhalte aber unterschiedlich zu. Deshalb besitzt jeder Titel ein eigenes Datenprofil; Ordner, Watchlists und Regeln zur Textaufloesung werden pro Spiel getrennt gehalten.

##### 2. Unterstuetzte Spiele und Datenunterschiede

| Aspekt | Anno 117 | Anno 1800 |
| --- | --- | --- |
| Textschluessel in texts\_\*.xml | `<Text><LineId>` | `<Text><GUID>` |
| Verweis auf den Anzeigenamen | `Text/OasisId` | die eigene `Standard/GUID` des Assets |
| Inline-Anzeigetext | – | `LocaText/English/Text` |
| Zusaetzliche Datendatei | – | `properties.xml` |
| Technologiename | `Tech/VisibleTechName` | – |

Auswirkungen in der Oberflaeche:

- In Anno 1800 **ist** die GUID eines Assets sein Textschluessel; der Anzeigename wird direkt ueber die GUID nachgeschlagen, ohne Umweg.
- `LineID` ist in Anno 117 ein echter Textverweis, in Anno 1800 dagegen eine interne Nummer und wird dort nie aufgeloest.
- Reine Mengenangaben wie `<Amount>`, `<InactiveAmount>` und `<MaximumHitPoints>` verweisen auf gar nichts. Sie werden als Zahl angezeigt und nicht mehr gegen die Asset-Datenbank geprueft.
- Nur Tags, die ausdruecklich als Textverweis deklariert sind, werden in texts\_\*.xml nachgeschlagen; jede andere Zahl im Asset bleibt ein Wert.

**Spielerkennung:** Beim Laden eines Ordners wird zuerst geprueft, in welcher Spielliste er eingetragen ist. Ist er unbekannt, entscheidet der Inhalt – das verwendete Textschluessel-Element in texts\_\*.xml und das Vorhandensein von properties.xml.

##### 3. Erste Schritte

- **Datenordner waehlen:** Oeffne den Reiter **Settings**, wechsle zu **XML Settings** und fuege mit **Browse...** einen oder mehrere Ordner mit XML-Dateien hinzu. Die Ordner werden getrennt fuer **Anno 117 XML Files** und **Anno 1800 XML Files** verwaltet. Ein Ordner muss assets.xml enthalten; templates.xml und texts\_\*.xml werden fuer den vollen Funktionsumfang empfohlen.
- **Aktiven Ordner waehlen:** Ueber das XML-Pfad-Dropdown in der oberen Leiste kannst du zwischen gespeicherten XML-Ordnern wechseln. Die Eintraege sind nach Spiel gruppiert und mit einer hervorgehobenen Gruppenueberschrift versehen. Beim Wechsel werden die Daten neu geladen und die Watchlist des jeweiligen Spiels angezeigt.
- **Sprache:** Waehle die Anzeigesprache in der oberen Leiste. Die Standardsprache wird unter **Settings > General** festgelegt.
- **Theme:** Das Farbschema waehlst du unter **Settings > General > Appearance**. Aenderungen werden sofort uebernommen.
- **Ladevorgang:** Das Programm laedt die Daten im Hintergrund. Fortschritt, Statusmeldungen und das verwendete Spielprofil stehen im Reiter **Engine Log**.

##### 4. Hauptfunktionen

###### Asset Editor & Suche

- **Suchleiste:** Gib einen oder mehrere Begriffe ein, um Assets zu finden.
- Leerzeichen verwenden eine "UND"-Logik, zum Beispiel farm sheep.
- Ein Minus-Praefix schliesst Begriffe aus, zum Beispiel farm -module.
- **Suchtiefe:** Standardmaessig durchsucht das Tool GUID, Anzeigename und Template. Deaktiviere **Search only GUID Text**, um den gesamten XML-Textinhalt der Assets zu durchsuchen. Das ist langsamer, aber gruendlicher.
- **Template-Filter:** Mit **Template Filter...** kannst du Template-Kategorien auswaehlen oder abwaehlen. Das Popup enthaelt eine Suche sowie **Select All** und **Deselect All**.
- **Asset-Tabelle:** Zeigt GUID, Anzeigename und Template. Die Auswahl einer Zeile aktualisiert die Analyse-Fenster.

###### Watchlist

- Das **WATCHLIST**-Fenster speichert ausgewaehlte Assets per GUID fuer schnellen Zugriff.
- **Anno 117 und Anno 1800 haben getrennte Watchlists.** Die Kopfzeile zeigt an, welche Liste gerade sichtbar ist; sie folgt dem Spiel des geladenen XML-Ordners.
- Mit **+** wird das aktuell ausgewaehlte Asset hinzugefuegt.
- Mit **-** wird der ausgewaehlte Watchlist-Eintrag entfernt.
- Die Watchlist wird pro Spiel in config.ini gespeichert und beim Neustart wiederhergestellt. Eine Watchlist aus einer aelteren Version wird dem Spiel des damals aktiven Ordners zugeordnet.

###### Analyse-Fenster

- **Property Tree:** Zeigt die \<Values\>-Sektion des ausgewaehlten Assets als Baumstruktur. GUIDs und Text-IDs werden soweit moeglich in Namen aufgeloest; reine Mengenangaben bleiben unveraendert.
- **XML View:** Zeigt den rohen, formatierten XML-Code des ausgewaehlten Assets.
- **Buffs / Effects:** Zeigt verknuepfte Assets, die ueber konfigurierte Buff-/Effect-Tags referenziert werden. Mit **Filter...** steuerst du, welche Kategorien angezeigt werden. Welches Unterelement die referenzierte GUID enthaelt, ist pro Spiel definiert.
- **References:** Zeigt die Rueckwaertssuche: Assets, die auf die aktuell ausgewaehlte GUID verweisen.

###### GUID Compare

Der Reiter **GUID Compare** stellt ein einzelnes Asset aus zwei Datenordnern nebeneinander dar. So laesst sich schnell erkennen, was ein Patch veraendert hat. Fuer jeden Ordner werden eigene \*.xml-Dateien benoetigt.

- **GUID waehlen:** Direkt eingeben oder einen Eintrag aus dem **Watchlist**-Dropdown auswaehlen.
- **Ordner waehlen:** Lege den Ordner fuer das linke und das rechte Fenster fest. Beide Dropdowns enthalten dieselben Ordner wie die obere Leiste, nach Spiel gruppiert.
- **Ausgerichteter Vergleich:** Beide Fenster zeigen immer gleich viele Zeilen. Zeilen, die nur auf einer Seite existieren, werden auf der anderen Seite aufgefuellt, damit zusammengehoerende Inhalte auf derselben Hoehe bleiben.
- **Zeilennummern und Markierungen:** Die Randspalte zeigt die urspruengliche Zeilennummer sowie eine Markierung: + fuer Zeilen, die nur auf dieser Seite vorhanden sind, - fuer entfernte Zeilen und ~ fuer geaenderte Zeilen.
- **Wort-Hervorhebung:** Innerhalb einer geaenderten Zeile werden nur die tatsaechlich abweichenden Woerter hervorgehoben.
- **Synchrones Scrollen:** Beide Fenster scrollen gemeinsam, horizontal und vertikal.
- **Navigation:** Mit **Prev diff** und **Next diff** springst du von einem Aenderungsblock zum naechsten. Aufeinanderfolgende geaenderte Zeilen zaehlen als ein Block.
- **Ignore whitespace:** Standardmaessig aktiv. Zeilen werden ohne fuehrende und abschliessende Leerzeichen verglichen, sodass reine Einrueckungsaenderungen nicht als Unterschied gelten.
- **Zusammenfassung:** Der Statustext neben der Werkzeugleiste zeigt, wie viele Zeilen geaendert wurden und wie viele nur auf einer Seite vorhanden sind.
- **Theme-abhaengige Farben:** Die Diff-Farben werden aus dem Editor-Hintergrund berechnet, sodass hinzugefuegte, entfernte und geaenderte Zeilen sowohl auf dunklen als auch auf hellen Themes lesbar bleiben.
- Die Suche liest die XML-Dateien fortlaufend ein, statt sie vollstaendig zu laden. Dadurch lassen sich auch grosse assets.xml-Dateien ohne hohen Speicherbedarf durchsuchen. Die Quelldatei eines Treffers wird als Kommentar in der ersten Zeile ergaenzt. Ein neuer Vergleich bricht noch laufende Suchen ab.

###### Templates

Der Reiter **Templates** listet Templates aus templates.xml.

- Mit dem Suchfeld filterst du die Template-Liste.
- Die Auswahl eines Templates zeigt eine formatierte XML-Vorschau.

###### Structure Library

Der Reiter **Structure Library** katalogisiert einzigartige XML-Pfade aus den geladenen Daten.

- Mit dem Suchfeld filterst du die Pfade.
- Die Auswahl eines Pfades zeigt eine Struktur-Vorschau und bekannte Werte dieses Pfades im Datensatz.

###### Engine Log

Der Reiter **Engine Log** zeigt Ladefortschritt, Parser-Meldungen, Warnungen und Fehler. Zusaetzlich wird protokolliert, mit welchem Spielprofil ein Ordner geladen wurde, es wird gewarnt, wenn eine texts\_\*.xml keine Schluessel des erwarteten Typs enthaelt (ein Hinweis darauf, dass der Ordner in der falschen Spielliste steht), beim Start wird der Theme-Status ausgegeben und es werden XML-Dateien aufgefuehrt, die wegen eines Parser-Fehlers uebersprungen wurden.

###### Settings

Der Reiter **Settings** verwaltet die Anwendungskonfiguration und ist in zwei Unterreiter aufgeteilt.

**General**

- **Default Language:** Legt die Sprache fest, die nach dem Laden standardmaessig verwendet wird.
- **Appearance:** Waehlt das Theme der Anwendung. **Anno Dark (built-in)** steht immer zur Verfuegung. Ist das optionale Paket **qt-themes** installiert, erscheinen zusaetzliche Farbschemata wie Modern Dark/Light, One Dark Two, Atom One, Monokai, Dracula, Nord, Blender, GitHub und Catppuccin. Die Auswahl wird sofort angewendet und beim Neustart wiederhergestellt. Kann qt-themes nicht genutzt werden, wird der Grund neben der Auswahl angezeigt.
- **Game Folders:** Legt die Installationsordner von Anno 117 und Anno 1800 fest, die fuer die Gamefile-Extraktion verwendet werden.
- **Save Settings:** Speichert alle Einstellungen in config.ini und laedt den aktiven XML-Ordner neu.

**XML Settings**

- **Anno 117 XML Files:** Ordnerliste fuer extrahierte Anno-117-Daten. Ordner werden mit **Browse...** hinzugefuegt und mit **Remove Selected** entfernt.
- **Anno 1800 XML Files:** Ebenso fuer Anno-1800-Daten.
- **Buff/Effect XML tags:** Bearbeitet die Tag-Liste, mit der verknuepfte Buffs und Effekte erkannt werden. Die Standardliste ist die Vereinigung der Tags beider Spiele. Eintraege werden mit **Add Tag** und **Remove Selected Tag** verwaltet. Ein Doppelklick benennt einen Eintrag um.
- Aenderungen an den Ordnerlisten wirken sofort in allen Dropdowns; **Save Settings** schreibt sie dauerhaft in die config.ini.

###### Gamefile-Extraktion (RDA)

Im Reiter **Settings > General** lassen sich XML-Gamefiles direkt aus den installierten Spielarchiven extrahieren.

- Konfiguriere den jeweiligen Anno-Spielordner, waehle **Extract Anno 117 gamefiles** oder **Extract Anno 1800 gamefiles** und anschliessend einen Ausgabeordner.
- Anno 117 benoetigt maindata/config.rda; bei Anno 1800 wird der Spielordner nach data\*.rda-Archiven durchsucht. Die Archive werden vom neuesten zum aeltesten verarbeitet, damit gepatchte Dateien nicht von aelteren ueberschrieben werden; erhalten bleibt nur der extrahierte data/config-Baum.
- RdaConsole.exe muss im Anwendungsverzeichnis liegen. Fehlt die Datei, zeigt das Tool einen Download-Link an.
- Die Extraktion laeuft in einem separaten Prozess. Ein Fortschrittsfenster bleibt waehrend des Vorgangs sichtbar und zeigt bei Anno 1800 das gerade bearbeitete Archiv an.
- Fuege den Ausgabeordner anschliessend unter **Settings > XML Settings** der passenden Liste hinzu.

###### Export

Der Button **EXPORT XML** speichert das ausgewaehlte Asset in eine neue XML-Datei. Dabei erfolgt ein rekursiver Export: Erkannte Buffs und Effekte werden basierend auf dem aktiven Buff-/Effect-Filter mit exportiert. Das ist nuetzlich zum Erstellen eigenstaendiger Mod-Snippets.

###### Update-Pruefung

Beim Start vergleicht das Tool seine eigene Version mit der auf GitHub veroeffentlichten Versionsdatei. Gibt es eine neuere Version, erscheint ein Hinweisfenster mit Link. Die Pruefung laeuft im Hintergrund und verzoegert den Start nicht, wenn keine Netzwerkverbindung besteht. Der Button **GitHub** in der Werkzeugleiste oeffnet die Projektseite direkt.

##### Technical Details / Technische Details

**Requirements / Anforderungen:**

- Python 3.13+ if running from source
- PyQt6
- qt-themes (optional, for additional themes: pip install qt-themes)
- RdaConsole.exe in the application directory (only for gamefile extraction)

**Project structure / Projektstruktur:**

| File / Datei | Purpose / Zweck |
| --- | --- |
| `Anno_XML_Viewer.py` | Main window, tabs, UI logic / Hauptfenster, Reiter, UI-Logik |
| `anno_game.py` | Base class + registry of the game profiles / Basisklasse und Registry der Spielprofile |
| `anno117.py` | Anno 117 data rules / Anno-117-Datenregeln |
| `anno1800.py` | Anno 1800 data rules / Anno-1800-Datenregeln |
| `anno_loader.py` | Background parsing of assets, templates, texts / Hintergrund-Parsing |
| `guid_compare.py` | Streaming GUID lookup / Streaming-GUID-Suche |
| `guid_diff_view.py` | Side-by-side diff panes / Diff-Ansicht |
| `theme_manager.py` | Themes and color helpers / Themes und Farbhilfen |
| `rda_extractor.py` | RDA archive extraction / RDA-Extraktion |
| `build_onefile.py` | PyInstaller one-file build / PyInstaller-Onefile-Build |

Adding another Anno title only requires a new profile module derived from `AnnoGame`; the UI itself does not need to be changed. / Ein weiterer Anno-Titel benoetigt lediglich ein neues Profilmodul auf Basis von `AnnoGame`; die Oberflaeche selbst muss nicht angepasst werden.

**Build:** `python build_onefile.py` creates a windowed one-file executable named after version.txt. The script explicitly bundles the lazily imported game profiles and the qt-themes data files, and excludes other Qt bindings so PyQt6 stays the only one in the build. / `python build_onefile.py` erzeugt eine Onefile-EXE, benannt nach version.txt. Das Skript bindet die verzoegert importierten Spielprofile sowie die qt-themes-Dateien explizit ein und schliesst andere Qt-Bindings aus.

**Configuration / Konfiguration:** Settings are stored in config.ini in the application directory. This includes the XML paths per game, the active/default language, the selected theme, the buff/effect tags, the configured game folders and the watchlist GUIDs per game. Folder lists and watchlists from earlier versions are migrated automatically on first start.

**Credits:** Created by gz2k2. This is a fan project and not affiliated with Ubisoft.
