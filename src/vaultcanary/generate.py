"""Build and write disposable migration canaries."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Bundle:
    """In-memory synthetic probe and its audit contract."""

    run_id: str
    probe: dict[str, Any]
    manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WrittenBundle:
    """Paths produced by :func:`write_bundle`."""

    run_id: str
    probe_path: Path
    manifest_path: Path
    instructions_path: Path


def build_bundle(*, seed: str | None) -> Bundle:
    """Create one synthetic Bitwarden vault and its feature manifest."""

    run_id = _run_id(seed)
    prefix = f"VaultCanary {run_id} —"
    folder_id = _stable_uuid(run_id, "folder")
    folder_name = f"VCN-{run_id}-FOLDER"
    login_title = f"{prefix} Login"
    note_title = f"{prefix} Secure Note"
    card_title = f"{prefix} Card"
    identity_title = f"{prefix} Identity"

    uri = f"https://login-{run_id}.example.invalid/account"
    username = f"canary+{run_id}@example.invalid"
    password = f"VCN!{run_id}!PASSWORD!7x"
    login_notes = f"VCN-{run_id}-LOGIN-NOTES"
    text_field = f"VCN-{run_id}-CUSTOM-TEXT"
    hidden_field = f"VCN-{run_id}-CUSTOM-HIDDEN"
    unicode_value = f"VCN-{run_id}-UNICODE-你好-مرحبا-🙂-e\u0301"
    totp_secret = _totp_secret(run_id)
    totp_uri = (
        f"otpauth://totp/VaultCanary:{run_id}?secret={totp_secret}"
        "&issuer=VaultCanary&algorithm=SHA1&digits=6&period=30"
    )
    note_body = f"VCN-{run_id}-SECURE-NOTE-BODY"
    cardholder = f"VCN-{run_id}-CARDHOLDER"
    card_number = "4111111111111111"
    identity_email = f"identity+{run_id}@example.invalid"
    identity_address = f"VCN-{run_id}-IDENTITY-ADDRESS"

    login_item = {
        "id": _stable_uuid(run_id, "login"),
        "folderId": folder_id,
        "type": 1,
        "reprompt": 0,
        "name": login_title,
        "notes": login_notes,
        "favorite": True,
        "fields": [
            {"name": "Canary text", "value": text_field, "type": 0},
            {"name": "Canary hidden", "value": hidden_field, "type": 1},
            {"name": "Canary boolean", "value": "true", "type": 2},
            {"name": "Unicode sample", "value": unicode_value, "type": 0},
        ],
        "login": {
            "uris": [{"match": None, "uri": uri}],
            "username": username,
            "password": password,
            "totp": totp_uri,
        },
    }
    note_item = {
        "id": _stable_uuid(run_id, "note"),
        "folderId": None,
        "type": 2,
        "reprompt": 0,
        "name": note_title,
        "notes": note_body,
        "favorite": False,
        "secureNote": {"type": 0},
    }
    card_item = {
        "id": _stable_uuid(run_id, "card"),
        "folderId": None,
        "type": 3,
        "reprompt": 0,
        "name": card_title,
        "notes": None,
        "favorite": False,
        "card": {
            "cardholderName": cardholder,
            "brand": "Visa",
            "number": card_number,
            "expMonth": "12",
            "expYear": "2030",
            "code": "123",
        },
    }
    identity_item = {
        "id": _stable_uuid(run_id, "identity"),
        "folderId": None,
        "type": 4,
        "reprompt": 0,
        "name": identity_title,
        "notes": None,
        "favorite": False,
        "identity": {
            "title": "Mx",
            "firstName": "Canary",
            "middleName": None,
            "lastName": run_id,
            "address1": identity_address,
            "address2": None,
            "address3": None,
            "city": "Example City",
            "state": "EX",
            "postalCode": "00000",
            "country": "ZZ",
            "company": "VaultCanary",
            "email": identity_email,
            "phone": "+1-555-0100",
            "ssn": None,
            "username": None,
            "passportNumber": None,
            "licenseNumber": None,
        },
    }
    probe: dict[str, Any] = {
        "encrypted": False,
        "folders": [{"id": folder_id, "name": folder_name}],
        "items": [login_item, note_item, card_item, identity_item],
    }
    features = [
        _feature("login.title", login_title, "title", login_title),
        _feature("login.uri", login_title, "login.uri", uri, kind="uri"),
        _feature("login.username", login_title, "login.username", username),
        _feature("login.password", login_title, "login.password", password),
        _feature("login.notes", login_title, "notes", login_notes),
        _feature("login.totp", login_title, "login.totp", totp_uri, kind="totp"),
        _feature("custom.text", login_title, "custom.Canary text", text_field),
        _feature("custom.hidden", login_title, "custom.Canary hidden", hidden_field),
        _feature("custom.boolean", login_title, "custom.Canary boolean", "true"),
        _feature("unicode.roundtrip", login_title, "custom.Unicode sample", unicode_value),
        _feature("folder.assignment", login_title, "folder", folder_name),
        _feature("favorite.status", login_title, "favorite", True, kind="boolean"),
        _feature("secure_note.body", note_title, "notes", note_body),
        _feature("card.cardholder", card_title, "card.cardholder", cardholder),
        _feature("card.number", card_title, "card.number", card_number),
        _feature("identity.email", identity_title, "identity.email", identity_email),
        _feature("identity.address", identity_title, "identity.address", identity_address),
    ]
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "tool": "vaultcanary",
        "synthetic_data": True,
        "run_id": run_id,
        "title_prefix": prefix,
        "source_format": "bitwarden-json",
        "features": features,
    }
    return Bundle(run_id=run_id, probe=probe, manifest=manifest)


def write_bundle(output_dir: Path, *, seed: str | None) -> WrittenBundle:
    """Write a generated bundle to a new or empty directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle(seed=seed)
    probe_path = output_dir / "vaultcanary-bitwarden.json"
    manifest_path = output_dir / "vaultcanary-manifest.json"
    instructions_path = output_dir / "NEXT_STEPS.md"
    _write_json(probe_path, bundle.probe)
    _write_json(manifest_path, bundle.manifest)
    instructions_path.write_text(_instructions(bundle.run_id), encoding="utf-8", newline="\n")
    return WrittenBundle(
        run_id=bundle.run_id,
        probe_path=probe_path,
        manifest_path=manifest_path,
        instructions_path=instructions_path,
    )


