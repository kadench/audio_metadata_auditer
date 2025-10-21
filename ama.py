"""
Audio Metadata Auditer (ama.py)

Return an overall health report of all audio files in a given folder. I haven't tested all audio formats, so I cannot guarantee full compatibility, but it should work with most common formats supported by Mutagen. Feel free to modify and distribute this code as you see fit. Please attribute.

Usage:
    python ama.py --folder <path> [--to-file] [--terminal] [--output-path <file>] [--copy]
                   [--debug] [--max-depth <n>] [--per-album] [--no-quick-stats]

Authors: kadench, ChatGPT 5

License: MIT

Requirements:
- Python 3.10 or newer
- Mutagen library (`pip install mutagen`)

*tests are provided in `ama_unittest.py` from ChatGPT. If you don't have python, you can run the .exe version instead.*
"""

import os
import sys
import argparse
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
from decimal import Decimal, ROUND_HALF_UP
import pyperclip

from mutagen import File
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3, error as ID3Error, ID3NoHeaderError
from mutagen.flac import FLAC, Picture
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE


SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".oga", ".opus", ".wav", ".m4a", ".aac"}


def initialize_parser(default_output: str) -> argparse.ArgumentParser:
    """
    Initialize the argument parser.
    Args:
        default_output (str): Default output file path.
    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Return an overall health report of all audio files in a given folder.",
        epilog=(
            "Examples:\n"
            "  python scan_music.py --folder . --terminal\n"
            "  python scan_music.py -f /path/to/music --to-file --output-path ./out.txt\n"
            "  python scan_music.py -f ./Album --copy --debug\n"
            "  python scan_music.py -f ./Lib -pa         # per-album extra info (duration/size)\n"
            "  python scan_music.py -f ./Lib -nqs        # hide global quick stats\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--folder", "-f", type=str, required=True, help="Path of the folder to scan.")
    parser.add_argument("--to-file", "-tf", action="store_true", help="Save results to a file.")
    parser.add_argument("--terminal", "-t", action="store_true", help="Print results to the terminal.")
    parser.add_argument("--output-path", "-op", type=str, default=str(default_output), help="File path to save results to.")
    parser.add_argument("--copy", "-c", action="store_true", help="Copy results to clipboard.")
    parser.add_argument("--debug", "-d", action="store_true", help="Include a debug section at the end.")
    parser.add_argument("--max-depth", "-md", type=int, default=5, help="Maximum subfolder depth to scan (default 5).")
    parser.add_argument("--per-album", "-pa", action="store_true", help="Show per-album duration and size on the header line.")
    parser.add_argument("--no-quick-stats", "-nqs", action="store_true", help="Hide the global quick stats line (the line under the health bar).")
    return parser


def load_audio(file_path: str):
    """
    Load an audio file and return its metadata.
    Args:
        file_path (str): Path to the audio file.
    Returns:
        tuple: (audio_object, info_object, tags_object). Returns (None, None, None) if unrecognized.
    """
    audio_object = File(file_path)  # Mutagen auto-detects type and exposes .info and .tags
    if audio_object is None:
        return None, None, None
    return audio_object, getattr(audio_object, "info", None), getattr(audio_object, "tags", None)


def sha1_of_file(file_path: str, chunk_size: int = 1024 * 1024) -> str | None:
    """
    Compute a SHA-1 hash of the entire file content.
    Args:
        file_path (str): Path to the file.
    Returns:
        str | None: Hex digest of the file content or None on failure.
    """
    try:
        hasher = hashlib.sha1()
        with open(file_path, "rb") as file_handle:
            while True:
                chunk = file_handle.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def sha1_of_bytes(data: bytes | None) -> str | None:
    """
    Compute a SHA-1 hash of bytes.
    Args:
        data (bytes | None): Input bytes.
    Returns:
        str | None: Hex digest or None if no data.
    """
    if not data:
        return None
    return hashlib.sha1(data).hexdigest()


def parse_track_number(tags_map: dict) -> tuple[int | None, int | None]:
    """
    Parse track number and total from tag map.
    Args:
        tags_map (dict): Tag key to value list mapping.
    Returns:
        tuple: (track_number, track_total) integers or None.
    """
    raw_value = None
    if "TRCK" in tags_map and tags_map["TRCK"]:
        raw_value = tags_map["TRCK"][0]
    elif "TRACKNUMBER" in tags_map and tags_map["TRACKNUMBER"]:
        raw_value = tags_map["TRACKNUMBER"][0]
    if not raw_value:
        return None, None
    raw_string = str(raw_value).strip()
    if "/" in raw_string:
        left_part, right_part = raw_string.split("/", 1)
        return safe_int(left_part), safe_int(right_part)
    return safe_int(raw_string), None


def safe_int(value) -> int | None:
    """
    Convert a value to int, returning None on failure.
    Args:
        value (any): Value to convert.
    Returns:
        int | None: Converted int or None.
    """
    try:
        return int(str(value).strip())
    except Exception:
        return None


def canonicalize_string(value: str) -> str:
    """
    Canonicalize a string for comparison (lowercased, trimmed, single-spaced).
    Args:
        value (str): Input string.
    Returns:
        str: Canonicalized string.
    """
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def format_bytes(num_bytes: int) -> str:
    """
    Format a byte count into B, KB, MB, GB, TB using two-decimal rounding (half-up).
    Args:
        num_bytes (int): Size in bytes.
    Returns:
        str: Human-readable size string.
    """
    units = ["B", "KB", "MB", "GB", "TB"]
    size_value = Decimal(num_bytes)
    unit_index = 0
    while size_value >= 1024 and unit_index < len(units) - 1:
        size_value = (size_value / Decimal(1024))
        unit_index += 1
    return f"{Decimal(size_value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)} {units[unit_index]}"


def format_duration_total(total_seconds: float | int) -> str:
    """
    Format a total duration with scaled units:
    - seconds only if under 60s
    - minutes+seconds if under 60min
    - hours+minutes+seconds if under 24h
    - days+hours+minutes if under 7d
    - weeks+days+hours if under 30d
    - months+days if under 365d (30d month)
    - years+months if 365d or more
    Args:
        total_seconds (float | int): Duration in seconds.
    Returns:
        str: Human-readable duration.
    """
    seconds_int = int(Decimal(total_seconds).to_integral_value(rounding=ROUND_HALF_UP))
    if seconds_int < 60:
        return f"{seconds_int}s"
    minutes_int, seconds_int = divmod(seconds_int, 60)
    if minutes_int < 60:
        return f"{minutes_int}m {seconds_int}s"
    hours_int, minutes_int = divmod(minutes_int, 60)
    if hours_int < 24:
        return f"{hours_int}h {minutes_int}m {seconds_int}s"
    days_int, hours_int = divmod(hours_int, 24)
    if days_int < 7:
        return f"{days_int}d {hours_int}h {minutes_int}m"
    weeks_int, days_int = divmod(days_int, 7)
    if weeks_int < 4:
        return f"{weeks_int}w {days_int}d {hours_int}h"
    months_int, days_int = divmod(days_int, 30)
    if months_int < 12:
        return f"{months_int}mo {days_int}d"
    years_int, months_int = divmod(months_int, 12)
    return f"{years_int}y {months_int}mo"


def first_value(values: list[str] | None) -> str:
    """
    Safely return first value of a list or empty string.
    Args:
        values (list[str] | None): Values list.
    Returns:
        str: First string or empty.
    """
    if isinstance(values, list) and values:
        return values[0]
    return ""


def first_tag_text(tags_map: dict, keys: list[str]) -> str:
    """
    Return the first available text value for the first matching key in keys.
    The tags_map values are expected to be lists (mutagen style).
    """
    for k in keys:
        v = tags_map.get(k)
        if isinstance(v, list) and v:
            return str(v[0])
    return ""


def to_uniform_dict(file_path: str) -> dict:
    """
    Convert any supported audio file into a uniform dictionary for comparisons and reporting.
    Args:
        file_path (str): Path to the audio file.
    Returns:
        dict: Dictionary with path, container, stream fields, album-wide fields, and hashes.
    """
    file_name = Path(file_path).name
    file_size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    content_hash = sha1_of_file(file_path)  # for duplicate detection

    audio_object = None
    info_object = None
    tags_object = None
    artwork_hashes = set()
    id3_version_string = None

    try:
        audio_object, info_object, tags_object = load_audio(file_path)
    except (HeaderNotFoundError, ID3NoHeaderError, ID3Error):
        return {
            "path": file_path,
            "file_name": file_name,
            "error": "mp3_unreadable",
            "content_hash": content_hash,
            "size_bytes": file_size_bytes,
        }
    except Exception:
        return {
            "path": file_path,
            "file_name": file_name,
            "error": "unreadable",
            "content_hash": content_hash,
            "size_bytes": file_size_bytes,
        }

    if audio_object is None:
        return {
            "path": file_path,
            "file_name": file_name,
            "error": "unrecognized",
            "content_hash": content_hash,
            "size_bytes": file_size_bytes,
        }

    container_name = audio_object.__class__.__name__.lower()
    length_seconds = getattr(info_object, "length", None)
    sample_rate_hz = getattr(info_object, "sample_rate", None)
    channel_count = getattr(info_object, "channels", None)
    bitrate_value = getattr(info_object, "bitrate", None)

    tags_map = {}
    if isinstance(audio_object, MP3) and isinstance(tags_object, ID3):
        for frame_identifier in ("TIT2", "TALB", "TPE1", "TPE2", "TRCK", "TPOS", "TCON", "TDRC"):
            if frame_identifier in tags_object:
                frame_object = tags_object.get(frame_identifier)
                tags_map[frame_identifier] = getattr(frame_object, "text", [str(frame_object)])
        for apic_frame in tags_object.getall("APIC"):
            artwork_hashes.add(sha1_of_bytes(getattr(apic_frame, "data", None)))
        id3_version_tuple = getattr(tags_object, "version", None)
        if isinstance(id3_version_tuple, tuple) and len(id3_version_tuple) == 3:
            id3_version_string = ".".join(str(part) for part in id3_version_tuple)
        else:
            id3_version_string = str(id3_version_tuple) if id3_version_tuple is not None else None

    elif isinstance(audio_object, WAVE):
        if isinstance(tags_object, ID3):
            for frame_identifier in ("TIT2", "TALB", "TPE1", "TPE2", "TRCK", "TPOS", "TCON", "TDRC"):
                if frame_identifier in tags_object:
                    frame_object = tags_object.get(frame_identifier)
                    tags_map[frame_identifier] = getattr(frame_object, "text", [str(frame_object)])
            id3_version_tuple = getattr(tags_object, "version", None)
            if isinstance(id3_version_tuple, tuple) and len(id3_version_tuple) == 3:
                id3_version_string = ".".join(str(part) for part in id3_version_tuple)
            else:
                id3_version_string = str(id3_version_tuple) if id3_version_tuple is not None else None

    elif isinstance(audio_object, FLAC):
        for key_name in ("TITLE", "ALBUM", "ARTIST", "ALBUMARTIST", "TRACKNUMBER", "TRACKTOTAL", "DATE", "GENRE"):
            if key_name in audio_object:
                tags_map[key_name] = list(audio_object.get(key_name, []))
        for picture in getattr(audio_object, "pictures", []):
            artwork_hashes.add(sha1_of_bytes(getattr(picture, "data", None)))

    elif isinstance(audio_object, OggVorbis):
        for key_name in ("TITLE", "ALBUM", "ARTIST", "ALBUMARTIST", "TRACKNUMBER", "TRACKTOTAL", "DATE", "GENRE"):
            if key_name in audio_object:
                tags_map[key_name] = list(audio_object.get(key_name, []))
        for base64_payload in audio_object.get("metadata_block_picture", []):
            try:
                import base64
                picture_object = Picture()
                picture_object.from_data(base64.b64decode(base64_payload))
                artwork_hashes.add(sha1_of_bytes(getattr(picture_object, "data", None)))
            except Exception:
                pass
    else:
        if hasattr(tags_object, "keys"):
            tags_map = {key_name: list(tags_object.get(key_name, [])) for key_name in tags_object.keys()}

    # Extract strings (not lists)
    title_text = first_tag_text(tags_map, ["TIT2", "TITLE"])
    album_text = first_tag_text(tags_map, ["TALB", "ALBUM"])
    artist_text = first_tag_text(tags_map, ["TPE1", "ARTIST"])
    track_number, track_total = parse_track_number(tags_map)

    return {
        "path": file_path,
        "file_name": file_name,
        "container": container_name,
        "length_s": length_seconds,
        "sample_rate": sample_rate_hz,
        "channels": channel_count,
        "bitrate": bitrate_value,
        "tags": tags_map,
        "title": title_text,
        "album": album_text,
        "artist": artist_text,
        "track_number": track_number,
        "track_total": track_total,
        "id3_version": id3_version_string,
        "artwork_hashes": {hash_value for hash_value in artwork_hashes if hash_value},
        "content_hash": content_hash,
        "size_bytes": file_size_bytes,
    }


def scan_count_total_candidates(root: str, max_depth: int) -> int:
    """
    Count how many files are eligible for scanning (by extension) within depth.
    Args:
        root (str): Root directory path.
    max_depth (int): Maximum recursion depth.
    Returns:
        int: Number of candidate files to scan.
    """
    total = 0

    def should_consider(name_or_path: str) -> bool:
        extension = Path(name_or_path).suffix.lower()
        return extension in SUPPORTED_EXTENSIONS

    def walk(current_dir: str, current_depth: int):
        nonlocal total
        try:
            with os.scandir(current_dir) as directory_iterator:
                for directory_entry in directory_iterator:
                    if directory_entry.is_file():
                        if should_consider(directory_entry.name):
                            total += 1
                    elif directory_entry.is_dir():
                        if current_depth < max_depth:
                            walk(directory_entry.path, current_depth + 1)
        except FileNotFoundError:
            pass

    walk(root, 0)
    return total


def scan_folder_for_audio_recursive(root: str, max_depth: int, debug_enabled: bool, show_progress: bool) -> tuple[list[dict], list[str]]:
    """
    Recursively scan for audio files up to a maximum depth and collect uniform metadata dictionaries.
    Also prints a simple progress bar (made of '=') to the terminal when show_progress is True.
    Args:
        root (str): Root directory to scan.
        max_depth (int): Maximum subfolder depth to scan.
    Returns:
        tuple: (results, debug_lines) where results is a list of uniform dicts for recognized audio
               files, and debug_lines is a list of debug strings when debug is enabled.
    """
    results = []
    debug_lines = []

    total_candidates = scan_count_total_candidates(root, max_depth)
    processed_candidates = 0
    progress_bar_width = 40  # number of '=' max in the bar

    def update_progress():
        if not show_progress or total_candidates == 0:
            return
        filled = int(progress_bar_width * processed_candidates / total_candidates)
        bar = "=" * filled + "." * (progress_bar_width - filled)
        # Carriage return keeps it on one line; flush for immediate repaint
        sys.stdout.write(f"\rScanning: [{bar}] {processed_candidates}/{total_candidates}")
        sys.stdout.flush()

    def finish_progress_line():
        if not show_progress or total_candidates == 0:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()

    def should_consider(name_or_path: str) -> bool:
        extension = Path(name_or_path).suffix.lower()
        return extension in SUPPORTED_EXTENSIONS

    def walk_dir(current_dir: str, current_depth: int):
        nonlocal processed_candidates
        if debug_enabled:
            debug_lines.append(f"[debug] entering: {current_dir} (depth={current_depth})")
        try:
            with os.scandir(current_dir) as directory_iterator:
                for directory_entry in directory_iterator:
                    try:
                        if directory_entry.is_file():
                            if should_consider(directory_entry.name):
                                file_info = to_uniform_dict(directory_entry.path)
                                results.append(file_info)
                                processed_candidates += 1
                                update_progress()
                        elif directory_entry.is_dir():
                            if current_depth < max_depth:
                                walk_dir(directory_entry.path, current_depth + 1)
                            else:
                                if debug_enabled:
                                    debug_lines.append(f"[debug] depth limit reached at: {directory_entry.path}")
                    except (HeaderNotFoundError, ID3NoHeaderError, ID3Error):
                        results.append({
                            "path": directory_entry.path,
                            "file_name": Path(directory_entry.path).name,
                            "error": "mp3_unreadable"
                        })
                        processed_candidates += 1
                        update_progress()
                        if debug_enabled:
                            debug_lines.append(f"[debug] mp3_unreadable: {directory_entry.path}")
                    except Exception:
                        results.append({
                            "path": directory_entry.path,
                            "file_name": Path(directory_entry.path).name,
                            "error": "unreadable"
                        })
                        processed_candidates += 1
                        update_progress()
                        if debug_enabled:
                            debug_lines.append(f"[debug] unreadable: {directory_entry.path}")
        except FileNotFoundError:
            if debug_enabled:
                debug_lines.append(f"[debug] not found: {current_dir}")

    update_progress()
    walk_dir(root, 0)
    finish_progress_line()

    results.sort(key=lambda info: info.get("file_name", "").lower())
    return results, debug_lines


def group_by_album(file_infos: list[dict]) -> dict:
    """
    Primary: group by containing folder (when 'path' is present).
    Fallback: if no 'path' in items, group by album tag like before,
              using 'unknown' for empty/None/whitespace.
    """
    albums_by_key = defaultdict(list)

    # Detect whether we have paths at all
    has_any_path = any("path" in fi and fi.get("path") for fi in file_infos)

    if has_any_path:
        # Folder-based grouping (keeps prior WARN checks meaningful)
        for fi in file_infos:
            if "error" in fi:
                albums_by_key["__errors__"].append(fi)
                continue
            parent = Path(fi.get("path", "")).parent
            parent_key = canonicalize_string(str(parent)) or "unknown_dir"
            albums_by_key[parent_key].append(fi)
        return dict(albums_by_key)

    # Fallback: tag-based grouping (to satisfy legacy tests)
    for fi in file_infos:
        if "error" in fi:
            albums_by_key["__errors__"].append(fi)
            continue
        album_raw = fi.get("album", "") or ""
        key = canonicalize_string(album_raw) or "unknown"
        albums_by_key[key].append(fi)

    return dict(albums_by_key)


def resolve_display_album(album_files: list[dict], album_key: str) -> str:
    """
    Resolve a human-friendly album name to display.
    Args:
        album_files (list[dict]): Files in the album.
        album_key (str): Canonical album key.
    Returns:
        str: Display album name.
    """
    raw_names = [fi.get("album", "") for fi in album_files if fi.get("album")]
    if raw_names:
        return Counter(raw_names).most_common(1)[0][0]
    return "Unknown Album"


def resolve_display_artist(album_files: list[dict]) -> str:
    """
    Resolve a human-friendly album artist to display (most common artist tag).
    """
    raw_artists = [fi.get("artist", "") for fi in album_files if fi.get("artist")]
    if raw_artists:
        return Counter(raw_artists).most_common(1)[0][0]
    return "Unknown Artist"


def build_album_messages(album_files: list[dict]) -> tuple[str | None, list[str], int, int]:
    """
    Determine the album severity level (CRIT/WARN/INFO) and produce human sentences.
    Returns:
        (level, messages, total_seconds, total_size_bytes)
        - level is 'CRIT', 'WARN', 'INFO', or None if no issues.
        - messages is a list of plain-English sentences (no codes).
        - totals are for optional -pa display.
    Policy:
        * If WARN exists, drop INFO (no need for INFO if WARN trumps it).
        * If CRIT exists, keep WARN (and drop INFO).
    """
    total_seconds = sum(fi.get("length_s") or 0 for fi in album_files)
    total_size_bytes = sum(fi.get("size_bytes", 0) for fi in album_files)

    info_msgs: list[str] = []
    warn_msgs: list[str] = []
    crit_msgs: list[str] = []

    # 1) Multiple file formats present (INFO)
    extensions_in_album = sorted({Path(fi["file_name"]).suffix.lower() for fi in album_files})
    if len(extensions_in_album) > 1:
        info_msgs.append(f"There are multiple file formats found in this album: {', '.join(extensions_in_album)}.")

    # 2) Duplicate audio content by hash (WARN)
    files_by_hash = defaultdict(list)
    for fi in album_files:
        ch = fi.get("content_hash")
        if ch:
            files_by_hash[ch].append(fi)

    all_groups = list(files_by_hash.values())
    duplicate_groups = [g for g in all_groups if len(g) > 1]
    if duplicate_groups:
        shown = 0
        for grp in duplicate_groups:
            if shown >= 3:
                break
            rep = grp[0]["file_name"]
            warn_msgs.append(
                f"Duplicate audio content detected, for example: {rep} (+{len(grp) - 1} more in that group)."
            )
            shown += 1
        remaining_groups = len(all_groups) - shown
        if remaining_groups > 0:
            warn_msgs.append(f"There are {remaining_groups} more duplicate group(s) not shown.")

    # 3) Album name consistency (WARN)
    album_variants = Counter([fi.get("album", "") for fi in album_files if fi.get("album")])
    if len([name for name in album_variants if name]) > 1:
        warn_msgs.append("Tracks in this album do not all share the same album name.")

    # 4) Artist consistency (WARN)
    artist_variants = Counter([fi.get("artist", "") for fi in album_files if fi.get("artist")])
    if len([name for name in artist_variants if name]) > 1:
        warn_msgs.append("Tracks in this album do not all share the same artist.")

    # 5) Artwork presence and uniformity (WARN)
    tracks_without_art = []
    art_hashes_per_track = []
    for fi in album_files:
        hs = fi.get("artwork_hashes") or set()
        first_hash = next(iter(hs), None)
        art_hashes_per_track.append(first_hash)
        if first_hash is None:
            if fi.get("track_number") is not None:
                tracks_without_art.append(str(fi.get("track_number")))
            else:
                tracks_without_art.append(fi.get("file_name"))
    if tracks_without_art and len(tracks_without_art) < len(album_files):
        warn_msgs.append(f"The following tracks do not have an album cover: {', '.join(tracks_without_art)}.")
    art_present_hashes = [h for h in art_hashes_per_track if h is not None]
    if len(set(art_present_hashes)) > 1:
        warn_msgs.append("Cover artwork differs across tracks in this album.")

    # 6) Sample rate and channel count consistency (WARN)
    sample_rates = [fi.get("sample_rate") for fi in album_files if fi.get("sample_rate")]
    if sample_rates and len(set(sample_rates)) > 1:
        warn_msgs.append(
            f"Tracks use multiple sample rates in this album: {', '.join(str(r) for r in sorted(set(sample_rates)))}."
        )
    channels = [fi.get("channels") for fi in album_files if fi.get("channels") is not None]
    if channels and len(set(channels)) > 1:
        warn_msgs.append(
            f"Tracks use multiple channel counts in this album: {', '.join(str(c) for c in sorted(set(channels)))}."
        )

    # 7) ID3 validation (WARN)
    id3_versions = [fi.get("id3_version") for fi in album_files if fi.get("id3_version")]
    if id3_versions:
        if len(set(id3_versions)) > 1:
            warn_msgs.append(
                f"ID3 versions are not consistent across tracks: {', '.join(sorted(set(v for v in id3_versions if v)))}."
            )
        invalid_versions = [v for v in id3_versions if v not in {"2.3.0", "2.4.0"}]
        if invalid_versions:
            warn_msgs.append(
                f"Some tracks use non-standard ID3 versions: {', '.join(sorted(set(invalid_versions)))}."
            )

    # 8) Critical unreadable MP3s (CRIT)
    crit_count = 0
    for fi in album_files:
        if fi.get("container") == "mp3" and (fi.get("error") == "mp3_unreadable" or fi.get("length_s") is None):
            crit_count += 1
    if crit_count:
        crit_msgs.append(f"{crit_count} MP3 file(s) appear unreadable or invalid.")

    # Select level + prune INFO if WARN/CRIT exists
    if crit_msgs:
        level = "CRIT"
        messages = warn_msgs + crit_msgs
    elif warn_msgs:
        level = "WARN"
        messages = warn_msgs
    elif info_msgs:
        level = "INFO"
        messages = info_msgs
    else:
        return None, [], total_seconds, total_size_bytes

    return level, messages, total_seconds, total_size_bytes


def _render_health_bar(health_percent: int, width: int = 40) -> str:
    """
    Render a simple ASCII health bar like the scan progress bar.
    """
    health_percent = max(0, min(100, int(health_percent)))
    filled = int(width * health_percent / 100)
    bar = "=" * filled + "." * (width - filled)
    return f"Health: [{bar}] {health_percent}%"


def get_output(root: str, debug_enabled: bool, max_depth: int, per_album: bool, no_quick_stats: bool, show_progress: bool) -> str:
    """
    Scan the music library (recursively) and return a compact, file-friendly report.
    Args:
        root (str): Root directory to scan.
        debug_enabled (bool): Whether to include debug lines in the output.
        max_depth (int): Maximum subfolder depth to scan.
        per_album (bool): Whether to include per-album duration and size on the header line.
        no_quick_stats (bool): Whether to hide global quick stats.
        show_progress (bool): Whether to paint a textual progress bar while scanning.
    Returns:
        str: Formatted report as a single string.
    """
    # Title line uses the actual folder path for clarity
    header_title = f"\n\"{root}\" Library Scan"

    # Perform the scan (progress bar shown only when printing to terminal)
    file_infos, debug_lines = scan_folder_for_audio_recursive(root, max_depth, debug_enabled, show_progress)

    recognized_files = [file_info for file_info in file_infos if "error" not in file_info]
    if not recognized_files:
        return "Couldn't find any music files with current parameters.\n"

    # Group by album/folder and keep stable order by display name
    albums_by_key = group_by_album(recognized_files)
    ordered_album_keys = sorted(
        albums_by_key.keys(),
        key=lambda album_key: resolve_display_album(albums_by_key[album_key], album_key).lower()
    )

    # First pass over albums to compute levels/messages for health scoring and later rendering
    computed_per_album = {}
    warn_albums = 0
    crit_albums = 0
    for album_key in ordered_album_keys:
        album_files = albums_by_key[album_key]
        level, messages, album_seconds, album_size_bytes = build_album_messages(album_files)
        computed_per_album[album_key] = (level, messages, album_seconds, album_size_bytes)
        if level == "CRIT":
            crit_albums += 1
        elif level == "WARN":
            warn_albums += 1

    total_albums = len(ordered_album_keys)
    total_tracks = len(recognized_files)
    total_size_bytes = sum(file_info.get("size_bytes", 0) for file_info in recognized_files)
    total_length_seconds = sum(file_info.get("length_s") or 0 for file_info in recognized_files)

    # Compute an overall health score out of 100% based on album severities (CRIT weighs double)
    # Health = 100% when no WARN/CRIT. Each WARN deducts 1 unit; each CRIT deducts 2 units, normalized by (2*total_albums).
    if total_albums > 0:
        penalty_units = warn_albums + 2 * crit_albums
        max_units = 2 * total_albums
        health_percent = int(round(100 * (1 - (penalty_units / max_units))))
    else:
        health_percent = 100

    health_line = _render_health_bar(health_percent)

    quick_line = (
        f"Albums: {total_albums}  "
        f"Tracks: {total_tracks}  "
        f"Size: {format_bytes(total_size_bytes)}  "
        f"Duration: {format_duration_total(total_length_seconds)}"
    )

    # Header and global quick stats + health bar
    output_lines = [header_title]

    if not no_quick_stats:
        # Separator lines must match the size of the quick stats (nqs) line
        sep_len = len(quick_line)
        sep = "=" * sep_len
        output_lines.append(sep)
        # Health bar should appear BEFORE the quick stats line
        output_lines.append(health_line)
        output_lines.append(quick_line)
        output_lines.append(sep)
        output_lines.append(f"\n")
    else:
        # When quick stats are hidden, use a separator matching the title length (top only here)
        sep_len = len(header_title)
        output_lines.append("=" * len(health_line))
        # Still show the health bar even when quick stats are hidden
        output_lines.append(health_line)
        output_lines.append("=" * len(health_line))
        output_lines.append(f"\n")

    # Build per-album sections. Only print albums that have at least one message.
    album_blocks = []

    for album_key in ordered_album_keys:
        album_files = albums_by_key[album_key]
        display_album_name = resolve_display_album(album_files, album_key)
        display_artist_name = resolve_display_artist(album_files)

        level, messages, album_seconds, album_size_bytes = computed_per_album[album_key]
        if level is None:
            continue  # skip albums with no messages

        # Build the album header line with exactly one level tag.
        if level == "CRIT":
            level_tag = f"[CRIT]"
        elif level == "WARN":
            level_tag = f"[WARN]"
        else:
            level_tag = f"[INFO]"

        if per_album:
            header_line = (
                f"{level_tag} {display_album_name} ({display_artist_name}) | Duration: "
                f"{format_duration_total(album_seconds)}, Size {format_bytes(album_size_bytes)}"
            )
        else:
            header_line = f"{level_tag} {display_album_name} ({display_artist_name}):"

        # Add a newline *after each album message block*
        block_lines = [header_line] + [f"    - {s}" for s in messages]
        album_blocks.append("\n".join(block_lines) + "\n")

    # If no albums produced messages, say so clearly
    if not album_blocks:
        # For symmetry, add a bottom separator if quick stats were hidden (match title length)
        if no_quick_stats:
            output_lines.append("=" * len(header_title))
        output_lines.append("No warnings, critical issues, or informational notes were detected.")
        if debug_enabled and debug_lines:
            output_lines.append("")
            output_lines.append("Debug")
            output_lines.extend(debug_lines)
        return "\n".join(output_lines) + "\n"

    # Print album issue blocks
    output_lines.extend(album_blocks)

    # Add a simple multi-line legend to help non-savvy readers (human wording, not codes)
    output_lines.append("")
    output_lines.append("Legend")
    output_lines.append("  [CRIT] Serious problems that likely prevent proper playback or visibility.")
    output_lines.append("  [WARN] Inconsistencies that may cause confusion or uneven playback/organization.")
    output_lines.append("  [INFO] Helpful notes that are not problems (for example, multiple file formats).")

    # Optional debug appendix
    if debug_enabled and debug_lines:
        output_lines.append("")
        output_lines.append("Debug")
        output_lines.extend(debug_lines)

    return "\n".join(output_lines) + "\n"

def main():
    # Build the default output path alongside the script
    default_dir = Path(__file__).resolve().parent
    default_output = default_dir / "output.txt"

    # Parse command-line arguments
    parser = initialize_parser(str(default_output))
    args = parser.parse_args()

    # Validate the input folder early to avoid confusing errors later
    root = os.path.abspath(args.folder)
    if not os.path.isdir(root):
        print(f"Error: '{args.folder}' is not a valid directory.")
        raise SystemExit(1)

    # We only show a progress bar when printing to the terminal (to avoid polluting files/clipboard)
    show_progress = bool(args.terminal)

    # Generate the report text
    output_text = get_output(
        root=root,
        debug_enabled=args.debug,
        max_depth=args.max_depth,
        per_album=args.per_album,
        no_quick_stats=args.no_quick_stats,
        show_progress=show_progress,
    )

    # Save to file if requested
    if args.to_file:
        output_file_path = Path(args.output_path)
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        if output_file_path.exists():
            print(f"Error: Output file '{output_file_path}' already exists.")
            raise SystemExit(1)
        with open(output_file_path, "w", encoding="utf-8") as out_handle:
            out_handle.write(output_text)
        print(f"File written to: {output_file_path}")

    # Copy to clipboard if requested
    if args.copy:
        pyperclip.copy(output_text)
        print("Music scan results copied to clipboard.")

    # Print to terminal if requested, or when no sink was chosen
    if args.terminal or (not args.to_file and not args.copy):
        print(output_text, end="")


if __name__ == "__main__":
    main()