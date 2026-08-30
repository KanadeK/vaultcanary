"""Small normalized domain model shared by export adapters and the audit engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

Scalar: TypeAlias = str | bool


@dataclass(frozen=True, slots=True)
class NormalizedItem:
    """One exported item represented by stable semantic paths."""

    title: str
    item_type: str
    values: dict[str, Scalar]


@dataclass(frozen=True, slots=True)
class NormalizedVault:
    """The canary-relevant subset of one return export."""

    format_name: str
    items: tuple[NormalizedItem, ...]

    @property
    def by_title(self) -> dict[str, NormalizedItem]:
        """Index items by exact title, rejecting ambiguous duplicate canaries."""

        indexed: dict[str, NormalizedItem] = {}
        for item in self.items:
            if item.title in indexed:
                raise ValueError(f"duplicate exported item title: {item.title}")
            indexed[item.title] = item
        return indexed
