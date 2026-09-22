## Anno XML Viewer Documentation

### English Version

---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

#### 1. Introduction
  
The **Anno XML Viewer** is a specialized tool for modders of the _Anno_ series. It allows high-performance browsing, searching, and analysis of game assets from assets.xml. The tool resolves text IDs into readable strings, maps relationships between assets, and helps inspect linked buffs, effects, templates, and XML structures.

#### 2. Getting Started
- **Select Data Folder:** Open the **Settings** tab, switch to **XML Settings**, and use **Browse...** to add one or more folders containing your XML files. Folders are managed separately for **Anno 117 XML Files** and **Anno 1800 XML Files**. A folder must contain assets.xml; templates.xml and texts\_\*.xml are recommended for full functionality.
- **Choose Active Folder:** Use the XML path dropdown in the top bar to switch between saved XML folders. Entries are grouped by game. Switching the active folder reloads the data.
- **Language:** Select the display language in the top bar. Set the default language in **Settings \> General**.
- **Theme:** Choose a color scheme under **Settings \> General \> Appearance**. Changes apply immediately.
- **Loading:** The tool parses the data in the background. Check the **Engine Log** tab for progress and status messages.

#### 3. Core Features

##### Asset Editor & Search
- **Search Bar:** Enter one or more terms to find assets.
- Spaces use "AND" logic, for example farm sheep.
- A minus prefix excludes terms, for example farm -module.
- **Search Depth:** By default, the search checks GUID, display name, and template. Disable **Search only GUID Text** to search all XML text content inside assets. This is slower but more thorough.
- **Template Filter:** Click **Template Filter...** to select or deselect template categories. The popup includes a template search field plus **Select All** and **Deselect All** buttons.
- **Asset Table:** Shows GUID, display name, and template. Selecting a row updates the analysis panes.

##### Watchlist
- The **WATCHLIST** panel stores selected assets by GUID for quick access.
- Use **\+** to add the currently selected asset.
- Use **-** to remove the selected watchlist entry.
- Watchlist entries are saved in config.ini and restored on restart.

##### Analysis Panes
- **Property Tree:** Displays the \<Values\> section of the selected asset in a readable tree. GUIDs and text IDs are resolved into names where possible.
- **XML View:** Shows the raw, formatted XML of the selected asset.
- **Buffs / Effects:** Shows linked assets referenced through configured buff/effect tags. Use the **Filter...** button to select which categories are shown.
- **References:** Shows reverse-search results: assets that reference the currently selected GUID.

##### GUID Compare
  
The **GUID Compare** tab shows a single asset from two data folders side by side, which makes it easy to see what a patch changed. Each folder requires its own set of \*.xml files.
- **Select a GUID:** Enter it directly or pick an entry from the **Watchlist** dropdown.
- **Select Folders:** Choose the folder for the left and right pane. Both dropdowns list the same folders as the top bar, grouped by game.
- **Aligned Diff:** Both panes always show the same number of rows. Lines that exist only on one side are padded on the other so matching content stays on the same row.
- **Line Numbers and Markers:** The gutter shows the original line number of each line plus a marker: `+` for lines that exist only on this side, `-` for removed lines, and `~` for modified lines.
- **Word Highlighting:** Within a modified line, only the words that actually differ are highlighted.
- **Synchronized Scrolling:** Both panes scroll together, horizontally and vertically.
- **Navigation:** **Prev diff** and **Next diff** jump from one block of changes to the next. Consecutive changed lines count as a single block.
- **Ignore whitespace:** Enabled by default. Lines are compared without leading and trailing whitespace so pure indentation changes are not reported as differences.
- **Summary:** The status text next to the toolbar shows how many lines were changed and how many exist on only one side.
- The lookup streams the XML files instead of loading them completely, so even large assets.xml files can be searched without high memory usage. The source file of a match is added as a comment in the first line.

##### Templates
  
The **Templates** tab lists templates from templates.xml.
- Use the search field to filter templates.
- Selecting a template shows its formatted XML preview.

##### Structure Library
  
The **Structure Library** tab catalogs unique XML tag paths found in the loaded data.
- Use the search field to filter paths.
- Selecting a path shows a structural preview and known values for that path across the dataset.

##### Engine Log
  
