# Anno XML Viewer Documentation

## English Version
---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

### 1. Introduction
The **Anno XML Viewer** is a specialized tool for modders of the *Anno* series. It allows high-performance browsing, searching, and analysis of game assets from `assets.xml`. The tool resolves text IDs into readable strings, maps relationships between assets, and helps inspect linked buffs, effects, templates, and XML structures.

### 2. Getting Started
1. **Select Data Folder:** Open the **Settings** tab and use **Browse...** to add one or more folders containing your XML files. A folder must contain `assets.xml`; `templates.xml` and `texts_*.xml` are recommended for full functionality.
2. **Choose Active Folder:** Use the XML path dropdown in the top bar to switch between saved XML folders. Switching the active folder reloads the data.
3. **Language:** Select the display language in the top bar. Set the default language in **Settings**.
4. **Loading:** The tool parses the data in the background. Check the **Engine Log** tab for progress and status messages.

### 3. Core Features

#### Asset Editor & Search
* **Search Bar:** Enter one or more terms to find assets.
  * Spaces use "AND" logic, for example `farm sheep`.
  * A minus prefix excludes terms, for example `farm -module`.
* **Search Depth:** By default, the search checks GUID, display name, and template. Disable **Search only GUID Text** to search all XML text content inside assets. This is slower but more thorough.
* **Template Filter:** Click **Template Filter...** to select or deselect template categories. The popup includes a template search field plus **Select All** and **Deselect All** buttons.
* **Asset Table:** Shows GUID, display name, and template. Selecting a row updates the analysis panes.

#### Watchlist
* The **WATCHLIST** panel stores selected assets by GUID for quick access.
* Use **+** to add the currently selected asset.
* Use **-** to remove the selected watchlist entry.
* Watchlist entries are saved in `config.ini` and restored on restart.

#### Analysis Panes
* **Property Tree:** Displays the `<Values>` section of the selected asset in a readable tree. GUIDs and text IDs are resolved into names where possible.
* **XML View:** Shows the raw, formatted XML of the selected asset.
* **Buffs / Effects:** Shows linked assets referenced through configured buff/effect tags. Use the **Filter...** button to select which categories are shown.
* **References:** Shows reverse-search results: assets that reference the currently selected GUID.

#### Templates
The **Templates** tab lists templates from `templates.xml`.
* Use the search field to filter templates.
* Selecting a template shows its formatted XML preview.

#### Structure Library
The **Structure Library** tab catalogs unique XML tag paths found in the loaded data.
* Use the search field to filter paths.
* Selecting a path shows a structural preview and known values for that path across the dataset.

#### Engine Log
The **Engine Log** tab displays background loading progress, parser messages, warnings, and errors.

#### Settings
The **Settings** tab stores application configuration.
* **Path Configuration:** Add XML folders with **Browse...** and remove saved folders with **Remove Selected**.
* **Default Language:** Choose the language selected by default after loading.
* **Buff/Effect XML tags:** Edit the tag list used to detect linked buffs and effects. Use **Add Tag** and **Remove Selected Tag** to manage entries.
* **Save Settings:** Writes paths, default language, and buff/effect tags to `config.ini`, then reloads the active XML folder.

#### Export
The **EXPORT XML** button saves the selected asset into a new XML file. It performs a recursive export: detected buffs and effects are included based on the active Buff/Effect filter, which makes it useful for creating standalone mod snippets.

---

## Deutsche Version
---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---

### 1. Einleitung
Der **Anno XML Viewer** ist ein spezialisiertes Werkzeug fuer Modder der *Anno*-Serie. Er ermoeglicht schnelles Durchsuchen, Anzeigen und Analysieren von Game-Assets aus `assets.xml`. Das Tool loest Text-IDs in lesbare Texte auf, zeigt Beziehungen zwischen Assets und hilft beim Pruefen von Buffs, Effekten, Templates und XML-Strukturen.

### 2. Erste Schritte
1. **Datenordner waehlen:** Oeffne den Reiter **Settings** und fuege mit **Browse...** einen oder mehrere Ordner mit XML-Dateien hinzu. Ein Ordner muss `assets.xml` enthalten; `templates.xml` und `texts_*.xml` werden fuer den vollen Funktionsumfang empfohlen.
2. **Aktiven Ordner waehlen:** Ueber das XML-Pfad-Dropdown in der oberen Leiste kannst du zwischen gespeicherten XML-Ordnern wechseln. Beim Wechsel werden die Daten neu geladen.
3. **Sprache:** Waehle die Anzeigesprache in der oberen Leiste. Die Standardsprache wird unter **Settings** festgelegt.
4. **Ladevorgang:** Das Programm laedt die Daten im Hintergrund. Fortschritt und Statusmeldungen stehen im Reiter **Engine Log**.

