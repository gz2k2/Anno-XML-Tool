"""Theme handling: the built-in Anno Dark look plus optional qt-themes.

qt-themes applies its colour schemes through a QPalette. A widget stylesheet
always wins over the palette, so the hard-coded Anno Dark stylesheet has to be
removed before a qt-theme can take effect. This module owns both stylesheets
and switches between the two modes.

Two things make qt-themes awkward to ship:

1. It only looks for `qtpy`, `PySide6` and `PySide2` - it never imports PyQt6
   directly. On a PyQt6-only installation the import fails even though the
   package is installed, so a minimal `qtpy` shim backed by PyQt6 is
   registered first.
2. The themes themselves are JSON data files inside the package. PyInstaller
   does not bundle package data by default, so in a one-file build the theme
   folder is empty and only the built-in theme shows up. The build script
   collects them with `--collect-data qt_themes`; additionally the QT_THEMES
   environment variable is pointed at the bundled folder here, which is the
   officially supported way to add theme search paths.

    pip install qt-themes
"""

from __future__ import annotations

import os
import sys
import types

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# Environment variable qt-themes reads for additional theme search paths.
QT_THEMES_ENV = "QT_THEMES"


def _install_qtpy_shim() -> None:
    """Expose PyQt6 under the `qtpy` name so qt-themes can import it."""
    if "qtpy" in sys.modules:
        return
    try:  # a real qtpy installation always wins
        import qtpy  # noqa: F401
        return
    except ImportError:
        pass

    from PyQt6 import QtCore, QtGui, QtWidgets

    shim = types.ModuleType("qtpy")
    shim.QtCore, shim.QtGui, shim.QtWidgets = QtCore, QtGui, QtWidgets
    shim.API_NAME = "PyQt6"
    sys.modules["qtpy"] = shim
    sys.modules["qtpy.QtCore"] = QtCore
    sys.modules["qtpy.QtGui"] = QtGui
    sys.modules["qtpy.QtWidgets"] = QtWidgets


def _candidate_theme_dirs() -> list[str]:
    """Folders that may hold the bundled qt-themes *.json files."""
    roots = []
    # PyInstaller one-file: everything is unpacked below sys._MEIPASS.
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        roots.append(meipass)
    # PyInstaller one-folder / plain script: next to the executable.
    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(sys.executable))
    roots.append(os.path.dirname(os.path.abspath(__file__)))

    candidates = []
    for root in roots:
        candidates.append(os.path.join(root, "qt_themes", "themes"))
        candidates.append(os.path.join(root, "themes"))
    return candidates


def _register_bundled_themes() -> str:
    """Point QT_THEMES at the bundled theme folder; return the folder used."""
    existing = os.environ.get(QT_THEMES_ENV, "")
    for path in _candidate_theme_dirs():
        if not os.path.isdir(path):
            continue
        if not any(name.endswith(".json") for name in os.listdir(path)):
            continue
        parts = [part for part in existing.split(os.pathsep) if part]
        if path not in parts:
            parts.append(path)
            os.environ[QT_THEMES_ENV] = os.pathsep.join(parts)
        return path
    return ""


BUNDLED_THEMES_DIR = ""
QT_THEMES_ERROR = ""
try:
    _install_qtpy_shim()
    BUNDLED_THEMES_DIR = _register_bundled_themes()
    import qt_themes
except Exception as exc:  # pragma: no cover - import guard only
    qt_themes = None
    QT_THEMES_ERROR = f"{type(exc).__name__}: {exc}"


ANNO_DARK = "anno_dark"
ANNO_DARK_LABEL = "Anno Dark (built-in)"
DEFAULT_ACCENT = "#81c784"

# Theme names shipped with qt-themes 0.4, in drop-down order. Unknown names are
# ignored and any extra theme found on disk is appended automatically.
_PREFERRED_ORDER = (
    "modern_dark", "modern_light",
    "one_dark_two", "atom_one", "monokai", "dracula", "nord", "blender",
    "github_dark", "github_light",
    "catppuccin_mocha", "catppuccin_macchiato",
    "catppuccin_frappe", "catppuccin_latte",
)

# --------------------------------------------------------------------------
# Stylesheets
# --------------------------------------------------------------------------
ANNO_DARK_STYLESHEET = """
    QMainWindow, QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
    QTableWidget, QTreeWidget, QTextEdit, QPlainTextEdit, QListWidget {
        background-color: #1e1e1e; border: 1px solid #333; gridline-color: #333; border-radius: 4px;
    }
    QHeaderView::section { background-color: #252525; padding: 4px; border: 1px solid #333; }
    QTableCornerButton::section { background-color: #252525; border: 1px solid #333; }
    QPushButton { background-color: #333; border: 1px solid #444; padding: 6px; border-radius: 4px; }
    QPushButton:hover { background-color: #444; }
    QPushButton:disabled { color: #666; border-color: #333; }
    QLineEdit, QComboBox { background-color: #1e1e1e; border: 1px solid #444; padding: 4px; color: white; }
    QTabWidget::pane { border: 1px solid #333; }
    QTabBar::tab { background: #252525; padding: 10px 20px; border: 1px solid #333; border-bottom: none; }
    QTabBar::tab:selected { background: #1e1e1e; border-bottom: 2px solid #1b5e20; }
    QGroupBox {
        border: 1px solid #333; border-radius: 4px;
        margin-top: 10px; padding-top: 8px; font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin; subcontrol-position: top left;
        left: 8px; padding: 0 4px; color: #81c784;
    }
    QLabel[sectionHeader="true"] {
        background-color: #252525; padding: 4px; font-weight: bold;
        border: 1px solid #333; color: #81c784;
    }
    QLabel[accentText="true"] { color: #81c784; font-weight: bold; padding-left: 8px; }
"""

