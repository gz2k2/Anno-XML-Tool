"""RdaConsole extraction helpers."""
import os
import subprocess
import re
import shutil

NET_CONSOLE_EXIT_CODE = 3762504530
XML_FILTER = r"(assets\.xml|templates\.xml|properties[^\\/]*\.xml|Ttexts_[^\\/]*\.xml)$"
subprocess_timeout_error = subprocess.TimeoutExpired

def extract_archive(app_dir, archive, output_folder, xml_filter, timeout=300):
    exe = os.path.join(app_dir, "RdaConsole.exe")
    if not os.path.isfile(exe):
        raise FileNotFoundError(exe)
    command = [exe, "extract", "-f", archive, "-o", output_folder,
               "-y", "-n", "--filter", xml_filter]
    kwargs = dict(cwd=app_dir, capture_output=True, text=True, timeout=timeout)
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(command, **kwargs)
    output = (result.stdout or "") + (result.stderr or "")
    return command, result.returncode, output


def extract_gamefiles(app_dir, archive, output_folder, timeout=300):
    return extract_archive(app_dir, archive, output_folder, XML_FILTER, timeout)


ANNO1800_FILES = [
    "assets.xml", "properties.xml", "templates.xml", "texts_brazilian.xml", "texts_chinese.xml",
    "texts_english.xml", "texts_french.xml", "texts_german.xml", "texts_italian.xml",
    "texts_japanese.xml", "texts_korean.xml", "texts_polish.xml", "texts_portuguese.xml",
    "texts_russian.xml", "texts_spanish.xml", "texts_taiwanese.xml",
]


def _keep_only_data_config(output_folder):
    """Keep only the extracted data/config tree in an Anno 1800 output."""
    data_root = os.path.join(output_folder, "data")
    config_root = os.path.join(data_root, "config")
    if not os.path.isdir(config_root):
        return

    # Remove files/directories outside data/.
    for entry in os.listdir(output_folder):
        if entry != "data":
            path = os.path.join(output_folder, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)

    # Keep only data/config and its subdirectories.
    for entry in os.listdir(data_root):
        if entry != "config":
            path = os.path.join(data_root, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)


def _data_rda_sort_key(path):
    match = re.search(r"data(\d*)\.rda$", os.path.basename(path), re.IGNORECASE)
    return int(match.group(1) or 0) if match else -1


def extract_anno1800_gamefiles(app_dir, game_folder, output_folder, timeout=300):
    archives = []
    for root, _dirs, files in os.walk(game_folder):
        for name in files:
            if re.fullmatch(r"data\d*\.rda", name, re.IGNORECASE):
                archives.append(os.path.join(root, name))
    archives.sort(key=_data_rda_sort_key, reverse=True)
    if not archives:
        raise FileNotFoundError(os.path.join(game_folder, "data*.rda"))

    os.makedirs(output_folder, exist_ok=True)
    missing = set(ANNO1800_FILES)
    logs = []
    last_command, last_code = [], 0
    for archive in archives:
        if not missing:
            break
        wanted = sorted(missing)
        pattern = r"(?:^|[\\/])(" + "|".join(re.escape(name) for name in wanted) + r")$"
        command, code, output = extract_archive(app_dir, archive, output_folder, pattern, timeout)
        logs.append(f"Archive: {archive}\n{output}".strip())
        last_command, last_code = command, code
        if code not in (0, NET_CONSOLE_EXIT_CODE):
            continue
        # Only files physically present in the output count as found. Newer
        # archives are processed first, so older archives cannot overwrite them.
        extracted_names = {
            file_name
            for root, _dirs, files in os.walk(output_folder)
            for file_name in files
        }
        missing = {name for name in missing if name not in extracted_names}

    if missing:
        raise RuntimeError("Missing after extraction: " + ", ".join(sorted(missing)))
    _keep_only_data_config(output_folder)
    return last_command, last_code, "\n\n".join(logs)
