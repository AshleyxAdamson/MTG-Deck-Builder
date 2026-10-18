"""Getting a finished order to a shop.

No print shop has an API. notmpc.com takes the MPC Autofill XML through its order form,
so `send` opens that page and says what to click; a browser driver that fills the form is
the follow-up in docs/spec/print-suite.md. MakePlayingCards is the fallback, through the
mpc-autofill desktop tool when it is installed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from ..cards import CardDataError

NOTMPC_URL = "https://notmpc.com/custom-game-cards/"
NOTMPC_STEPS = [
    "Choose the custom game cards product, black border, 63 x 88 mm, S33 Superior Smooth, and the quantity tier shown above.",
    "Upload the XML file. The page fetches every image from Google Drive and fills the slots; check none is blank.",
    "Add to cart (repeat for a second deck's XML), check out and pay.",
    "Then tell the agent the order number: it records the order in the ledger with `mtg placed`.",
]


def open_in_browser(url_or_path: str) -> bool:
    opener = shutil.which("open") or shutil.which("xdg-open")
    if not opener:
        return False
    return subprocess.run([opener, url_or_path], capture_output=True).returncode == 0


def to_notmpc(xml_paths: list[Path], *, open_browser: bool = True) -> dict:
    opened = open_in_browser(NOTMPC_URL) if open_browser else False
    if open_browser:
        for path in xml_paths:
            open_in_browser(str(path.parent))
    return {"shop": "notmpc", "url": NOTMPC_URL, "opened": opened, "xml": [str(p) for p in xml_paths], "steps": NOTMPC_STEPS}


def to_mpc(xml_paths: list[Path], *, autofill_bin: str | None = None) -> dict:
    """Put each XML in its own folder (the desktop tool reads one per directory) and run the tool when given."""
    folders = []
    for path in xml_paths:
        folder = path.parent / "mpc" / path.stem
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, folder / path.name)
        folders.append(folder)
    result = {"shop": "mpc", "folders": [str(f) for f in folders], "ran": False}
    if autofill_bin:
        binary = Path(autofill_bin).expanduser()
        if not binary.exists():
            raise CardDataError(f"{binary} does not exist. Download the mpc-autofill desktop tool and pass its path.")
        for folder in folders:
            # The tool is interactive (it waits for a login in Chrome), so it keeps the terminal.
            subprocess.run([str(binary), "--directory", str(folder), "--site", "MakePlayingCards"], cwd=folder,
                           stdin=sys.stdin, stdout=sys.stderr)
        result["ran"] = True
    else:
        result["steps"] = [
            "Install the mpc-autofill desktop tool (github.com/chilli-axe/mpc-autofill, releases).",
            "Run it in each folder above: it opens Chrome, waits for you to log in to MakePlayingCards, then fills the order.",
            "Add the project to your cart on the site and pay; tell the agent the order number.",
        ]
    return result
