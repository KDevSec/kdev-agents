"""AR-{DOMAIN}-{MAJOR}.{MINOR}.{PATCH} format validator. v0.1 §3.1."""
from __future__ import annotations
from dataclasses import dataclass
import re

_PATTERN = re.compile(r"^AR-([A-Z][A-Z0-9_]*)-(\d{1,2})\.(\d{3})\.(\d{3})$")


class ArInvalid(ValueError):
    pass


@dataclass(frozen=True)
class Ar:
    domain: str
    major: int
    minor: int
    patch: int

    @property
    def canonical(self) -> str:
        return f"AR-{self.domain}-{self.major:02d}.{self.minor:03d}.{self.patch:03d}"


def parse_ar(s: str) -> Ar:
    m = _PATTERN.match(s or "")
    if not m:
        raise ArInvalid(f"not a valid AR number: {s!r}")
    return Ar(domain=m.group(1), major=int(m.group(2)), minor=int(m.group(3)), patch=int(m.group(4)))


def is_valid_ar(s: str) -> bool:
    try:
        parse_ar(s)
        return True
    except ArInvalid:
        return False
