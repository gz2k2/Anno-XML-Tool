### [Anno XML Viewer Screenshot](screenshot.jpg)

### 📖 [**Detailed Documentation / Ausführliche Dokumentation**](Documentation.md)

## Anno XML Viewer

### English Version (Deutsche Version unterhalb)

**Anno XML Viewer** is a specialized utility tool designed for modders and data analysts of the _Anno_ game series. It simplifies the process of navigating, analyzing, and exploring complex game data by providing a clean, searchable interface for XML assets. **Anno 117 and Anno 1800 are supported side by side**, each with its own data rules, folder list and watchlist.

#### Key Features

- **Two Games, Two Rule Sets:** Anno 117 and Anno 1800 store their data differently. Each title has its own profile (`anno117.py` / `anno1800.py`), so text IDs, display names and references are resolved with the rules of the game the folder actually belongs to.
- **Automatic Game Detection:** A data folder is identified by its content (text key element, presence of `properties.xml`), so a folder added to the wrong list is still parsed correctly.
- **Advanced Search:** Instantly locate any asset by searching for its **Name** or **GUID**. Spaces combine terms with AND, commas with OR, a `-` prefix excludes and `*` is a wildcard. XML snippets such as `<Name>DeliveryTime</Name>` search the raw asset XML.
- **Search Highlighting:** Search terms are highlighted in color in the asset list, the Texts tab, the Templates list and the Structure Library.
- **Comprehensive Asset Insights:** Selecting an asset automatically reveals all its associated **references**, **effects**, and **buffs** in a structured view.
- **Correct Text Resolution:** Only tags that genuinely reference a `texts_*.xml` entry are resolved. Plain quantities such as `<Amount>`, `<MaximumHitPoints>` or the Anno 1800 `<LineID>` are shown as numbers instead of being mistaken for an asset or a translation.
- **Smart Template Filtering:** Narrow down your search by filtering assets to display only those belonging to a specific template.
- **Per-Game Watchlist:** Anno 117 and Anno 1800 keep separate watchlists. The panel follows the game of the loaded folder.
- **Version Comparison:** Compare a single asset across two game versions side by side, with aligned lines, line numbers, change markers, word-level highlighting and synchronized scrolling. Each side has its own folder, GUID field and watchlist dropdown, so two different assets can be compared as well.
- **Texts Browser:** Browse the content of `texts_*.xml` for the selected language, search by exact GUID or by combined text terms (`mackerel -coast`) and see the XML of each entry.
- **Structure Library Tree:** All XML tag paths of the loaded data in a collapsible tree, with value previews per path.
- **Data Export:** Easily export complete XML data—including all linked effects and buffs (if applicable)—for external use or modding. Also available via right-click.
- **Gamefile Extraction:** Extract XML gamefiles from Anno 117 and Anno 1800 RDA archives directly from the Settings tab. A progress window keeps the interface responsive while extraction runs in a separate process.
- **Themes:** Choose between the built-in dark theme and additional color schemes provided by the optional [qt-themes](https://pypi.org/project/qt-themes/) package. Diff colors, XML syntax colors and combo box headers follow the active theme.
- **Adjustable Font Sizes:** Separate font sizes for result lists and XML views under Settings > General > Text.
- **Update Check:** On startup the tool compares its version against the published one and points to the GitHub release if a newer version exists.

#### Project Description

**Anno XML Viewer** is a lightweight, intuitive tool designed to streamline data exploration for _Anno_ modders. Instead of digging through massive, disorganized XML files, this tool allows you to search for assets instantly using their **Name** or **GUID**. Once an asset is selected, the program dynamically maps out its entire ecosystem, displaying all connected **references**, **buffs**, and **effects** at a glance. With built-in **template filters**, you can isolate specific categories of assets effortlessly. The **GUID Compare** tab shows what changed between two game versions without leaving the application. Need to use the data elsewhere? The application features a comprehensive **export function** that packs the full XML data, along with its effects and buffs, into a clean file ready for your next modding project.

#### Feature Overview

| Feature | Description |
| --- | --- |
| **Supported Games** | Anno 117 and Anno 1800, each with its own XML rules |
| **Search Modes** | By Asset Name or unique GUID, AND/OR/exclude, wildcards and XML snippets |
| **Relational Views** | Automatic display of references, effects, and buffs |
| **Filtering** | Filter by specific asset templates |
| **Watchlist** | Separate lists for Anno 117 and Anno 1800 |
| **GUID Compare** | Side-by-side diff of one asset across two game versions, or of two different assets |
| **Texts** | Search texts_\*.xml by exact GUID or text terms, with XML view |
| **Structure Library** | Collapsible tree of all XML tag paths with value previews |
| **Export** | Full XML dump including active buffs/effects |
| **Gamefile Extraction** | Extract Anno 117 / Anno 1800 XML gamefiles from RDA archives with progress feedback |
| **Themes** | Built-in dark theme plus optional qt-themes color schemes |
| **Font Sizes** | Separate font sizes for result lists and XML views |

#### Project Structure

| File | Purpose |
| --- | --- |
| `Anno_XML_Viewer.py` | Main window, tabs and all UI logic |
| `anno_game.py` | Base class and registry describing how a title stores its XML data |
| `anno117.py` | Anno 117 data rules (`LineId` text keys, `Text/OasisId` display names) |
| `anno1800.py` | Anno 1800 data rules (`GUID` text keys, inline `LocaText`, `properties.xml`) |
| `anno_value_only_tags.py` | Value-only tags (plain numbers) shared by both games |
| `anno_buff_tags.py` | Default buff/effect tags shared by both games |
| `anno_loader.py` | Background loader for assets, templates and texts |
| `guid_compare.py` | Background GUID lookup that streams large XML files |
| `guid_diff_view.py` | Side-by-side diff panes with gutter, markers and synced scrolling |
| `theme_manager.py` | Built-in theme, qt-themes integration and color helpers |
| `rda_extractor.py` | RdaConsole based extraction of Anno 117 / Anno 1800 archives |
| `build_onefile.py` | PyInstaller one-file build (bundles the qt-themes data files) |

### Support

---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

_Note: This is a fan project and is not affiliated with Ubisoft._

### Deutsche Version

**Anno XML Viewer** ist ein spezialisiertes Utility-Tool, das für Modder und Datenanalysten der _Anno_-Spieleserie entwickelt wurde. Es vereinfacht das Navigieren, Analysieren und Exportieren komplexer Spieldaten, indem es eine übersichtliche und durchsuchbare Benutzeroberfläche für XML-Assets bereitstellt. **Anno 117 und Anno 1800 werden parallel unterstützt** – jeweils mit eigenen Datenregeln, eigener Ordnerliste und eigener Watchlist.

#### Hauptfunktionen

- **Zwei Spiele, zwei Regelsätze:** Anno 117 und Anno 1800 legen ihre Daten unterschiedlich ab. Jeder Titel besitzt ein eigenes Profil (`anno117.py` / `anno1800.py`), sodass Text-IDs, Anzeigenamen und Referenzen nach den Regeln des tatsächlich geladenen Spiels aufgelöst werden.
- **Automatische Spielerkennung:** Ein Datenordner wird anhand seines Inhalts erkannt (Text-Schlüsselelement, Vorhandensein von `properties.xml`). Ein falsch einsortierter Ordner wird dadurch trotzdem korrekt gelesen.
- **Erweiterte Suche:** Finden Sie jedes Asset im Handumdrehen durch die Suche nach dem **Namen** oder der **GUID**. Leerzeichen verknüpfen mit UND, Kommas mit ODER, ein `-`-Präfix schließt aus und `*` ist ein Platzhalter. XML-Snippets wie `<Name>DeliveryTime</Name>` durchsuchen das rohe Asset-XML.
- **Treffer-Markierung:** Suchbegriffe werden in der Asset-Liste, im Reiter Texts, in der Templates-Liste und in der Structure Library farbig markiert.
- **Umfassende Asset-Einblicke:** Bei Auswahl eines Assets werden automatisch alle damit verknüpften **Referenzen (References)**, **Effekte (Effects)** und **Buffs** in einer strukturierten Ansicht angezeigt.
- **Korrekte Textauflösung:** Nur Tags, die wirklich auf einen Eintrag in `texts_*.xml` verweisen, werden aufgelöst. Reine Mengenangaben wie `<Amount>`, `<MaximumHitPoints>` oder das Anno-1800-`<LineID>` bleiben Zahlen und werden nicht mehr als Asset oder Übersetzung fehlgedeutet.
- **Intelligente Template-Filterung:** Grenzen Sie Ihre Suche präzise ein, indem Sie über Filter festlegen, dass nur Assets eines bestimmten Templates angezeigt werden.
- **Watchlist pro Spiel:** Anno 117 und Anno 1800 haben getrennte Watchlists. Die Anzeige folgt dem Spiel des geladenen Ordners.
- **Versionsvergleich:** Vergleichen Sie ein einzelnes Asset zwischen zwei Spielversionen nebeneinander – mit ausgerichteten Zeilen, Zeilennummern, Änderungsmarkierungen, Wort-Hervorhebung und synchronem Scrollen. Jede Seite hat einen eigenen Ordner, ein eigenes GUID-Feld und ein eigenes Watchlist-Dropdown, sodass sich auch zwei verschiedene Assets vergleichen lassen.
- **Texte-Browser:** Durchsuchen Sie den Inhalt der `texts_*.xml` der gewählten Sprache – exakt nach GUID oder mit kombinierten Textbegriffen (`makrele -küste`) – und sehen Sie das XML jedes Eintrags.
- **Structure Library als Baum:** Alle XML-Pfade der geladenen Daten in einem auf- und zuklappbaren Baum, mit Werte-Vorschau pro Pfad.
- **Datenexport:** Exportieren Sie mühelos die vollständigen XML-Daten – einschließlich aller verknüpften Effekte und Buffs (falls vorhanden) – für die externe Weiterverwendung oder das Modding. Auch per Rechtsklick verfügbar.
- **Gamefile-Extraktion:** Extrahieren Sie XML-Gamefiles aus den RDA-Archiven von Anno 117 und Anno 1800 direkt im Reiter Settings. Ein Fortschrittsfenster haelt die Oberflaeche waehrend der Extraktion in einem separaten Prozess reaktionsfaehig.
- **Themes:** Wählen Sie zwischen dem integrierten Dark-Theme und weiteren Farbschemata aus dem optionalen Paket [qt-themes](https://pypi.org/project/qt-themes/). Diff-Farben, XML-Syntaxfarben und Dropdown-Kopfzeilen folgen dem aktiven Theme.
- **Einstellbare Schriftgrößen:** Getrennte Schriftgrößen für Ergebnislisten und XML-Ansichten unter Settings > General > Text.
- **Update-Prüfung:** Beim Start vergleicht das Tool seine Version mit der veröffentlichten und verweist bei einer neueren Version auf GitHub.

#### Projektbeschreibung

**Anno XML Viewer** ist ein leichtgewichtiges, intuitives Tool, das die Datenanalyse für _Anno_-Modder rationalisiert. Anstatt sich durch riesige, unübersichtliche XML-Dateien zu wühlen, ermöglicht dieses Programm das sofortige Aufspüren von Assets anhand ihres **Namens** oder ihrer **GUID**. Sobald ein Asset ausgewählt ist, bildet das Programm dynamisch dessen gesamtes Ökosystem ab und zeigt alle verbundenen **Referenzen**, **Buffs** und **Effekte** auf einen Blick. Mit den integrierten **Template-Filtern** lassen sich gezielt bestimmte Asset-Kategorien isolieren. Der Reiter **GUID Compare** zeigt direkt in der Anwendung, was sich zwischen zwei Spielversionen geändert hat. Sie benötigen die Daten für andere Zwecke? Die Anwendung verfügt über eine umfassende **Exportfunktion**, die die kompletten XML-Daten inklusive aller Effekte und Buffs in eine saubere Datei für Ihr nächstes Modding-Projekt packt.

#### Funktionsübersicht

| Funktion | Beschreibung |
| --- | --- |
| **Unterstützte Spiele** | Anno 117 und Anno 1800 mit jeweils eigenen XML-Regeln |
| **Suchmodi** | Nach Asset-Name oder eindeutiger GUID, UND/ODER/Ausschluss, Platzhalter und XML-Snippets |
| **Relationale Ansicht** | Automatische Anzeige von Referenzen, Effekten und Buffs |
| **Filterung** | Filtern nach spezifischen Asset-Templates |
| **Watchlist** | Getrennte Listen für Anno 117 und Anno 1800 |
| **GUID Compare** | Gegenüberstellung eines Assets aus zwei Spielversionen oder zweier verschiedener Assets |
| **Texts** | Suche in texts_\*.xml nach exakter GUID oder Textbegriffen, mit XML-Ansicht |
| **Structure Library** | Auf- und zuklappbarer Baum aller XML-Pfade mit Werte-Vorschau |
| **Export** | Vollständiger XML-Dump inklusive aktiver Buffs/Effekte |
| **Gamefile-Extraktion** | Extraktion der Anno 117 / Anno 1800 XML-Gamefiles aus RDA-Archiven mit Fortschrittsanzeige |
| **Themes** | Integriertes Dark-Theme sowie optionale qt-themes-Farbschemata |
| **Schriftgrößen** | Getrennte Schriftgrößen für Ergebnislisten und XML-Ansichten |

#### Projektstruktur

| Datei | Zweck |
| --- | --- |
| `Anno_XML_Viewer.py` | Hauptfenster, Reiter und gesamte UI-Logik |
| `anno_game.py` | Basisklasse und Registry für die Datenablage eines Titels |
| `anno117.py` | Anno-117-Regeln (`LineId`-Textschlüssel, `Text/OasisId`-Anzeigenamen) |
| `anno1800.py` | Anno-1800-Regeln (`GUID`-Textschlüssel, Inline-`LocaText`, `properties.xml`) |
| `anno_value_only_tags.py` | Gemeinsame Werte-Tags (reine Zahlen) beider Spiele |
| `anno_buff_tags.py` | Gemeinsame Standard-Buff-/Effect-Tags beider Spiele |
| `anno_loader.py` | Hintergrund-Loader für Assets, Templates und Texte |
| `guid_compare.py` | Hintergrundsuche nach GUIDs, streamt große XML-Dateien |
| `guid_diff_view.py` | Gegenüberstellung mit Randspalte, Markierungen und synchronem Scrollen |
| `theme_manager.py` | Integriertes Theme, qt-themes-Anbindung und Farbhilfen |
| `rda_extractor.py` | Extraktion der Anno-117-/Anno-1800-Archive über RdaConsole |
| `build_onefile.py` | PyInstaller-Onefile-Build (bündelt die qt-themes-Dateien) |

### Support

---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

_Hinweis: Dies ist ein Fan-Projekt und steht in keiner Verbindung zu Ubisoft._
