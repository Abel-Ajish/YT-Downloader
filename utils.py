import re
import os

def sanitize_filename(name: str, replacement: str = "_", max_length: int = 200) -> str:
    """Return a filesystem-safe filename derived from `name`.

    - Removes control characters and characters forbidden on Windows and most filesystems.
    - Replaces path separators with `replacement` and collapses runs of replacements.
    - Strips leading/trailing whitespace and leading dots to avoid hidden files or traversal.
    - Truncates to `max_length` (preserves extension handling should be done by caller).
    """
    if not isinstance(name, str):
        name = str(name)

    # Normalize whitespace
    name = name.strip()

    # Remove control characters
    name = re.sub(r"[\x00-\x1f\x7f]+", "", name)

    # Replace forbidden characters with replacement
    forbidden_pattern = r"[<>:\"/\\|?*]"
    name = re.sub(forbidden_pattern, replacement, name)

    # Replace any remaining path separators
    name = name.replace(os.path.sep, replacement)

    # Collapse multiple replacements into one
    rep_escaped = re.escape(replacement)
    name = re.sub(rf"{rep_escaped}+", replacement, name)

    # Remove leading dots (avoid hidden files or relative paths)
    name = re.sub(r"^\.+", "", name)

    # Trim to max length
    if len(name) > max_length:
        name = name[:max_length].rstrip()

    # If name becomes empty, return a safe default
    if not name:
        return "untitled"

    return name

def safe_join(base_dir: str, filename: str) -> str:
    """Join base_dir and filename ensuring the result is inside base_dir.

    Raises ValueError if the resolved path escapes base_dir.
    """
    base_dir = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base_dir, filename))
    if os.path.commonpath([base_dir, candidate]) != base_dir:
        raise ValueError("Attempted path traversal in filename")
    return candidate
