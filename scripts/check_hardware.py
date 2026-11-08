"""KiCad実出力を回路定義と照合し、未確定部品を製造承認から分離する。"""

import argparse
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from inspect_environment import find_kicad_cli


ROOT = Path(__file__).resolve().parents[1]


def run_cli(cli, arguments, log):
    result = subprocess.run([cli, *arguments], cwd=ROOT, capture_output=True, text=True, timeout=90)
    log.append({"command": [cli, *arguments], "returncode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr})
    return result.returncode


def check(output, cli):
    output.mkdir(parents=True, exist_ok=True)
    schematic = "hardware/schematic/generated/nixie-jjy-clock.kicad_sch"
    log = []
    errors = []
    paths = {name: output / filename for name, filename in (("erc", "erc.json"), ("xml", "clock.xml"), ("bom", "bom.csv"), ("pdf", "schematic.pdf"))}
    jobs = [
        ["sch", "erc", "--format", "json", "--severity-all", "--exit-code-violations", "-o", str(paths["erc"]), schematic],
        ["sch", "export", "netlist", "--format", "kicadxml", "-o", str(paths["xml"]), schematic],
        ["sch", "export", "bom", "--fields", "Reference,Value,Sources,OpenRisks,ReviewStatus,Footprint,QUANTITY",
         "--labels", "Reference,Value,Sources,OpenRisks,ReviewStatus,Footprint,Qty", "-o", str(paths["bom"]), schematic],
        ["sch", "export", "pdf", "-o", str(paths["pdf"]), schematic],
    ]
    for job in jobs:
        if run_cli(cli, job, log) != 0:
            errors.append("KiCadコマンド失敗: " + " ".join(job[:3]))
    (output / "cli-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        return {"status": "FAIL", "errors": errors, "manufacturing_release": False}
    specification = importlib.util.spec_from_file_location("clock_design", ROOT / "hardware/schematic_design.py")
    design = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(design)
    components = {component["reference"]: component for sheet in design.SHEETS for component in sheet["components"] if not component["reference"].startswith("#")}
    tree = ET.parse(paths["xml"])
    actual_components = {element.attrib["ref"]: element for element in tree.findall("./components/comp")}
    if set(actual_components) != set(components):
        errors.append("KiCadネットリストの部品集合が設計定義と不一致: " + str(set(actual_components) ^ set(components)))
    connections = {}
    for net in tree.findall("./nets/net"):
        for node in net.findall("node"):
            connections[(node.attrib["ref"], node.attrib["pin"])] = net.attrib["name"]
    pin_count = 0
    for reference, component in components.items():
        for number, expected in component["nets"].items():
            if expected is not None:
                pin_count += 1
                actual = connections.get((reference, number))
                if actual != expected:
                    errors.append(f"接続不一致: {reference}.{number}: {expected} / {actual}")
            elif (reference, number) in connections and not connections[(reference, number)].startswith("unconnected-"):
                errors.append(f"NC指定ピンに接続あり: {reference}.{number}")
    with paths["bom"].open(encoding="utf-8-sig", newline="") as stream:
        bom = list(csv.DictReader(stream))
    if {row["Reference"] for row in bom} != set(components):
        errors.append("BOMと回路定義の部品番号不一致")
    for row in bom:
        component = components.get(row["Reference"])
        if component and (row["Value"] != component["value"] or row["Sources"] != ";".join(component["sources"]) or row["OpenRisks"] != ";".join(component["risks"]) or row["Footprint"] != component.get("footprint", "")):
            errors.append("BOMの値/出典/リスク/フットプリント不一致: " + row["Reference"])
    independent_expectations = {
        ("A1", "5"): "JJY_DATA", ("A1", "23"): "I2C_SDA", ("A1", "24"): "I2C_SCL",
        ("U3", "14"): "VBAT", ("U3", "15"): "I2C_SDA", ("U3", "16"): "I2C_SCL",
        ("U4", "1"): "GND", ("U4", "2"): "JJY_LDO_IN", ("U4", "3"): "+3V_JJY",
        ("RX1", "1"): "+3V_JJY", ("RX1", "3"): "JJY_PDN2", ("RX1", "4"): "JJY_OUT_RAW", ("RX1", "5"): "JJY_PDN1",
        ("U1", "9"): "SR_CASCADE", ("U2", "14"): "SR_CASCADE", ("U1", "13"): "GND", ("U2", "13"): "GND",
    }
    independent_expectations.update({("U3", str(number)): "GND" for number in range(5, 14)})
    for index in range(4):
        for digit, driver_pin in enumerate([16, 15, 8, 9, 13, 14, 11, 10, 1, 2]):
            tube_pin = [2, 11, 10, 9, 8, 7, 6, 5, 4, 3][digit]
            independent_expectations[(f"U{10 + index}", str(driver_pin))] = f"DIGIT{index}_K{digit}"
            independent_expectations[(f"V{1 + index}", str(tube_pin))] = f"DIGIT{index}_K{digit}"
    for key, expected in independent_expectations.items():
        if connections.get(key) != expected:
            errors.append(f"資料基準ピン対応不一致: {key}: {expected}")
    erc = json.loads(paths["erc"].read_text(encoding="utf-8"))
    violations = [violation for sheet in erc["sheets"] for violation in sheet["violations"]]
    if violations:
        errors.append(f"ERC違反: {len(violations)}")
    unresolved = [reference for reference, component in components.items() if component["risks"] or "TBD" in component["value"]]
    return {"status": "FAIL" if errors else "PASS", "errors": errors, "kicad_version": erc["kicad_version"],
            "schematic_pages": len(erc["sheets"]), "components": len(components), "connected_pins_checked": pin_count,
            "datasheet_pin_checks": len(independent_expectations), "erc_violations": len(violations),
            "candidate_footprints_assigned": sum(bool(component.get("footprint")) for component in components.values()),
            "erc_ignored_checks": erc.get("ignored_checks", []), "unresolved_components": unresolved,
            "manufacturing_release": False,
            "scope": "全体回路図とKiCadネットリスト/BOMの整合性。制御板の候補配置/配線は別検査。HV電圧・保護・実物適合・安全性は未検証。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/phase2")
    parser.add_argument("--require-release", action="store_true")
    args = parser.parse_args()
    cli = find_kicad_cli()
    if not cli:
        print("KiCad CLIなし。KICAD_CLIまたはPATHを設定してください。", file=sys.stderr)
        return 1
    try:
        report = check(args.output, cli)
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, ET.ParseError) as error:
        report = {"status": "FAIL", "errors": [str(error)], "manufacturing_release": False}
    if args.require_release and not report["manufacturing_release"]:
        report["status"] = "FAIL"
        report["errors"].append("未確定設計のため製造リリース不可")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
