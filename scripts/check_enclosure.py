"""OpenSCAD実行による構文・2D/3D出力検査。加工適合や安全性を保証しない。"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from mechanical import ROOT, validate, load_layout


def find_openscad():
    candidates = [os.environ.get("OPENSCAD_CLI"), shutil.which("openscad")]
    candidates.extend(str(path) for path in Path("/Applications").glob("OpenSCAD*.app/Contents/MacOS/OpenSCAD"))
    return next((candidate for candidate in candidates if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK)), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    cli = find_openscad()
    if not cli:
        print("OpenSCAD未検出。OPENSCAD_CLIまたはPATHを設定してください。", file=sys.stderr)
        return 1
    output = ROOT / "build/enclosure"
    output.mkdir(parents=True, exist_ok=True)
    report = validate(load_layout())
    log = []
    tasks = [["--version"], ["--hardwarnings", "-o", str(output / "assembly.csg"), "enclosure/clock.scad"]]
    for name, suffix in (("front_2d", "svg"), ("rear_2d", "svg"), ("shell", "stl"), ("hv_cover", "stl")):
        tasks.append(["--hardwarnings", "-o", str(output / (name + "." + suffix)), "-D", f'part="{name}"', "enclosure/clock.scad"])
    if args.preview:
        tasks.append(["--hardwarnings", "-o", str(output / "assembly.png"), "--imgsize", "1280,960", "--viewall", "--autocenter", "--projection", "o", "--camera", "0,45,42,65,0,25,370", "enclosure/clock.scad"])
    for arguments in tasks:
        try:
            result = subprocess.run([cli, *arguments], cwd=ROOT, capture_output=True, text=True, timeout=90)
            log.append({"command": [cli, *arguments], "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            if result.returncode != 0:
                report["errors"].append("OpenSCAD実行失敗: " + " ".join(arguments[:3]))
            if "-o" in arguments:
                artifact = Path(arguments[arguments.index("-o") + 1])
                if not artifact.exists() or artifact.stat().st_size == 0:
                    report["errors"].append("出力なし: " + artifact.name)
                elif artifact.suffix == ".svg":
                    ET.parse(artifact)
        except (OSError, subprocess.TimeoutExpired, ET.ParseError) as error:
            report["errors"].append(str(error))
    report.update({"status": "FAIL" if report["errors"] else "PASS", "manufacturing_release": False,
                   "openscad_cli": cli, "commands": log,
                   "scope": "OpenSCAD構文と出力、共通JSONの概略包絡検査。現物・公差・熱・固定方法・絶縁・受信は未検証。"})
    (output / "openscad-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "commands"}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