# Rules for qt-themes. Colours are taken from the palette so the theme stays
# in control, but every styled widget must be described COMPLETELY.
#
# Qt quirk: as soon as a single stylesheet property is set on a widget class,
# that widget stops being drawn by the native/Fusion style and is rendered by
# the stylesheet engine instead. Properties that are not specified then fall
# back to "nothing" rather than to the style default - a QPushButton with only
# `padding` and `border-radius` therefore loses its background and border and
# shows up as bare text. Hence the explicit background/border/state rules.
THEMED_STYLESHEET = """
    QMainWindow, QWidget {{ font-family: 'Segoe UI', sans-serif; }}
    QTableWidget, QTreeWidget, QTextEdit, QPlainTextEdit, QListWidget {{
        border: 1px solid palette(mid);
        border-radius: 4px;
    }}

    QHeaderView::section {{
        background-color: palette(button);
        color: palette(button-text);
        border: 1px solid palette(mid);
        padding: 4px;
    }}
    QTableCornerButton::section {{
        background-color: palette(button);
        border: 1px solid palette(mid);
    }}

    QPushButton {{
        background-color: palette(button);
        color: palette(button-text);
        border: 1px solid palette(mid);
        border-radius: 4px;
        padding: 6px 12px;
    }}
    QPushButton:hover {{ background-color: palette(light); }}
    QPushButton:pressed {{ background-color: palette(dark); }}
    /* There is no palette(disabled-text) role - palette(mid) is the
       conventional stand-in for greyed-out text. */
    QPushButton:disabled {{
        color: palette(mid);
        background-color: palette(window);
        border-color: palette(dark);
    }}

    QLineEdit, QComboBox, QSpinBox, QAbstractSpinBox {{
        background-color: palette(base);
        color: palette(text);
        border: 1px solid palette(mid);
        border-radius: 3px;
        padding: 4px;
        min-height: 18px;
        selection-background-color: palette(highlight);
        selection-color: palette(highlighted-text);
    }}
    QLineEdit:disabled, QComboBox:disabled {{
        color: palette(mid);
        background-color: palette(window);
    }}
    QComboBox:hover {{ border: 1px solid palette(highlight); }}

    /* QComboBox::drop-down and ::down-arrow are deliberately NOT styled.
       Touching either subcontrol makes the stylesheet engine take over its
       rendering, and without an `image:` it then draws no arrow at all. */

    /* The popup is a separate top-level view and does not inherit the
       combo box rule, so it has to be styled on its own. */
    QComboBox QAbstractItemView {{
        background-color: palette(base);
        color: palette(text);
        border: 1px solid palette(mid);
        outline: 0;
        selection-background-color: palette(highlight);
        selection-color: palette(highlighted-text);
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 22px;
        padding: 2px 6px;
        border: none;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: palette(highlight);
        color: palette(highlighted-text);
    }}
    /* Disabled entries are used as group headers in the folder selectors. */
    QComboBox QAbstractItemView::item:disabled {{
        color: {accent};
        background-color: palette(alternate-base);
        font-weight: bold;
    }}

    /* Context menus are top-level windows and need their own rule. */
    QMenu {{
        background-color: palette(base);
        color: palette(text);
        border: 1px solid palette(mid);
    }}
    QMenu::item {{ padding: 5px 24px 5px 12px; background: transparent; }}
    QMenu::item:selected {{
        background-color: palette(highlight);
        color: palette(highlighted-text);
    }}
    QMenu::item:disabled {{ color: palette(mid); }}
    QMenu::separator {{
        height: 1px; background: palette(mid); margin: 4px 8px;
    }}

    QToolTip {{
        background-color: palette(base);
        color: palette(text);
        border: 1px solid palette(mid);
        padding: 3px;
    }}

    QTabWidget::pane {{ border: 1px solid palette(mid); }}
    QTabBar::tab {{
        background: palette(window);
        color: palette(text);
        border: 1px solid palette(mid);
        border-bottom: none;
        padding: 10px 20px;
    }}
    QTabBar::tab:selected {{
        background: palette(base);
        border-bottom: 2px solid {accent};
    }}
    QTabBar::tab:hover {{ background: palette(light); }}

    QGroupBox {{
        border: 1px solid palette(mid); border-radius: 4px;
        margin-top: 10px; padding-top: 8px; font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin; subcontrol-position: top left;
        left: 8px; padding: 0 4px; color: {accent};
    }}

    QLabel[sectionHeader="true"] {{
        background-color: palette(alternate-base); padding: 4px; font-weight: bold;
        border: 1px solid palette(mid); color: {accent};
    }}
    QLabel[accentText="true"] {{ color: {accent}; font-weight: bold; padding-left: 8px; }}
"""

