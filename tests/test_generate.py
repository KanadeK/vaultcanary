from __future__ import annotations

import json
from pathlib import Path

from vaultcanary.generate import build_bundle, write_bundle


def test_seeded_bundle_is_deterministic_and_covers_the_feature_contract() -> None:
    first = build_bundle(seed="demo-seed")
    second = build_bundle(seed="demo-seed")

    assert first == second
    assert first.manifest["schema_version"] == 1
    assert first.probe["encrypted"] is False
    assert {item["type"] for item in first.probe["items"]} == {1, 2, 3, 4}
    assert {feature["feature_id"] for feature in first.manifest["features"]} == {
        "card.cardholder",
        "card.number",
        "custom.boolean",
        "custom.hidden",
        "custom.text",
        "favorite.status",
        "folder.assignment",
        "identity.address",
        "identity.email",
        "login.notes",
        "login.password",
        "login.title",
        "login.totp",
        "login.uri",
        "login.username",
        "secure_note.body",
        "unicode.roundtrip",
    }


def test_generated_probe_contains_only_reserved_network_locations() -> None:
    bundle = build_bundle(seed="network-safety")
    serialized = json.dumps(bundle.probe, ensure_ascii=False)

    assert "https://" in serialized
    assert ".example.invalid" in serialized
    assert ".com" not in serialized
    assert bundle.manifest["synthetic_data"] is True


def test_write_bundle_produces_identical_bytes_for_the_same_seed(tmp_path: Path) -> None:
    first = write_bundle(tmp_path / "first", seed="stable")
    second = write_bundle(tmp_path / "second", seed="stable")

    assert first.probe_path.read_bytes() == second.probe_path.read_bytes()
    assert first.manifest_path.read_bytes() == second.manifest_path.read_bytes()
    assert first.instructions_path.read_bytes() == second.instructions_path.read_bytes()


def test_unseeded_bundles_use_distinct_run_ids() -> None:
    assert build_bundle(seed=None).run_id != build_bundle(seed=None).run_id
