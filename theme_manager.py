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
   environment variable is pointed at the bundled folder here.

    pip install qt-themes
"""

from __future__ import annotations

import os
import sys
import tempfile
import types

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QPainter, QPalette, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import QApplication

#: Environment variable qt-themes reads for additional theme search paths.
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
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        roots.append(meipass)
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
        try:
            if not any(name.endswith(".json") for name in os.listdir(path)):
                continue
        except OSError:
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
    QComboBox QAbstractItemView {
        background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #444; outline: 0;
        selection-background-color: #264f78; selection-color: #ffffff;
    }
    QComboBox QAbstractItemView::item { min-height: 22px; padding: 3px 8px; border: none; }
    QMenu { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; }
    QMenu::item { padding: 5px 24px 5px 12px; background: transparent; }
    QMenu::item:selected { background-color: #264f78; }
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

# Rules for qt-themes. Colours come from the palette so the theme stays in
# control, but every styled widget must be described COMPLETELY.
#
# Qt quirk: as soon as a single stylesheet property is set on a widget class,
# that widget stops being drawn by the native/Fusion style and is rendered by
# the stylesheet engine instead. Unspecified properties then fall back to
# "nothing" rather than to the style default - a QPushButton with only
# `padding` and `border-radius` loses its background and shows as bare text.
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

    /* The popup is a separate top-level view and does not inherit the combo
       box rule, so it has to be styled on its own. Group headers are NOT
       styled via ::item:disabled - Qt paints disabled items with the
       greyed-out palette group and ignores any colour set here. The viewer
       therefore keeps those items enabled and paints them with explicit
       foreground/background brushes instead. */
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
        padding: 3px 8px;
        border: none;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: palette(highlight);
        color: palette(highlighted-text);
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
    QMenu::separator {{ height: 1px; background: palette(mid); margin: 4px 8px; }}

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
        left: 8px; padding: 0 4px; color: {header};
    }}

    QLabel[sectionHeader="true"] {{
        background-color: palette(alternate-base); padding: 4px; font-weight: bold;
        border: 1px solid palette(mid); color: {header};
    }}
    QLabel[accentText="true"] {{ color: {header}; font-weight: bold; padding-left: 8px; }}
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
# Colour helpers
# --------------------------------------------------------------------------
def relative_luminance(color: QColor) -> float:
    """WCAG relative luminance of a colour."""
    channels = []
    for value in (color.redF(), color.greenF(), color.blueF()):
        channels.append(value / 12.92 if value <= 0.03928
                        else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: QColor, second: QColor) -> float:
    """WCAG contrast ratio between two colours (1.0 - 21.0)."""
    light, dark = sorted((relative_luminance(first), relative_luminance(second)),
                         reverse=True)
    return (light + 0.05) / (dark + 0.05)


def is_dark(color: QColor) -> bool:
    """Relative luminance test used to pick diff colour intensities."""
    return relative_luminance(color) < 0.5


def mix(color: QColor, background: QColor, weight: float) -> QColor:
    """Blend *color* over *background*; weight 0 -> background, 1 -> color."""
    return QColor(
        round(background.red() + (color.red() - background.red()) * weight),
        round(background.green() + (color.green() - background.green()) * weight),
        round(background.blue() + (color.blue() - background.blue()) * weight),
    )


def readable_on(color: QColor, background: QColor, min_ratio: float = 4.5) -> QColor:
    """Push *color* away from *background* until it is comfortably readable.

    Theme accents are picked to look good as a thin underline, not as text on
    a popup background. On several themes they end up nearly invisible - too
    dark on a dark base, too light on a light one - so the lightness is
    shifted step by step until the WCAG target is met. Hue and saturation are
    preserved, so the result still reads as the theme accent.
    """
    if contrast_ratio(color, background) >= min_ratio:
        return QColor(color)

    hue, saturation, lightness, alpha = QColor(color).getHslF()
    step = 0.04 if is_dark(background) else -0.04

    for _ in range(25):
        lightness = min(1.0, max(0.0, lightness + step))
        candidate = QColor.fromHslF(hue, saturation, lightness, alpha)
        if contrast_ratio(candidate, background) >= min_ratio:
            return candidate
        if lightness in (0.0, 1.0):
            break

    return QColor("#ffffff") if is_dark(background) else QColor("#000000")


def popup_background(key: str) -> QColor:
    """Background of a combo box popup for the given theme."""
    if key == ANNO_DARK:
        return QColor("#1e1e1e")
    app = QApplication.instance()
    palette = app.palette() if app is not None else QPalette()
    return palette.base().color()


def header_color(key: str) -> QColor:
    """Readable text colour for group headers and accent labels."""
    colors = editor_colors(key)
    return readable_on(colors["accent"], popup_background(key), 5.0)


def header_background(key: str) -> QColor:
    """Band colour behind a group header inside a popup."""
    background = popup_background(key)
    # A visible but subtle step away from the popup background.
    return background.lighter(160) if is_dark(background) else background.darker(112)


#: XML syntax colours for a dark editor background (VS Code "Dark+" palette).
_XML_COLORS_DARK = {
    "tag": "#4ec9b0",
    "attr": "#9cdcfe",
    "value": "#ce9178",
    "comment": "#6a9955",
    "text": "#dcdcdc",
}

#: The same roles for a light background. The dark palette is unusable here -
#: #dcdcdc body text on white is effectively invisible.
_XML_COLORS_LIGHT = {
    "tag": "#0f6f5c",
    "attr": "#0451a5",
    "value": "#a31515",
    "comment": "#3c7a3c",
    "text": "#1f1f1f",
}


def xml_highlight_colors(key: str) -> dict:
    """Syntax colours for the XML views, matched to the editor background.

    Every colour is additionally pushed to at least 4.5x contrast against the
    actual background, so a theme with an unusually light or dark base still
    produces readable markup.
    """
    background = editor_colors(key)["background"]
    palette = _XML_COLORS_DARK if is_dark(background) else _XML_COLORS_LIGHT
    return {role: readable_on(QColor(value), background, 4.5)
            for role, value in palette.items()}


def combo_header_color(key: str) -> QColor:
    """Readable text colour for a group header in a combo box popup.

    Measured against :func:`header_background`, not against the popup
    background: the header text is drawn on top of the band, and on a dark
    theme that band is noticeably lighter than the popup itself.
    """
    accent = editor_colors(key)["accent"]
    return readable_on(accent, header_background(key), 5.0)


# --------------------------------------------------------------------------
# Check boxes
# --------------------------------------------------------------------------
# Qt draws an indicator either with the widget style (Fusion, using the
# palette) or with the stylesheet engine - never with both. Neither
# stylesheet in this module used to mention QCheckBox at all, so the
# indicators kept whatever Fusion made of a theme palette: on most dark
# themes an almost black box on an almost black background, with a check
# mark in a barely lighter grey.
#
# Worse, a single partial rule is enough to break them completely. The
# search filter set only "QCheckBox::indicator { width: 12px; height: 12px }",
# which handed the rendering to the stylesheet engine while specifying
# neither border nor background - the same trap the QComboBox::drop-down
# comment above warns about. The result was an invisible indicator.
#
# The indicators are therefore described COMPLETELY and centrally here.

#: Edge length of an indicator in pixels.
INDICATOR_SIZE = 14

#: (colour name, size) -> PNG path, so the image is drawn once per theme.
_CHECKMARK_CACHE: dict = {}


def _icon_cache_dir() -> str:
    """Folder for the generated check-mark images."""
    path = os.path.join(tempfile.gettempdir(), "anno_xml_tool_icons")
    os.makedirs(path, exist_ok=True)
    return path


def checkmark_image(color: QColor, size: int = INDICATOR_SIZE) -> str:
    """Draw a check mark and return a path usable in ``image: url(...)``.

    A stylesheet cannot draw a glyph by itself, and Qt ships no built-in
    check-mark image that follows a palette. Rendering one to a PNG keeps
    the mark in a colour that actually contrasts with the filled indicator.
    Returns "" when no image could be produced; the caller then falls back
    to a plain filled box, which still reads as "checked".
    """
    cache_key = (color.name(), size)
    cached = _CHECKMARK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    # QPixmap needs a running QApplication.
    if QApplication.instance() is None:
        return ""

    path = os.path.join(_icon_cache_dir(),
                        f"check_{color.name().lstrip('#')}_{size}.png")
    url_path = path.replace("\\", "/")

    if os.path.isfile(path):
        _CHECKMARK_CACHE[cache_key] = url_path
        return url_path

    try:
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            pen = QPen(color)
            pen.setWidthF(max(1.6, size / 7.0))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            # Relative coordinates keep the shape correct at any size.
            # A QPolygon hits one unambiguous drawPolyline() overload;
            # passing loose points relies on a variadic form instead.
            painter.drawPolyline(QPolygon([
                QPoint(round(x * size), round(y * size))
                for x, y in ((0.22, 0.52), (0.42, 0.72), (0.78, 0.28))
            ]))
        finally:
            painter.end()

        if not pixmap.save(path, "PNG"):
            return ""
    except Exception:
        # A read-only temp folder must not cost the application its theme.
        return ""

    _CHECKMARK_CACHE[cache_key] = url_path
    return url_path


def _outline(text: QColor, background: QColor, min_ratio: float = 3.0) -> QColor:
    """Border colour that stays visible against *background*.

    WCAG asks for 3:1 on non-text elements such as an input border. Blending
    the text colour halfway into the background reaches that on dark themes
    but falls short on very light ones (Catppuccin Latte lands at 2.5), so
    the blend is strengthened until the target is met.
    """
    color = mix(text, background, 0.55)
    weight = 0.55
    while contrast_ratio(color, background) < min_ratio and weight < 1.0:
        weight = min(1.0, weight + 0.1)
        color = mix(text, background, weight)
    return color


def indicator_colors(key: str) -> dict:
    """Colours of a check box indicator for the given theme."""
    if key == ANNO_DARK:
        base = QColor("#1e1e1e")
        text = QColor("#e0e0e0")
        window = QColor("#121212")
    else:
        app = QApplication.instance()
        palette = app.palette() if app is not None else QPalette()
        base = palette.base().color()
        text = palette.text().color()
        window = palette.window().color()

    # The accent doubles as the fill of a checked box, so it has to stand
    # out against the unchecked one.
    accent = readable_on(QColor(_theme_accent(key)), base, 3.0)

    # Black or white, whichever is easier to read on the filled box.
    mark = max((QColor("#ffffff"), QColor("#000000")),
               key=lambda candidate: contrast_ratio(candidate, accent))

    return {
        "base": base,
        "text": text,
        # A clearly visible outline: the Fusion default sits far too close
        # to the background on most dark themes.
        "border": _outline(text, base),
        "accent": accent,
        "accent_hover": accent.lighter(115) if is_dark(base) else accent.darker(110),
        "mark": mark,
        "muted": mix(text, window, 0.45),
        "disabled_bg": mix(window, base, 0.5),
        "disabled_border": mix(text, window, 0.28),
    }


#: Doubled braces: this is a .format() template, like THEMED_STYLESHEET.
_CHECKBOX_TEMPLATE = """
    QCheckBox {{ spacing: 6px; color: {text}; background: transparent; }}
    QCheckBox:disabled {{ color: {muted}; }}
    QCheckBox::indicator {{
        width: {size}px;
        height: {size}px;
        border: 1px solid {border};
        border-radius: 3px;
        background-color: {base};
    }}
    QCheckBox::indicator:hover {{ border: 1px solid {accent}; }}
    QCheckBox::indicator:checked {{
        background-color: {accent};
        border: 1px solid {accent};{check_image}
    }}
    QCheckBox::indicator:checked:hover {{
        background-color: {accent_hover};
        border: 1px solid {accent_hover};
    }}
    QCheckBox::indicator:disabled {{
        background-color: {disabled_bg};
        border: 1px solid {disabled_border};
    }}
    QCheckBox::indicator:checked:disabled {{
        background-color: {disabled_border};
        border: 1px solid {disabled_border};
    }}
