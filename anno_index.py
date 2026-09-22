"""On-disk index so a known XML folder does not have to be re-parsed.

Two problems are solved here.

**Repeated loading.** Parsing a multi-hundred-MB assets.xml takes seconds
every single time the folder is selected, even though nothing changed. The
index stores everything the loader derived - asset metadata, reverse
references, structure catalog, template library - next to a fingerprint of the
source files. A second load turns into one ``pickle.load`` plus an ``mmap``.

**Memory.** The loader used to keep the serialised XML of every asset as an
individual ``str``: hundreds of thousands of small Python objects, each with
its own header. :class:`AssetStore` replaces them with a single flat buffer
plus (offset, length) pairs, and hands out the text only when an asset is
actually opened. On a cached load that buffer is not even read into RAM - it
is memory-mapped, so the OS pages in just the assets that get clicked.

Layout of the cache directory::

    <cache>/<key>.idx    pickled metadata (see _PAYLOAD_KEYS)
    <cache>/<key>.blob   concatenated <Asset> XML, UTF-8

``<key>`` is derived from the absolute folder path and the game key, so the
two games never share an index even if they point at the same folder.
"""

from __future__ import annotations

import hashlib
import mmap
import os
import pickle
from collections.abc import Mapping

#: Bumped whenever the payload layout or the record fields change. An older
#: file is then simply ignored and rebuilt instead of crashing the loader.
CACHE_VERSION = 1

_RECORD_KEYS = (
    "xml",
    "template_name",
    "oasis_id",
    "visible_tech_name_id",
    "info_description_id",
    "fallback_name",
    "text_ids",
)


# --------------------------------------------------------------------------
# Asset storage
# --------------------------------------------------------------------------
class AssetStore:
    """Flat UTF-8 buffer holding the serialised XML of every asset."""

    def __init__(self, buffer=None):
        self._buffer = buffer if buffer is not None else bytearray()
        self._mapping = None
        self._handle = None

    # -- writing ----------------------------------------------------------
    def add(self, xml_text: str) -> tuple[int, int]:
        """Append one asset; return its (offset, length) in the buffer."""
        encoded = xml_text.encode("utf-8")
        offset = len(self._buffer)
        self._buffer += encoded
        return offset, len(encoded)

    def write(self, path: str) -> None:
        with open(path, "wb") as blob:
            blob.write(self._buffer)

    # -- reading ----------------------------------------------------------
    def text(self, offset: int, length: int) -> str:
        if not length:
            return ""
        return bytes(self._buffer[offset:offset + length]).decode("utf-8")

    @property
    def size(self) -> int:
        return len(self._buffer)

    @classmethod
    def from_file(cls, path: str) -> "AssetStore":
        """Memory-map an existing blob instead of reading it into RAM."""
        store = cls()
        handle = open(path, "rb")
        try:
            size = os.fstat(handle.fileno()).st_size
            if size:
                mapping = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
                store._buffer = mapping
                store._mapping = mapping
            else:
                store._buffer = bytearray()
            store._handle = handle
        except Exception:
            handle.close()
            raise
        return store

    def __del__(self):
        # The store outlives the loader: the asset records keep it alive.
        # Once the last record of a folder is dropped, the mapping and the
        # file handle have to go with it.
        try:
            self.close()
        except Exception:
            pass

    def close(self) -> None:
        if self._mapping is not None:
            self._mapping.close()
            self._mapping = None
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        self._buffer = bytearray()


class AssetRecord(Mapping):
    """One asset as the UI sees it; ``record["xml"]`` is resolved lazily."""

    __slots__ = ("_store", "_offset", "_length", "template_name", "oasis_id",
                 "visible_tech_name_id", "info_description_id",
                 "fallback_name", "text_ids")

    def __init__(self, store, offset, length, template_name, oasis_id,
                 visible_tech_name_id, info_description_id, fallback_name,
                 text_ids):
        self._store = store
        self._offset = offset
        self._length = length
        self.template_name = template_name
        self.oasis_id = oasis_id
        self.visible_tech_name_id = visible_tech_name_id
        self.info_description_id = info_description_id
        self.fallback_name = fallback_name
        self.text_ids = text_ids

    # -- Mapping protocol -------------------------------------------------
    def __getitem__(self, key):
        if key == "xml":
            return self._store.text(self._offset, self._length)
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None

    def __iter__(self):
        return iter(_RECORD_KEYS)

    def __len__(self):
        return len(_RECORD_KEYS)

    # -- cache support ----------------------------------------------------
    def as_tuple(self) -> tuple:
        """Plain tuple for pickling - the store is rebound on load."""
        return (self._offset, self._length, self.template_name, self.oasis_id,
                self.visible_tech_name_id, self.info_description_id,
                self.fallback_name, self.text_ids)