_default_palette: QPalette | None = None
_default_style: str = ""


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------
def qt_themes_available() -> bool:
    """True when the optional qt-themes package could be imported."""
    return qt_themes is not None


def unavailable_reason() -> str:
    """Why qt-themes is not usable, for the settings hint and the log."""
    if qt_themes is None:
        if "No module named 'qt_themes'" in QT_THEMES_ERROR:
            if getattr(sys, "frozen", False):
                return ("qt-themes was not bundled into this build "
                        "(rebuild with --collect-data qt_themes)")
            return "qt-themes is not installed (pip install qt-themes)"
        return QT_THEMES_ERROR or "qt-themes could not be loaded"

    if not _installed_theme_names():
        if getattr(sys, "frozen", False):
            return ("no theme files found in this build "
                    "(rebuild with --collect-data qt_themes)")
        return "qt-themes is installed but contains no theme files"
    return ""


def diagnostics() -> str:
    """One-line status for the engine log."""
    if qt_themes is None:
        return f"qt-themes unavailable - {unavailable_reason()}"

    count = len(_installed_theme_names())
    if not count:
        return f"qt-themes loaded but no themes found - {unavailable_reason()}"

    source = BUNDLED_THEMES_DIR or "package data"
    return f"qt-themes ready, {count} extra themes available (source: {source})"


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _installed_theme_names() -> list[str]:
    """Theme names reported by qt-themes, preferred ones first."""
    if qt_themes is None:
        return []
    try:
        names = [str(name) for name in qt_themes.get_themes()]
    except Exception:
        return []

    order = {name: index for index, name in enumerate(_PREFERRED_ORDER)}
    names.sort(key=lambda name: (order.get(name, len(order)), name))
    return names


def list_themes() -> list[tuple[str, str]]:
    """Return [(key, label)] with the built-in theme always first."""
    themes = [(ANNO_DARK, ANNO_DARK_LABEL)]
    themes.extend((name, _pretty(name)) for name in _installed_theme_names())
    return themes


def is_valid(key: str) -> bool:
    return key in {theme_key for theme_key, _label in list_themes()}


# --------------------------------------------------------------------------
# Applying
# --------------------------------------------------------------------------
def _theme_accent(key: str) -> str:
    """Accent colour of a qt-theme, falling back to the Anno green."""
    if qt_themes is None or key == ANNO_DARK:
        return DEFAULT_ACCENT
    try:
        theme = qt_themes.get_theme(key)
    except Exception:
        theme = None
    if theme is None:
        return DEFAULT_ACCENT

    for attribute in ("primary", "green", "secondary", "blue", "cyan"):
        colour = getattr(theme, attribute, None)
        if colour is None:
            continue
        try:
            converted = QColor(colour)
            if converted.isValid():
                return converted.name()
        except Exception:
            continue
    return DEFAULT_ACCENT


def apply_theme(window, key: str) -> str:
    """Apply a theme to the whole application; return the key actually used."""
    global _default_palette, _default_style

    app = QApplication.instance()
    if app is None:
        return ANNO_DARK
    if _default_palette is None:
        _default_palette = QPalette(app.palette())
        style = app.style()
        _default_style = style.objectName() if style is not None else ""

    if not is_valid(key):
        key = ANNO_DARK

    if key == ANNO_DARK:
        app.setStyleSheet("")
        # set_theme() switches the widget style to Fusion, so undo that too.
        if _default_style:
            app.setStyle(_default_style)
        app.setPalette(_default_palette)
        window.setStyleSheet(ANNO_DARK_STYLESHEET)
    else:
        # The window stylesheet has to go first, otherwise it keeps
        # overriding the palette that qt-themes installs.
        window.setStyleSheet("")
        app.setStyleSheet("")
        try:
            qt_themes.set_theme(key)
        except Exception:
            # A broken theme file must never leave the UI unstyled.
            return apply_theme(window, ANNO_DARK)
        app.setStyleSheet(THEMED_STYLESHEET.format(accent=_theme_accent(key)))

    return key


def editor_colors(key: str) -> dict:
    """Background/text/accent used by the code and diff views."""
    if key == ANNO_DARK:
        return {"background": QColor("#1e1e1e"),
                "text": QColor("#d4d4d4"),
                "accent": QColor(DEFAULT_ACCENT)}

    app = QApplication.instance()
    palette = app.palette() if app is not None else QPalette()
    return {"background": palette.base().color(),
            "text": palette.text().color(),
            "accent": QColor(_theme_accent(key))}


def is_dark(color: QColor) -> bool:
    """Relative luminance test used to pick diff colour intensities."""
    return (0.2126 * color.redF()
            + 0.7152 * color.greenF()
            + 0.0722 * color.blueF()) < 0.5