"""


def checkbox_stylesheet(key: str) -> str:
    """Complete indicator rules for one theme, appended to its stylesheet."""
    colors = indicator_colors(key)
    image = checkmark_image(colors["mark"])
    # Without an image the filled accent box alone marks the checked state.
    check_image = f'\n        image: url("{image}");' if image else ""

    return _CHECKBOX_TEMPLATE.format(
        size=INDICATOR_SIZE,
        text=colors["text"].name(),
        muted=colors["muted"].name(),
        base=colors["base"].name(),
        border=colors["border"].name(),
        accent=colors["accent"].name(),
        accent_hover=colors["accent_hover"].name(),
        disabled_bg=colors["disabled_bg"].name(),
        disabled_border=colors["disabled_border"].name(),
        check_image=check_image,
    )


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
        # Appended rather than baked in: the rules depend on the palette
        # that is active at this moment.
        window.setStyleSheet(ANNO_DARK_STYLESHEET + checkbox_stylesheet(ANNO_DARK))
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
        # The indicator rules are formatted separately and appended: they
        # have to be read after qt-themes installed its palette, because
        # every colour in them is derived from it.
        app.setStyleSheet(THEMED_STYLESHEET.format(
            accent=_theme_accent(key),
            header=header_color(key).name(),
        ) + checkbox_stylesheet(key))

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
