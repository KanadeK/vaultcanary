"""Manifest validation and semantic round-trip auditing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypeAlias
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from vaultcanary.adapters import DEFAULT_MAX_BYTES
from vaultcanary.model import NormalizedVault, Scalar

FeatureStatus: TypeAlias = Literal["preserved", "relocated", "missing"]


class AuditError(ValueError):
    """A manifest or return export does not identify one auditable canary run."""


@dataclass(frozen=True, slots=True)
class ManifestFeature:
    feature_id: str
    item_title: str
    expected_path: str
    expected_value: Scalar
    kind: str


@dataclass(frozen=True, slots=True)
class Manifest:
    run_id: str
    title_prefix: str
    features: tuple[ManifestFeature, ...]


@dataclass(frozen=True, slots=True)
class FeatureResult:
    feature_id: str
    status: FeatureStatus
    expected_path: str
    observed_path: str | None


@dataclass(frozen=True, slots=True)
class AuditReport:
    run_id: str
    format_name: str
    results: tuple[FeatureResult, ...]

    @property
    def preserved_count(self) -> int:
        return sum(result.status == "preserved" for result in self.results)

    @property
    def relocated_count(self) -> int:
        return sum(result.status == "relocated" for result in self.results)

    @property
    def missing_count(self) -> int:
        return sum(result.status == "missing" for result in self.results)

    @property
    def ok(self) -> bool:
        return self.preserved_count == len(self.results)


def load_manifest(path: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> Manifest:
    """Read and validate a schema-versioned synthetic manifest."""

    try:
        size = path.stat().st_size
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise AuditError(f"cannot read manifest: {path}") from error
    if size > max_bytes:
        raise AuditError(f"manifest is larger than {max_bytes} bytes")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AuditError("manifest is not valid JSON") from error
    if not isinstance(value, dict):
        raise AuditError("manifest root must be an object")
    if value.get("schema_version") != 1:
        raise AuditError("manifest schema_version must be 1")
    if value.get("synthetic_data") is not True:
        raise AuditError("manifest must declare synthetic_data=true")
    run_id = _nonempty_string(value.get("run_id"), "manifest run_id")
    title_prefix = _nonempty_string(value.get("title_prefix"), "manifest title_prefix")
    if title_prefix != f"VaultCanary {run_id} —":
        raise AuditError("manifest title_prefix does not match run_id")
    raw_features = value.get("features")
    if not isinstance(raw_features, list) or not raw_features:
        raise AuditError("manifest features must be a non-empty array")
    features: list[ManifestFeature] = []
    feature_ids: set[str] = set()
    for index, raw_feature in enumerate(raw_features):
        if not isinstance(raw_feature, dict):
            raise AuditError(f"manifest features[{index}] must be an object")
        feature_id = _nonempty_string(raw_feature.get("feature_id"), "feature_id")
        if feature_id in feature_ids:
            raise AuditError(f"duplicate manifest feature_id: {feature_id}")
        feature_ids.add(feature_id)
        item_title = _nonempty_string(raw_feature.get("item_title"), "item_title")
        if not item_title.startswith(title_prefix):
            raise AuditError(f"feature {feature_id} belongs to another run")
        expected_path = _nonempty_string(raw_feature.get("expected_path"), "expected_path")
        expected_value = raw_feature.get("expected_value")
        if not isinstance(expected_value, (str, bool)):
            raise AuditError(f"feature {feature_id} expected_value must be text or boolean")
        kind = _nonempty_string(raw_feature.get("kind"), "kind")
        if kind not in {"exact", "uri", "totp", "boolean"}:
            raise AuditError(f"feature {feature_id} has unsupported comparison kind")
        features.append(
            ManifestFeature(feature_id, item_title, expected_path, expected_value, kind)
        )
    return Manifest(run_id=run_id, title_prefix=title_prefix, features=tuple(features))


def audit_manifest(manifest: Manifest, vault: NormalizedVault) -> AuditReport:
    """Evaluate every manifest feature against one normalized return export."""

    if not vault.items:
        raise AuditError(f"return export contains no items for run {manifest.run_id}")
    try:
        items = vault.by_title
    except ValueError as error:
        raise AuditError(str(error)) from error
    results: list[FeatureResult] = []
    for feature in manifest.features:
        item = items.get(feature.item_title)
        if item is None:
            results.append(_missing(feature))
            continue
        observed = item.values.get(feature.expected_path)
        if observed is not None and _equivalent(feature.kind, feature.expected_value, observed):
            results.append(
                FeatureResult(
                    feature_id=feature.feature_id,
                    status="preserved",
                    expected_path=feature.expected_path,
                    observed_path=feature.expected_path,
                )
            )
            continue
        relocated_path = next(
            (
                path
                for path, value in sorted(item.values.items())
                if path != feature.expected_path
                and _equivalent(feature.kind, feature.expected_value, value)
            ),
            None,
        )
        if relocated_path is None:
            results.append(_missing(feature))
        else:
            results.append(
                FeatureResult(
                    feature_id=feature.feature_id,
                    status="relocated",
                    expected_path=feature.expected_path,
                    observed_path=relocated_path,
                )
            )
    return AuditReport(manifest.run_id, vault.format_name, tuple(results))


def _missing(feature: ManifestFeature) -> FeatureResult:
    return FeatureResult(feature.feature_id, "missing", feature.expected_path, None)


def _equivalent(kind: str, expected: Scalar, observed: Scalar) -> bool:
    if type(expected) is not type(observed):
        return False
    if not isinstance(expected, str) or not isinstance(observed, str):
        return expected == observed
    if kind == "uri":
        return _normalized_uri(expected) == _normalized_uri(observed)
    if kind == "totp":
        return _normalized_totp(expected) == _normalized_totp(observed)
    return expected == observed


def _normalized_uri(value: str) -> str:
    parsed = urlsplit(value)
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def _normalized_totp(value: str) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    parsed = urlsplit(value)
    query = tuple(sorted((key.casefold(), item) for key, item in parse_qsl(parsed.query)))
    return parsed.netloc.casefold(), parsed.path, query


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AuditError(f"{label} must be a non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise AuditError(f"{label} must not contain control characters")
    return value
