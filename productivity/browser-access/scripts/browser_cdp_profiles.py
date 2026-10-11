"""Typed, host-local named configurations for dedicated Agent Chrome instances."""
from __future__ import annotations

import json
import os
import re
import tempfile
import tomllib
import urllib.parse
from dataclasses import dataclass, replace
from pathlib import Path

from browser_cdp_core import BrowserCdpError
from browser_cdp_lifecycle import (
    BrowserConfig, config_from_options, normalized_directory, validate_config,
)

DEFAULT_CONFIG_PATH = Path.home() / ".agent-browser" / "profiles.toml"


@dataclass(frozen=True)
class NamedProfile:
    name: str
    config: BrowserConfig


def validate_name(name: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name):
        raise BrowserCdpError("Profile names must use lowercase letters, digits and single hyphens")


def endpoint_key(endpoint: str) -> tuple[str, str | None, int | None]:
    parsed = urllib.parse.urlsplit(endpoint)
    host = "localhost" if parsed.hostname in {"localhost", "127.0.0.1", "::1"} else parsed.hostname
    return parsed.scheme, host, parsed.port or (443 if parsed.scheme == "https" else 80)


def validate_profiles(profiles: tuple[NamedProfile, ...]) -> None:
    names: set[str] = set()
    endpoints = {endpoint_key(BrowserConfig().endpoint)}
    directories: set[str] = set()
    for profile in profiles:
        validate_name(profile.name)
        if profile.name == "agent-browser":
            raise BrowserCdpError("agent-browser is a built-in default and cannot be redefined")
        validate_config(profile.config)
        directory = profile.config.user_data_dir
        if directory is None:
            raise BrowserCdpError(f"Named profile {profile.name!r} requires a dedicated user_data_dir")
        key = endpoint_key(profile.config.endpoint)
        normalized = normalized_directory(directory)
        overlaps = any(normalized == other or normalized.startswith(other + "\\") or
                       other.startswith(normalized + "\\") for other in directories)
        if profile.name in names or key in endpoints or overlaps:
            raise BrowserCdpError(f"Profile {profile.name!r} duplicates a name/endpoint or shares an overlapping data directory")
        names.add(profile.name)
        endpoints.add(key)
        directories.add(normalized)


def load_profiles(path: Path) -> tuple[NamedProfile, ...]:
    try:
        with path.open("rb") as source:
            document = tomllib.load(source)
    except FileNotFoundError:
        return ()
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise BrowserCdpError(f"Cannot read named browser configuration {path}: {exc}") from exc
    if set(document) != {"schema", "profiles"} or type(document["schema"]) is not int or document["schema"] != 1:
        raise BrowserCdpError("Named browser configuration requires schema = 1 and a profiles table")
    table = document["profiles"]
    if not isinstance(table, dict):
        raise BrowserCdpError("profiles must be a TOML table")
    profiles: list[NamedProfile] = []
    for name, fields in table.items():
        if not isinstance(fields, dict) or not {"endpoint", "user_data_dir"} <= set(fields) or \
                not set(fields) <= {"endpoint", "user_data_dir", "profile_directory"}:
            raise BrowserCdpError(f"Profile {name!r} requires endpoint/user_data_dir and optional profile_directory only")
        if not all(isinstance(value, str) and value.strip() for value in fields.values()):
            raise BrowserCdpError(f"Profile {name!r} fields must be nonempty strings")
        profiles.append(NamedProfile(name, BrowserConfig(
            endpoint=fields["endpoint"], user_data_dir=fields["user_data_dir"],
            profile_directory=fields.get("profile_directory", "Default"), identity=name,
        )))
    result = tuple(profiles)
    validate_profiles(result)
    return result


def resolve_profile(name: str | None, path: Path, endpoint: str | None,
                    user_data_dir: str | None, profile_directory: str | None) -> BrowserConfig:
    if name is None:
        return config_from_options(endpoint, user_data_dir, profile_directory)
    if any(option is not None for option in (endpoint, user_data_dir, profile_directory)):
        raise BrowserCdpError("--profile cannot be combined with endpoint or directory overrides")
    validate_name(name)
    if name == "agent-browser":
        return BrowserConfig()
    for profile in load_profiles(path):
        if profile.name == name:
            return profile.config
    raise BrowserCdpError(f"Unknown dedicated profile {name!r} in {path}; use profile-save first")


def serialize_profiles(profiles: tuple[NamedProfile, ...]) -> str:
    lines = ["# browser-access 专用 Agent 浏览器配置；不保存凭据。", "schema = 1", "", "[profiles]"]
    for profile in profiles:
        lines.extend([
            "", f"[profiles.{profile.name}]",
            "endpoint = " + json.dumps(profile.config.endpoint, ensure_ascii=False),
            "user_data_dir = " + json.dumps(profile.config.user_data_dir, ensure_ascii=False),
            "profile_directory = " + json.dumps(profile.config.profile_directory, ensure_ascii=False),
        ])
    return "\n".join(lines) + "\n"


def save_profile(name: str, config: BrowserConfig, path: Path) -> NamedProfile:
    profile = NamedProfile(name, replace(config, identity=name))
    validate_profiles((profile,))
    lock = path.with_name(path.name + ".lock")
    temporary: Path | None = None
    acquired = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(lock_fd)
        acquired = True
        profiles = load_profiles(path) + (profile,)
        validate_profiles(profiles)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write(serialize_profiles(profiles))
        os.replace(temporary, path)
        temporary = None
    except FileExistsError as exc:
        raise BrowserCdpError(f"Named profile configuration is locked: {lock}") from exc
    except OSError as exc:
        raise BrowserCdpError(f"Cannot save named browser configuration {path}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if acquired:
            lock.unlink(missing_ok=True)
    return profile