The **Engine Log** tab displays background loading progress, parser messages, warnings, and errors. It also reports the theme status at startup and lists XML files that were skipped because they could not be parsed.

##### Settings
  
The **Settings** tab stores application configuration and is divided into two sub-tabs.

**General**
- **Default Language:** Choose the language selected by default after loading.
- **Appearance:** Select the application theme. **Anno Dark (built-in)** is always available. If the optional package **qt-themes** is installed, additional color schemes such as Modern Dark/Light, One Dark Two, Atom One, Monokai, Dracula, Nord, Blender, GitHub, and Catppuccin are listed as well. The selection is applied immediately and restored on restart.
- **Game Folders:** Configure the Anno 117 and Anno 1800 installation folders used for gamefile extraction.
- **Save Settings:** Writes all settings to config.ini, then reloads the active XML folder.

**XML Settings**
- **Anno 117 XML Files:** Folder list for extracted Anno 117 data. Add folders with **Browse...** and remove them with **Remove Selected**.
- **Anno 1800 XML Files:** Same, for Anno 1800 data.
- **Buff/Effect XML tags:** Edit the tag list used to detect linked buffs and effects. Use **Add Tag** and **Remove Selected Tag** to manage entries. Double-click an entry to rename it.
- Changes to the folder lists take effect immediately in all dropdowns; **Save Settings** writes them to config.ini permanently.

##### Gamefile Extraction (RDA)
  
The **Settings \> General** tab can extract XML gamefiles directly from installed game archives.
- Configure the respective Anno game folder, then select **Extract Anno 117 gamefiles** or **Extract Anno 1800 gamefiles** and choose an output folder.
- Anno 117 requires maindata/config.rda; Anno 1800 searches the game folder for data\*.rda archives.
- RdaConsole.exe must be placed in the application directory. If it is missing, the tool displays a download link.
- Extraction runs in a separate process. A progress window remains visible throughout the operation; for Anno 1800 it identifies the archive currently being processed.
- Afterwards, add the output folder to the matching list under **Settings \> XML Settings**.

##### Export
  
The **EXPORT XML** button saves the selected asset into a new XML file. It performs a recursive export: detected buffs and effects are included based on the active Buff/Effect filter, which makes it useful for creating standalone mod snippets.

### Deutsche Version

---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

#### 1. Einleitung
  
Der **Anno XML Viewer** ist ein spezialisiertes Werkzeug fuer Modder der _Anno_-Serie. Er ermoeglicht schnelles Durchsuchen, Anzeigen und Analysieren von Game-Assets aus assets.xml. Das Tool loest Text-IDs in lesbare Texte auf, zeigt Beziehungen zwischen Assets und hilft beim Pruefen von Buffs, Effekten, Templates und XML-Strukturen.

#### 2. Erste Schritte
- **Datenordner waehlen:** Oeffne den Reiter **Settings**, wechsle zu **XML Settings** und fuege mit **Browse...** einen oder mehrere Ordner mit XML-Dateien hinzu. Die Ordner werden getrennt fuer **Anno 117 XML Files** und **Anno 1800 XML Files** verwaltet. Ein Ordner muss assets.xml enthalten; templates.xml und texts\_\*.xml werden fuer den vollen Funktionsumfang empfohlen.
- **Aktiven Ordner waehlen:** Ueber das XML-Pfad-Dropdown in der oberen Leiste kannst du zwischen gespeicherten XML-Ordnern wechseln. Die Eintraege sind nach Spiel gruppiert. Beim Wechsel werden die Daten neu geladen.
- **Sprache:** Waehle die Anzeigesprache in der oberen Leiste. Die Standardsprache wird unter **Settings \> General** festgelegt.
- **Theme:** Das Farbschema waehlst du unter **Settings \> General \> Appearance**. Aenderungen werden sofort uebernommen.
- **Ladevorgang:** Das Programm laedt die Daten im Hintergrund. Fortschritt und Statusmeldungen stehen im Reiter **Engine Log**.

#### 3. Hauptfunktionen