def _feature(
    feature_id: str,
    item_title: str,
    expected_path: str,
    expected_value: str | bool,
    *,
    kind: str = "exact",
) -> dict[str, Any]:
    return {
        "feature_id": feature_id,
        "item_title": item_title,
        "expected_path": expected_path,
        "expected_value": expected_value,
        "kind": kind,
    }


def _run_id(seed: str | None) -> str:
    if seed is None:
        return secrets.token_hex(6)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _stable_uuid(run_id: str, label: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"vaultcanary:{run_id}:{label}"))


def _totp_secret(run_id: str) -> str:
    digest = hashlib.sha256(f"vaultcanary:{run_id}:totp".encode()).digest()[:20]
    return base64.b32encode(digest).decode("ascii").rstrip("=")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _instructions(run_id: str) -> str:
    return f"""# VaultCanary run {run_id}

1. Import `vaultcanary-bitwarden.json` into an empty test vault or disposable profile.
2. Export that test vault as Bitwarden JSON/CSV or 1Password 1PUX.
3. Run:

   `vaultcanary audit vaultcanary-manifest.json PATH_TO_RETURN_EXPORT --html report.html`

Exit 0 means every v0.1.0 canary feature returned in its expected semantic field.
Exit 1 means at least one feature was relocated or lost. Exit 2 means the files could
not be audited. All values in this bundle are synthetic; do not add real credentials.
"""
