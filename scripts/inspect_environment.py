"""macOS・Linuxの開発環境を読み取り専用で記録する。"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def find_kicad_cli():
    override = os.environ.get("KICAD_CLI")
    candidates = [override] if override else []
    candidates.extend([
        shutil.which("kicad-cli"),
        "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
        "/Applications/KiCad.app/Contents/MacOS/kicad-cli",
    ])
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    return None


def probe(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "error": str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cli = find_kicad_cli()
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "python": sys.version,
        "tools": {name: shutil.which(name) for name in (
            "git", "curl", "cmake", "kicad", "pcbnew", "eeschema",
            "arduino-cli", "node", "npm",
        )},
        "kicad_cli": cli,
        "pcbnew_in_this_python": importlib.util.find_spec("pcbnew") is not None,
        "mcp": "このスクリプトでは接続状態を検査しない",
        "kicad_probes": [probe([cli, "--version"]), probe([cli, "--help"])] if cli else [],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