# --------------------------------------------------------------------------
# Fingerprinting
# --------------------------------------------------------------------------
def _stat_mark(path: str) -> tuple:
    try:
        stat = os.stat(path)
        return (os.path.abspath(path), int(stat.st_mtime), stat.st_size)
    except OSError:
        return (os.path.abspath(path), 0, 0)


def fingerprint(files: dict, text_fingerprint=()) -> tuple:
    """Identity of the source data; any change invalidates the index."""
    marks = [_stat_mark(files.get("assets", "")),
             _stat_mark(files.get("templates", "")),
             _stat_mark(files.get("properties", ""))]
    return (CACHE_VERSION, tuple(marks), tuple(text_fingerprint))


def cache_key(folder: str, game_key: str) -> str:
    raw = f"{game_key}|{os.path.normcase(os.path.abspath(folder or ''))}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    name = os.path.basename(os.path.abspath(folder or "data")) or "data"
    # A readable prefix makes the cache folder inspectable by hand.
    safe = "".join(char if char.isalnum() else "_" for char in name)[:32]
    return f"{safe}_{game_key}_{digest}"


def _paths(cache_dir: str, key: str) -> tuple[str, str]:
    return (os.path.join(cache_dir, key + ".idx"),
            os.path.join(cache_dir, key + ".blob"))


# --------------------------------------------------------------------------
# Reading / writing
# --------------------------------------------------------------------------
def load(cache_dir: str, folder: str, game_key: str, expected) -> dict | None:
    """Return the cached payload, or None when it is missing or stale."""
    if not cache_dir:
        return None

    index_path, blob_path = _paths(cache_dir, cache_key(folder, game_key))
    if not (os.path.isfile(index_path) and os.path.isfile(blob_path)):
        return None

    try:
        with open(index_path, "rb") as handle:
            payload = pickle.load(handle)
    except (OSError, pickle.UnpicklingError, EOFError, AttributeError):
        return None

    if not isinstance(payload, dict) or payload.get("version") != CACHE_VERSION:
        return None
    if payload.get("fingerprint") != expected:
        return None

    try:
        store = AssetStore.from_file(blob_path)
    except OSError:
        return None

    if store.size != payload.get("blob_size", -1):
        store.close()
        return None

    assets = {guid: AssetRecord(store, *values)
              for guid, values in payload["assets"].items()}

    payload["assets"] = assets
    payload["store"] = store
    return payload


def save(cache_dir: str, folder: str, game_key: str, expected,
         assets: dict, store: AssetStore, templates: dict, reverse_index: dict,
         structure_catalog, template_library: dict, value_catalog: dict) -> str:
    """Write the index; returns the index path, or "" when it failed."""
    if not cache_dir:
        return ""

    try:
        os.makedirs(cache_dir, exist_ok=True)
    except OSError:
        return ""

    index_path, blob_path = _paths(cache_dir, cache_key(folder, game_key))
    payload = {
        "version": CACHE_VERSION,
        "fingerprint": expected,
        "game": game_key,
        "folder": os.path.abspath(folder),
        "blob_size": store.size,
        "assets": {guid: record.as_tuple() for guid, record in assets.items()},
        "templates": templates,
        "reverse_index": reverse_index,
        "structure_catalog": list(structure_catalog),
        "template_library": template_library,
        "value_catalog": value_catalog,
    }

    try:
        # Write to a temporary name first: a half-written index must never
        # look valid to the next start.
        store.write(blob_path + ".tmp")
        with open(index_path + ".tmp", "wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(blob_path + ".tmp", blob_path)
        os.replace(index_path + ".tmp", index_path)
    except (OSError, pickle.PicklingError):
        for leftover in (blob_path + ".tmp", index_path + ".tmp"):
            try:
                os.remove(leftover)
            except OSError:
                pass
        return ""

    return index_path
