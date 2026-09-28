from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

PYTHON_EXTENSIONS = {".py"}
JSON_EXTENSIONS = {".json"}
TOML_EXTENSIONS = {".toml"}
SHELL_EXTENSIONS = {".sh", ".bash"}
NODE_MODULE_EXTENSIONS = {".mjs"}
NODE_COMMONJS_EXTENSIONS = {".cjs"}


def _run_git(
    root: Path,
    args: list[str],
    *,
    text: bool = False,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=text,
    )


def _staged_paths(root: Path) -> list[Path]:
    result = _run_git(
        root,
        ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
    )
    if result.returncode != 0:
        return []
    raw = bytes(result.stdout)
    return [Path(os.fsdecode(item)) for item in raw.split(b"\0") if item]


def _staged_bytes(root: Path, path: Path) -> bytes | None:
    result = _run_git(root, ["show", f":{path.as_posix()}"])
    if result.returncode != 0:
        return None
    return bytes(result.stdout)


def _syntax_error(path: Path, exc: SyntaxError) -> str:
    location = ""
    if exc.lineno is not None:
        location = f":{exc.lineno}"
        if exc.offset is not None:
            location += f":{exc.offset}"
    return f"{path}{location}: {exc.msg}"


def _validate_python(path: Path, data: bytes) -> str | None:
    try:
        compile(data, path.as_posix(), "exec", ast.PyCF_ONLY_AST, dont_inherit=True)
    except SyntaxError as exc:
        return _syntax_error(path, exc)
    except (TypeError, ValueError) as exc:
        return f"{path}: {exc}"
    return None


def _validate_json(path: Path, data: bytes) -> str | None:
    try:
        json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return f"{path}: {exc}"
    return None


def _validate_toml(path: Path, data: bytes) -> str | None:
    try:
        tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return f"{path}: {exc}"
    return None


def _validate_external(
    path: Path,
    data: bytes,
    command: list[str],
) -> str | None:
    result = subprocess.run(command, input=data, capture_output=True)
    if result.returncode == 0:
        return None
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    detail = stderr.splitlines()[0] if stderr else f"exit code {result.returncode}"
    return f"{path}: {detail}"


def _validator_error(path: Path, data: bytes) -> str | None:
    suffix = path.suffix.lower()
    if suffix in PYTHON_EXTENSIONS:
        return _validate_python(path, data)
    if suffix in JSON_EXTENSIONS:
        return _validate_json(path, data)
    if suffix in TOML_EXTENSIONS:
        return _validate_toml(path, data)
    if suffix in SHELL_EXTENSIONS:
        bash = shutil.which("bash")
        return _validate_external(path, data, [bash, "-n"]) if bash else None
    if suffix in NODE_MODULE_EXTENSIONS:
        node = shutil.which("node")
        return (
            _validate_external(path, data, [node, "--check", "--input-type=module", "-"])
            if node
            else None
        )
    if suffix in NODE_COMMONJS_EXTENSIONS:
        node = shutil.which("node")
        return (
            _validate_external(path, data, [node, "--check", "--input-type=commonjs", "-"])
            if node
            else None
        )
    return None


def staged_syntax_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _staged_paths(root):
        data = _staged_bytes(root, path)
        if data is None:
            continue
        error = _validator_error(path, data)
        if error is not None:
            errors.append(error)
    return errors
