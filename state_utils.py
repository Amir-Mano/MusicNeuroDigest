"""Atomic JSON state writes: serialize to a temp file in the same directory,
then rename over the target. A plain write_text() left a state file
truncated (and permanently unparseable by json.loads on every future run)
if the process died mid-write; os.replace() is atomic on both Windows and
POSIX, so a reader only ever sees the old complete file or the new one.
"""

import json
import os
import tempfile
from pathlib import Path


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