##### Asset Editor & Suche
- **Suchleiste:** Gib einen oder mehrere Begriffe ein, um Assets zu finden.
- Leerzeichen verwenden eine "UND"-Logik, zum Beispiel farm sheep.
- Ein Minus-Praefix schliesst Begriffe aus, zum Beispiel farm -module.
- **Suchtiefe:** Standardmaessig durchsucht das Tool GUID, Anzeigename und Template. Deaktiviere **Search only GUID Text**, um den gesamten XML-Textinhalt der Assets zu durchsuchen. Das ist langsamer, aber gruendlicher.
- **Template-Filter:** Mit **Template Filter...** kannst du Template-Kategorien auswaehlen oder abwaehlen. Das Popup enthaelt eine Suche sowie **Select All** und **Deselect All**.
- **Asset-Tabelle:** Zeigt GUID, Anzeigename und Template. Die Auswahl einer Zeile aktualisiert die Analyse-Fenster.

##### Watchlist
- Das **WATCHLIST**-Fenster speichert ausgewaehlte Assets per GUID fuer schnellen Zugriff.
- Mit **\+** wird das aktuell ausgewaehlte Asset hinzugefuegt.
- Mit **-** wird der ausgewaehlte Watchlist-Eintrag entfernt.
- Die Watchlist wird in config.ini gespeichert und beim Neustart wiederhergestellt.

##### Analyse-Fenster
- **Property Tree:** Zeigt die \<Values\>-Sektion des ausgewaehlten Assets als Baumstruktur. GUIDs und Text-IDs werden soweit moeglich in Namen aufgeloest.
- **XML View:** Zeigt den rohen, formatierten XML-Code des ausgewaehlten Assets.
- **Buffs / Effects:** Zeigt verknuepfte Assets, die ueber konfigurierte Buff-/Effect-Tags referenziert werden. Mit **Filter...** steuerst du, welche Kategorien angezeigt werden.
- **References:** Zeigt die Rueckwaertssuche: Assets, die auf die aktuell ausgewaehlte GUID verweisen.

##### GUID Compare
  
Der Reiter **GUID Compare** stellt ein einzelnes Asset aus zwei Datenordnern nebeneinander dar. So laesst sich schnell erkennen, was ein Patch veraendert hat. Fuer jeden Ordner werden eigene \*.xml-Dateien benoetigt.
- **GUID waehlen:** Direkt eingeben oder einen Eintrag aus dem **Watchlist**-Dropdown auswaehlen.
- **Ordner waehlen:** Lege den Ordner fuer das linke und das rechte Fenster fest. Beide Dropdowns enthalten dieselben Ordner wie die obere Leiste, nach Spiel gruppiert.
- **Ausgerichteter Vergleich:** Beide Fenster zeigen immer gleich viele Zeilen. Zeilen, die nur auf einer Seite existieren, werden auf der anderen Seite aufgefuellt, damit zusammengehoerende Inhalte auf derselben Hoehe bleiben.
- **Zeilennummern und Markierungen:** Die Randspalte zeigt die urspruengliche Zeilennummer sowie eine Markierung: `+` fuer Zeilen, die nur auf dieser Seite vorhanden sind, `-` fuer entfernte Zeilen und `~` fuer geaenderte Zeilen.
- **Wort-Hervorhebung:** Innerhalb einer geaenderten Zeile werden nur die tatsaechlich abweichenden Woerter hervorgehoben.
- **Synchrones Scrollen:** Beide Fenster scrollen gemeinsam, horizontal und vertikal.
- **Navigation:** Mit **Prev diff** und **Next diff** springst du von einem Aenderungsblock zum naechsten. Aufeinanderfolgende geaenderte Zeilen zaehlen als ein Block.
- **Ignore whitespace:** Standardmaessig aktiv. Zeilen werden ohne fuehrende und abschliessende Leerzeichen verglichen, sodass reine Einrueckungsaenderungen nicht als Unterschied gelten.
- **Zusammenfassung:** Der Statustext neben der Werkzeugleiste zeigt, wie viele Zeilen geaendert wurden und wie viele nur auf einer Seite vorhanden sind.
- Die Suche liest die XML-Dateien fortlaufend ein, statt sie vollstaendig zu laden. Dadurch lassen sich auch grosse assets.xml-Dateien ohne hohen Speicherbedarf durchsuchen. Die Quelldatei eines Treffers wird als Kommentar in der ersten Zeile ergaenzt.

##### Templates
  
Der Reiter **Templates** listet Templates aus templates.xml.
- Mit dem Suchfeld filterst du die Template-Liste.
- Die Auswahl eines Templates zeigt eine formatierte XML-Vorschau.

