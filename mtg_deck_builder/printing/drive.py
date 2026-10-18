"""Prepared card images in the user's own Google Drive, uploaded with the rclone CLI.

The print shop fetches each image anonymously by Drive id, so every file goes into one
folder and is shared as "anyone with the link". rclone does Google's OAuth in a one-time
`rclone config` session, so this module holds no tokens. Which Drive remote to use comes
from MTG_DRIVE_REMOTE (default "gdrive"). Uploaded names are remembered in
data/drive/uploads.json, so a re-export finds the file it already uploaded.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from ..cards import DATA_DIR, CardDataError

REMOTE = os.environ.get("MTG_DRIVE_REMOTE", "gdrive")
FOLDER = "MTG proxies"
TIMEOUT = 300
UPLOADS_FILE = DATA_DIR / "drive" / "uploads.json"
_ID = re.compile(r"(?:[?&]id=|/d/|/folders/)([A-Za-z0-9_-]{10,})")


class DriveUnavailable(CardDataError):
    """Google Drive cannot be used through rclone; the message says what to do."""


def _rclone(*args: str) -> subprocess.CompletedProcess:
    """Run rclone and return the finished process; raises on timeout, never on a non-zero exit."""
    try:
        return subprocess.run(["rclone", *args], capture_output=True, text=True, timeout=TIMEOUT)
    except FileNotFoundError:
        require()
        raise
    except subprocess.TimeoutExpired:
        raise DriveUnavailable(f"rclone took longer than {TIMEOUT} s on `rclone {args[0]}`. Check the connection and re-run.")


def _first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "no error message")


def _checked(*args: str) -> str:
    """Stdout of an rclone call that must succeed."""
    done = _rclone(*args)
    if done.returncode != 0:
        raise DriveUnavailable(f"`rclone {args[0]}` failed (exit {done.returncode}): {_first_line(done.stderr)}")
    return done.stdout


def _target(name: str | None = None) -> str:
    return f"{REMOTE}:{FOLDER}" + (f"/{name}" if name else "")


def available() -> bool:
    """Is rclone installed and does it have the Drive remote?"""
    if not shutil.which("rclone"):
        return False
    try:
        done = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and f"{REMOTE}:" in done.stdout.split()


def require() -> None:
    """Raise DriveUnavailable, saying how to fix it, unless available()."""
    if not shutil.which("rclone"):
        raise DriveUnavailable("rclone is not installed. Run: brew install rclone  -- then run `rclone config` "
                               f"to create a Google Drive remote named {REMOTE}, and re-run this.")
    if not available():
        raise DriveUnavailable(
            f"rclone has no remote named {REMOTE!r}. Run: rclone config  -- choose New remote, name it {REMOTE}, "
            "type drive (Google Drive), scope drive.file is enough, and finish the browser sign-in. "
            "Then re-run this. (To use another remote name, set MTG_DRIVE_REMOTE.)")


def existing() -> dict[str, str]:
    """{file name: Drive id} for the files already in the folder; empty when the folder does not exist yet."""
    require()
    done = _rclone("lsjson", _target(), "--files-only")
    if done.returncode != 0:
        if "directory not found" in done.stderr.lower():
            return {}
        raise DriveUnavailable(f"`rclone lsjson` failed (exit {done.returncode}): {_first_line(done.stderr)}")
    return {entry["Name"]: entry["ID"] for entry in json.loads(done.stdout or "[]") if entry.get("ID")}


def _remembered() -> dict[str, str]:
    try:
        return json.loads(UPLOADS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _remember(name: str, drive_id: str) -> None:
    known = _remembered()
    known[name] = drive_id
    UPLOADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    UPLOADS_FILE.write_text(json.dumps(known, indent=1, sort_keys=True), encoding="utf-8")


def _link(name: str) -> str:
    """Share the file with anyone who has the link and return its Drive id."""
    out = _checked("link", _target(name))
    match = _ID.search(out)
    if not match:
        raise DriveUnavailable(f"`rclone link` printed no Drive id for {name}: {_first_line(out)}")
    return match.group(1)


def upload(path: Path) -> str:
    """Put an image in the Drive folder, shared by link, and return its Drive id. Already-uploaded names are reused."""
    path = Path(path)
    if not path.is_file():
        raise CardDataError(f"{path} does not exist, so it cannot be uploaded.")
    require()
    name = path.name
    here = existing()
    if name in here:
        remembered = _remembered().get(name)
        if remembered == here[name]:
            return remembered
        drive_id = _link(name)  # uploaded earlier without being recorded: make sure it is shared
        _remember(name, drive_id)
        return drive_id
    _checked("mkdir", _target())
    _checked("copyto", str(path), _target(name))
    drive_id = _link(name)
    _remember(name, drive_id)
    return drive_id
