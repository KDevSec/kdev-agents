"""feature-name → filesystem-safe slug.

v0.1 strategy:
- Lowercase
- ASCII chars + digits + hyphen pass through
- Whitespace → hyphen
- Other chars (incl. Chinese) → stripped, but if any non-ASCII chars existed,
  append a 6-char hash suffix for stability.
- Collapse consecutive hyphens, strip leading/trailing
- Truncate to 64 chars
- Empty result → raise ValueError
"""
import hashlib
import re


_NON_ASCII = re.compile(r"[^\x00-\x7f]")


def slugify(name: str) -> str:
    if not name or not name.strip():
        raise ValueError("slug name must be non-empty")

    has_non_ascii = bool(_NON_ASCII.search(name))

    lowered = name.lower()
    # Replace any non-ASCII-alphanumeric run with hyphen
    ascii_only = re.sub(r"[^a-z0-9]+", "-", lowered)
    # Strip leading/trailing hyphens, collapse consecutives
    cleaned = re.sub(r"-+", "-", ascii_only).strip("-")

    if has_non_ascii:
        # Use 8-char hash when there is no ASCII portion (ensures >= 8 chars);
        # use 6-char hash when appended as a suffix to existing ASCII content.
        if cleaned:
            digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
            cleaned = f"{cleaned}-{digest}"
        else:
            digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
            cleaned = digest

    if not cleaned:
        raise ValueError(f"slug result empty for input {name!r}")

    return cleaned[:64]