##### Structure Library
  
Der Reiter **Structure Library** katalogisiert einzigartige XML-Pfade aus den geladenen Daten.
- Mit dem Suchfeld filterst du die Pfade.
- Die Auswahl eines Pfades zeigt eine Struktur-Vorschau und bekannte Werte dieses Pfades im Datensatz.

##### Engine Log
  
Der Reiter **Engine Log** zeigt Ladefortschritt, Parser-Meldungen, Warnungen und Fehler. Zusaetzlich wird beim Start der Theme-Status protokolliert und es werden XML-Dateien aufgefuehrt, die wegen eines Parser-Fehlers uebersprungen wurden.

##### Settings
  
Der Reiter **Settings** verwaltet die Anwendungskonfiguration und ist in zwei Unterreiter aufgeteilt.

**General**
- **Default Language:** Legt die Sprache fest, die nach dem Laden standardmaessig verwendet wird.
- **Appearance:** Waehlt das Theme der Anwendung. **Anno Dark (built-in)** steht immer zur Verfuegung. Ist das optionale Paket **qt-themes** installiert, erscheinen zusaetzliche Farbschemata wie Modern Dark/Light, One Dark Two, Atom One, Monokai, Dracula, Nord, Blender, GitHub und Catppuccin. Die Auswahl wird sofort angewendet und beim Neustart wiederhergestellt.
- **Game Folders:** Legt die Installationsordner von Anno 117 und Anno 1800 fest, die fuer die Gamefile-Extraktion verwendet werden.
- **Save Settings:** Speichert alle Einstellungen in config.ini und laedt den aktiven XML-Ordner neu.

**XML Settings**
- **Anno 117 XML Files:** Ordnerliste fuer extrahierte Anno-117-Daten. Ordner werden mit **Browse...** hinzugefuegt und mit **Remove Selected** entfernt.
- **Anno 1800 XML Files:** Ebenso fuer Anno-1800-Daten.
- **Buff/Effect XML tags:** Bearbeitet die Tag-Liste, mit der verknuepfte Buffs und Effekte erkannt werden. Eintraege werden mit **Add Tag** und **Remove Selected Tag** verwaltet. Ein Doppelklick benennt einen Eintrag um.
- Aenderungen an den Ordnerlisten wirken sofort in allen Dropdowns; **Save Settings** schreibt sie dauerhaft in die config.ini.

##### Gamefile-Extraktion (RDA)
  
Im Reiter **Settings \> General** lassen sich XML-Gamefiles direkt aus den installierten Spielarchiven extrahieren.
- Konfiguriere den jeweiligen Anno-Spielordner, waehle **Extract Anno 117 gamefiles** oder **Extract Anno 1800 gamefiles** und anschliessend einen Ausgabeordner.
- Anno 117 benoetigt maindata/config.rda; bei Anno 1800 wird der Spielordner nach data\*.rda-Archiven durchsucht.
- RdaConsole.exe muss im Anwendungsverzeichnis liegen. Fehlt die Datei, zeigt das Tool einen Download-Link an.
- Die Extraktion laeuft in einem separaten Prozess. Ein Fortschrittsfenster bleibt waehrend des Vorgangs sichtbar und zeigt bei Anno 1800 das gerade bearbeitete Archiv an.
- Fuege den Ausgabeordner anschliessend unter **Settings \> XML Settings** der passenden Liste hinzu.

##### Export
  
Der Button **EXPORT XML** speichert das ausgewaehlte Asset in eine neue XML-Datei. Dabei erfolgt ein rekursiver Export: Erkannte Buffs und Effekte werden basierend auf dem aktiven Buff-/Effect-Filter mit exportiert. Das ist nuetzlich zum Erstellen eigenstaendiger Mod-Snippets.

#### Technical Details / Technische Details
  
**Requirements / Anforderungen:**
- Python 3.13+ if running from source
- PyQt6
- qt-themes (optional, for additional themes: pip install qt-themes)  
**Configuration / Konfiguration:**Settings are stored in config.ini in the application directory. This includes XML paths per game, active/default language, selected theme, buff/effect tags, and watchlist GUIDs. Folder lists from earlier versions are migrated automatically on first start.  
**Credits:**Created by gz2k2. This is a fan project and not affiliated with Ubisoft.
