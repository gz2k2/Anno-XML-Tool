### Changelog
*   **Search only GUID Text checkbox**: Added a checkbox "Search only GUID Text". It is `True` by default and restricts the search to GUID, Template, and the primary display name (from `<Text><OasisId>`). When unchecked, all other text references within the asset (like `InfoDescription`) are also searched.
*   **Fallback for missing text**: If an `<OasisId>` exists but no corresponding text is found in the language files, the content of the `<Name>` tag is now used as a fallback for the display name.
*   **Default Language "English"**: The application now defaults to "English" if available, when data is loaded.
*   **Default Language in Settings**: Added an option in the "Settings" tab to define and save a default language, which is automatically selected upon loading.
*   **Status Bar Integration**: Moved status messages (loading progress, asset count) to a dedicated status bar at the bottom of the window for a cleaner UI.
*   **Exclude `texts_metadata.xml`**: The `texts_metadata.xml` file is now explicitly excluded from loading to prevent it from appearing as a language option.
*   **ComboBox Width Adjustment**: Adjusted the width of the language selection ComboBox for better visual consistency.