### 3. Hauptfunktionen

#### Asset Editor & Suche
* **Suchleiste:** Gib einen oder mehrere Begriffe ein, um Assets zu finden.
  * Leerzeichen verwenden eine "UND"-Logik, zum Beispiel `farm sheep`.
  * Ein Minus-Praefix schliesst Begriffe aus, zum Beispiel `farm -module`.
* **Suchtiefe:** Standardmaessig durchsucht das Tool GUID, Anzeigename und Template. Deaktiviere **Search only GUID Text**, um den gesamten XML-Textinhalt der Assets zu durchsuchen. Das ist langsamer, aber gruendlicher.
* **Template-Filter:** Mit **Template Filter...** kannst du Template-Kategorien auswaehlen oder abwaehlen. Das Popup enthaelt eine Suche sowie **Select All** und **Deselect All**.
* **Asset-Tabelle:** Zeigt GUID, Anzeigename und Template. Die Auswahl einer Zeile aktualisiert die Analyse-Fenster.

#### Watchlist
* Das **WATCHLIST**-Fenster speichert ausgewaehlte Assets per GUID fuer schnellen Zugriff.
* Mit **+** wird das aktuell ausgewaehlte Asset hinzugefuegt.
* Mit **-** wird der ausgewaehlte Watchlist-Eintrag entfernt.
* Die Watchlist wird in `config.ini` gespeichert und beim Neustart wiederhergestellt.

#### Analyse-Fenster
* **Property Tree:** Zeigt die `<Values>`-Sektion des ausgewaehlten Assets als Baumstruktur. GUIDs und Text-IDs werden soweit moeglich in Namen aufgeloest.
* **XML View:** Zeigt den rohen, formatierten XML-Code des ausgewaehlten Assets.
* **Buffs / Effects:** Zeigt verknuepfte Assets, die ueber konfigurierte Buff-/Effect-Tags referenziert werden. Mit **Filter...** steuerst du, welche Kategorien angezeigt werden.
* **References:** Zeigt die Rueckwaertssuche: Assets, die auf die aktuell ausgewaehlte GUID verweisen.

#### Templates
Der Reiter **Templates** listet Templates aus `templates.xml`.
* Mit dem Suchfeld filterst du die Template-Liste.
* Die Auswahl eines Templates zeigt eine formatierte XML-Vorschau.

#### Structure Library
Der Reiter **Structure Library** katalogisiert einzigartige XML-Pfade aus den geladenen Daten.
* Mit dem Suchfeld filterst du die Pfade.
* Die Auswahl eines Pfades zeigt eine Struktur-Vorschau und bekannte Werte dieses Pfades im Datensatz.

#### Engine Log
Der Reiter **Engine Log** zeigt Ladefortschritt, Parser-Meldungen, Warnungen und Fehler.

#### Settings
Der Reiter **Settings** verwaltet die Anwendungskonfiguration.
* **Path Configuration:** XML-Ordner mit **Browse...** hinzufuegen und gespeicherte Ordner mit **Remove Selected** entfernen.
* **Default Language:** Legt die Sprache fest, die nach dem Laden standardmaessig verwendet wird.
* **Buff/Effect XML tags:** Bearbeitet die Tag-Liste, mit der verknuepfte Buffs und Effekte erkannt werden. Eintraege werden mit **Add Tag** und **Remove Selected Tag** verwaltet.
* **Save Settings:** Speichert Pfade, Standardsprache und Buff-/Effect-Tags in `config.ini` und laedt den aktiven XML-Ordner neu.

#### Export
Der Button **EXPORT XML** speichert das ausgewaehlte Asset in eine neue XML-Datei. Dabei erfolgt ein rekursiver Export: Erkannte Buffs und Effekte werden basierend auf dem aktiven Buff-/Effect-Filter mit exportiert. Das ist nuetzlich zum Erstellen eigenstaendiger Mod-Snippets.

---

### Technical Details / Technische Details

**Requirements / Anforderungen:**
* Python 3.13+ if running from source
* PyQt6

**Configuration / Konfiguration:**
Settings are stored in `config.ini` in the application directory. This includes XML paths, active/default language, buff/effect tags, and watchlist GUIDs.

**Credits:**
Created by gz2k2. This is a fan project and not affiliated with Ubisoft.
