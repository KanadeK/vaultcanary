"""Strict local readers for supported password-manager return exports."""

from __future__ import annotations

import csv
import json
import zipfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from vaultcanary.model import NormalizedItem, NormalizedVault, Scalar

DEFAULT_MAX_BYTES = 64 * 1024 * 1024
BITWARDEN_CSV_HEADERS = {
    "folder",
    "favorite",
    "type",
    "name",
    "notes",
    "fields",
    "reprompt",
    "login_uri",
    "login_username",
    "login_password",
    "login_totp",
}


class ExportError(ValueError):
    """A return export cannot be audited safely or unambiguously."""


def load_export(
    path: Path,
    *,
    title_prefix: str | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> NormalizedVault:
    """Load one supported export without extracting archives or calling a network."""

    try:
        size = path.stat().st_size
    except OSError as error:
        raise ExportError(f"cannot read return export: {path}") from error
    if size > max_bytes:
        raise ExportError(f"return export is larger than {max_bytes} bytes")

    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_bitwarden_json(path, title_prefix)
    if suffix == ".csv":
        return _load_bitwarden_csv(path, title_prefix)
    if suffix == ".1pux":
        return _load_1pux(path, title_prefix, max_bytes)
    raise ExportError("supported return exports are .json, .csv, and .1pux")


def _load_bitwarden_json(path: Path, title_prefix: str | None) -> NormalizedVault:
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExportError("return export is not valid UTF-8 JSON") from error
    root_map = _mapping(root, "Bitwarden JSON root")
    if root_map.get("encrypted") is True:
        raise ExportError("encrypted Bitwarden exports are not supported")
    folders_raw = root_map.get("folders", [])
    folders: dict[str, str] = {}
    for index, value in enumerate(_iter_list(folders_raw, "folders")):
        folder = _mapping(value, f"folders[{index}]")
        folder_id = _required_str(folder.get("id"), f"folders[{index}].id")
        folders[folder_id] = _required_str(folder.get("name"), f"folders[{index}].name")

    items: list[NormalizedItem] = []
    for index, value in enumerate(_iter_list(root_map.get("items"), "items")):
        item = _mapping(value, f"items[{index}]")
        title = _required_str(item.get("name"), f"items[{index}].name")
        if title_prefix is not None and not title.startswith(title_prefix):
            continue
        items.append(_normalize_bitwarden_item(item, title, folders, index))
    return NormalizedVault("bitwarden-json", tuple(items))


def _normalize_bitwarden_item(
    item: Mapping[str, Any], title: str, folders: Mapping[str, str], index: int
) -> NormalizedItem:
    item_type_number = item.get("type")
    if not isinstance(item_type_number, int) or isinstance(item_type_number, bool):
        raise ExportError(f"items[{index}].type must be an integer")
    item_type = {1: "login", 2: "secure-note", 3: "card", 4: "identity"}.get(
        item_type_number, f"bitwarden-{item_type_number}"
    )
    values: dict[str, Scalar] = {"title": title}
    _put(values, "notes", item.get("notes"))
    _put(values, "favorite", item.get("favorite"))
    folder_id = item.get("folderId")
    if isinstance(folder_id, str) and folder_id in folders:
        values["folder"] = folders[folder_id]

    login = item.get("login")
    if isinstance(login, Mapping):
        _put(values, "login.username", login.get("username"))
        _put(values, "login.password", login.get("password"))
        _put(values, "login.totp", login.get("totp"))
        uris = login.get("uris", [])
        if isinstance(uris, list) and uris:
            first_uri = uris[0]
            if isinstance(first_uri, Mapping):
                _put(values, "login.uri", first_uri.get("uri"))

    for field_index, raw_field in enumerate(_iter_list(item.get("fields", []), "fields")):
        field = _mapping(raw_field, f"items[{index}].fields[{field_index}]")
        label = _required_str(field.get("name"), f"items[{index}].fields[{field_index}].name")
        field_type = field.get("type")
        semantic_type = (
            {0: "text", 1: "hidden", 2: "boolean", 3: "linked"}.get(field_type, "unknown")
            if isinstance(field_type, int) and not isinstance(field_type, bool)
            else "unknown"
        )
        _put(values, f"custom.{semantic_type}.{label}", field.get("value"))

    card = item.get("card")
    if isinstance(card, Mapping):
        _put(values, "card.cardholder", card.get("cardholderName"))
        _put(values, "card.number", card.get("number"))
    identity = item.get("identity")
    if isinstance(identity, Mapping):
        _put(values, "identity.email", identity.get("email"))
        _put(values, "identity.address", identity.get("address1"))
    return NormalizedItem(title=title, item_type=item_type, values=values)


def _load_bitwarden_csv(path: Path, title_prefix: str | None) -> NormalizedVault:
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise ExportError("cannot open Bitwarden CSV export") from error
    with handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        if headers != BITWARDEN_CSV_HEADERS:
            raise ExportError("CSV headers do not match the documented Bitwarden export")
        items: list[NormalizedItem] = []
        try:
            for row_number, row in enumerate(reader, start=2):
                title = row["name"]
                if not title:
                    raise ExportError(f"CSV row {row_number} has no name")
                if title_prefix is not None and not title.startswith(title_prefix):
                    continue
                values: dict[str, Scalar] = {"title": title}
                for semantic, column in (
                    ("folder", "folder"),
                    ("notes", "notes"),
                    ("login.uri", "login_uri"),
                    ("login.username", "login_username"),
                    ("login.password", "login_password"),
                    ("login.totp", "login_totp"),
                ):
                    if row[column]:
                        values[semantic] = row[column]
                values["favorite"] = row["favorite"].strip().lower() in {"1", "true"}
                for label, field_value in _parse_csv_fields(row["fields"]):
                    values[f"custom.untyped.{label}"] = field_value
                items.append(NormalizedItem(title, row["type"] or "unknown", values))
        except csv.Error as error:
            raise ExportError("return export is not valid CSV") from error
    return NormalizedVault("bitwarden-csv", tuple(items))


def _parse_csv_fields(value: str) -> Iterable[tuple[str, str]]:
    for line in value.splitlines():
        label, separator, field_value = line.partition(": ")
        if separator and label:
            yield label, field_value


def _load_1pux(path: Path, title_prefix: str | None, max_bytes: int) -> NormalizedVault:
    try:
        with zipfile.ZipFile(path) as archive:
            members = [member for member in archive.infolist() if member.filename == "export.data"]
            if not members:
                raise ExportError("1PUX archive is missing export.data")
            if len(members) != 1:
                raise ExportError("1PUX archive must contain exactly one export.data member")
            member = members[0]
            if member.file_size > max_bytes:
                raise ExportError(f"1PUX export.data is larger than {max_bytes} bytes")
            raw = archive.read(member)
    except zipfile.BadZipFile as error:
        raise ExportError("return export is not a valid 1PUX ZIP archive") from error
    try:
        root = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExportError("1PUX export.data is not valid UTF-8 JSON") from error

    items: list[NormalizedItem] = []
    root_map = _mapping(root, "1PUX export.data root")
    for account_index, account_raw in enumerate(_iter_list(root_map.get("accounts"), "accounts")):
        account = _mapping(account_raw, f"accounts[{account_index}]")
        for vault_index, vault_raw in enumerate(_iter_list(account.get("vaults"), "vaults")):
            vault = _mapping(vault_raw, f"accounts[{account_index}].vaults[{vault_index}]")
            for item_index, item_raw in enumerate(_iter_list(vault.get("items"), "items")):
                item = _mapping(item_raw, f"vaults[{vault_index}].items[{item_index}]")
                overview = _mapping(item.get("overview"), "1PUX item overview")
                title = _required_str(overview.get("title"), "1PUX item overview.title")
                if title_prefix is not None and not title.startswith(title_prefix):
                    continue
                items.append(_normalize_1pux_item(item, overview, title))
    return NormalizedVault("1password-1pux", tuple(items))


def _normalize_1pux_item(
    item: Mapping[str, Any], overview: Mapping[str, Any], title: str
) -> NormalizedItem:
    values: dict[str, Scalar] = {"title": title, "favorite": bool(item.get("favIndex", 0))}
    urls = overview.get("urls", overview.get("URLs", []))
    if isinstance(urls, list) and urls:
        first_url = urls[0]
        if isinstance(first_url, Mapping):
            _put(values, "login.uri", first_url.get("url"))
    details = item.get("details")
    if isinstance(details, Mapping):
        _put(values, "notes", details.get("notesPlain"))
        for field in _mapping_list(details.get("loginFields", [])):
            designation = field.get("designation")
            if designation in {"username", "password"}:
                _put(values, f"login.{designation}", field.get("value"))
        for section in _mapping_list(details.get("sections", [])):
            for field in _mapping_list(section.get("fields", [])):
                _put_1pux_field(values, field)
    for tag_index, tag in enumerate(_iter_list(overview.get("tags", []), "tags")):
        if isinstance(tag, str):
            values[f"tag.{tag_index}"] = tag
    item_type = str(item.get("categoryUuid", "unknown"))
    return NormalizedItem(title, f"1password-{item_type}", values)


def _put_1pux_field(values: dict[str, Scalar], field: Mapping[str, Any]) -> None:
    title_value = field.get("title", field.get("id", "field"))
    if not isinstance(title_value, str):
        return
    value = field.get("value")
    field_type = str(field.get("fieldType", "STRING")).upper()
    if field_type in {"OTP", "TOTP", "ONE_TIME_PASSWORD"}:
        _put(values, "login.totp", value)
        return
    label = title_value.strip()
    normalized_label = label.casefold()
    known_paths = {
        "cardholder": "card.cardholder",
        "cardholder name": "card.cardholder",
        "card number": "card.number",
        "number": "card.number",
        "email": "identity.email",
        "address": "identity.address",
        "address 1": "identity.address",
    }
    if normalized_label in known_paths:
        _put(values, known_paths[normalized_label], value)
        return
    semantic_type = "hidden" if field_type == "CONCEALED" else "text"
    if field_type in {"BOOLEAN", "BOOL"}:
        semantic_type = "boolean"
    _put(values, f"custom.{semantic_type}.{label}", value)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExportError(f"{label} must be an object")
    return value


def _mapping_list(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, list):
        return ()
    return (entry for entry in value if isinstance(entry, Mapping))


def _iter_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ExportError(f"{label} must be an array")
    return value


def _required_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExportError(f"{label} must be a non-empty string")
    return value


def _put(values: dict[str, Scalar], path: str, value: Any) -> None:
    if isinstance(value, (str, bool)):
        values[path] = value
