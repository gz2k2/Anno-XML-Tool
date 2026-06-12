# Anno XML Viewer Documentation

## English Version (deuterliche Version unterhalb)
---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---
### 1. Introduction
The **Anno XML Viewer** is a specialized tool for modders of the *Anno* series. It allows for high-performance browsing, searching, and analyzing of game assets from `assets.xml`. It automatically resolves text IDs into readable strings and maps relationships between assets (e.g., buffs and effects).

### 2. Getting Started
1.  **Select Data Folder:** On the first start, go to the **Settings** tab. Use "Browse" to select the folder containing your game XMLs (must contain `assets.xml`; `templates.xml` and `texts_*.xml` are highly recommended for full functionality).
2.  **Language:** Select your preferred display language in the settings.
3.  **Loading:** The tool parses the data in the background. Check the **Engine Log** tab to see the progress.

### 3. Core Features

#### Asset Editor & Search
*   **Search Bar:** Enter terms to find assets. 
    *   Use spaces for "AND" logic (e.g., `farm sheep`).
    *   Use a minus prefix to exclude terms (e.g., `farm -module`).
*   **Search Depth:** By default, it searches GUIDs, Names, and Templates. Uncheck **"Search only GUID Text"** to search through all text content within the assets (slower but more thorough).
*   **Template Filter:** Click the "Template Filter..." button to isolate specific categories (e.g., only "Factory" or "Participant").

#### Analysis Panes
*   **Property Tree (Left):** Displays the `<Values>` section of an asset in a readable tree format. It automatically resolves GUIDs and Text-IDs into names.
*   **XML View (Middle):** Shows the raw, formatted XML code of the selected asset.
*   **Buffs / Effects (Right):** Automatically finds and displays all assets referenced as buffs or effects. Use the "Filter..." button above to toggle which reference tags (like `BoostBuffs` or `UnlockReward`) should be tracked.
*   **References (Top Right):** Shows "Reverse Search" results—every asset in the database that points to the currently selected GUID.

#### Structure Library
This tab provides a catalog of all unique XML tag paths found in the loaded data.
*   Selecting a path shows a structural preview of how this tag is used in the game templates.
*   It lists all unique values found for that specific tag across the entire dataset.

#### Export
The **EXPORT XML** button saves the selected asset into a new XML file. Crucially, it performs a **recursive export**: it also includes the full XML data of all detected buffs and effects (based on your active Buff Filter), making it an excellent tool for creating standalone mod snippets.

---

## Deutsche Version
---
*Support the project:*
<a href="https://ko-fi.com/gz2k2" target="_blank">Buy Me A Coffee</a>
---
### 1. Einleitung
Der **Anno XML Viewer** ist ein spezialisiertes Werkzeug für Modder der *Anno*-Serie. Er ermöglicht das performante Durchsuchen und Analysieren von Game-Assets aus der `assets.xml`. Das Tool löst Text-IDs automatisch in Klartext auf und bildet Beziehungen zwischen Assets (z. B. Buffs und Effekte) ab.

### 2. Erste Schritte
1.  **Datenordner wählen:** Navigieren Sie beim ersten Start zum Reiter **Settings**. Wählen Sie über "Browse" den Ordner aus, in dem Ihre XML-Dateien liegen (erfordert `assets.xml`; `templates.xml` und `texts_*.xml` werden für den vollen Funktionsumfang dringend empfohlen).
2.  **Sprache:** Wählen Sie in den Einstellungen die gewünschte Anzeigesprache.
3.  **Ladevorgang:** Das Programm lädt die Daten im Hintergrund. Der Fortschritt kann im Reiter **Engine Log** verfolgt werden.

### 3. Hauptfunktionen

#### Asset Editor & Suche
*   **Suchleiste:** Geben Sie Begriffe ein, um Assets zu finden.
    *   Leerzeichen entsprechen einer "UND"-Logik (z. B. `farm sheep`).
    *   Ein Minus-Präfix schließt Begriffe aus (z. B. `farm -module`).
*   **Suchtiefe:** Standardmäßig werden GUID, Name und Template durchsucht. Deaktivieren Sie **"Search only GUID Text"**, um sämtliche Textinhalte innerhalb der Assets zu durchsuchen (langsamer, aber gründlicher).
*   **Template-Filter:** Nutzen Sie den Button "Template Filter...", um die Suche auf bestimmte Kategorien (z. B. nur "Factory" oder "Participant") zu begrenzen.

#### Analyse-Fenster
*   **Property Tree (Links):** Zeigt die `<Values>`-Sektion eines Assets in einer Baumstruktur an. GUIDs und Text-IDs werden automatisch in Namen aufgelöst.
*   **XML View (Mitte):** Zeigt den rohen, formatierten XML-Code des gewählten Assets.
*   **Buffs / Effects (Rechts):** Findet und zeigt automatisch alle Assets an, die als Buffs oder Effekte verknüpft sind. Über den "Filter..."-Button lässt sich steuern, welche Tags (z. B. `BoostBuffs` oder `UnlockReward`) berücksichtigt werden.
*   **References (Oben Rechts):** Zeigt eine "Rückwärtssuche" – jedes Asset in der Datenbank, das auf die aktuell ausgewählte GUID verweist.

#### Structure Library (Struktur-Bibliothek)
Dieser Reiter bietet einen Katalog aller einzigartigen XML-Pfade, die in den geladenen Daten gefunden wurden.
*   Die Auswahl eines Pfades zeigt eine Struktur-Vorschau, wie dieser Tag in den Templates verwendet wird.
*   Zudem werden alle einzigartigen Werte aufgelistet, die für diesen spezifischen Tag im gesamten Datensatz existieren.

#### Export
Der **EXPORT XML**-Button speichert das gewählte Asset in eine neue XML-Datei. Das Besondere: Es erfolgt ein **rekursiver Export**. Das bedeutet, dass auch die vollständigen XML-Daten aller erkannten Buffs und Effekte (basierend auf Ihrem aktiven Buff-Filter) mit exportiert werden. Ideal zum Erstellen von Mod-Vorlagen.

---

### Technical Details / Technische Details

**Requirements / Anforderungen:**
*   Python 3.13+ (if running from source)
*   PyQt6

**Configuration:**
Settings are stored in `config.ini` in the application directory.

**Credits:**
Created by gz2k2. This is a fan project and not affiliated with Ubisoft.