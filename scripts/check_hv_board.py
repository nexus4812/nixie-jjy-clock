"""表示/コロン/電源基板のKiCad ERC/DRCと配置/ネットを照合する。製造承認とは別。"""

import argparse
from collections import Counter
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew

from inspect_environment import find_kicad_cli
from kicad_runtime import initialize_gui_runtime
from mechanical import ROOT, load_layout


def coordinate(value):
    return round(pcbnew.ToMM(value), 4)


def check(name, cli):
    stem_name = name + "-board"
    output = ROOT / "build" / stem_name
    output.mkdir(parents=True, exist_ok=True)
    stem = ROOT / f"hardware/pcb/generated_{name}" / stem_name
    errors = []
    log = []
    jobs = [
        ["sch", "erc", "--format", "json", "--severity-all", "--exit-code-violations", "-o", str(output / "erc.json"), str(stem.with_suffix(".kicad_sch"))],
        ["sch", "export", "netlist", "--format", "kicadxml", "-o", str(output / (name + ".xml")), str(stem.with_suffix(".kicad_sch"))],
        ["pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--exit-code-violations", "-o", str(output / "drc.json"), str(stem.with_suffix(".kicad_pcb"))],
        ["pcb", "export", "svg", "--layers", "F.Cu,B.Cu,Edge.Cuts", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "-o", str(output / "routing.svg"), str(stem.with_suffix(".kicad_pcb"))],
    ]
    for arguments in jobs:
        result = subprocess.run([cli, *arguments], capture_output=True, text=True, timeout=120)
        log.append({"arguments": arguments, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            errors.append("CLI検査/出力失敗: " + " ".join(arguments[:3]))
    (output / "cli-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    layout_path = ROOT / f"hardware/pcb/{name}_layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    metadata = json.loads((stem.parent / "board-generation.json").read_text(encoding="utf-8"))
    for key, source in [("layout_sha256", layout_path), ("mechanical_sha256", ROOT / "enclosure/layout.json")]:
        if metadata.get(key) != hashlib.sha256(source.read_bytes()).hexdigest():
            errors.append("基板生成後に正本が変更されている: " + source.name)
    document = ET.parse(output / (name + ".xml"))
    components = {element.attrib["ref"]: element for element in document.findall("./components/comp")}
    expected = {(node.attrib["ref"], node.attrib["pin"]): net.attrib["name"] for net in document.findall("./nets/net") for node in net.findall("node")}
    board = pcbnew.LoadBoard(str(stem.with_suffix(".kicad_pcb")))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    mechanical = load_layout()[layout["mechanical_key"]]
    extra = layout.get("extra_holes", [])
    hole_references = {f"H{index + 1}" for index in range(len(mechanical["mount_holes"]) + len(extra))}
    if set(footprints) != set(layout["components"]) | hole_references:
        errors.append("基板の部品集合不一致")
    pad_count = 0
    for reference, placement in layout["components"].items():
        footprint = footprints.get(reference)
        if footprint is None:
            continue
        if footprint.GetFPIDAsString() != placement["footprint"] or footprint.GetValue() != components[reference].findtext("value"):
            errors.append("フットプリントID/値不一致: " + reference)
        if [coordinate(footprint.GetPosition().x), coordinate(footprint.GetPosition().y)] != placement["at"]:
            errors.append("配置不一致: " + reference)
        if footprint.IsFlipped() != (placement["side"] == "B"):
            errors.append("実装面不一致: " + reference)
        for pad in footprint.Pads():
            if not pad.GetNumber():
                continue
            pad_count += 1
            expected_net = expected.get((reference, pad.GetNumber()), "")
            if expected_net.startswith("unconnected-"):
                expected_net = expected_net.replace("/", "{slash}")
            if pad.GetNetname() != expected_net:
                errors.append(f"パッドネット不一致: {reference}.{pad.GetNumber()}")
    if coordinate(board.GetDesignSettings().GetBoardThickness()) != mechanical["thickness"]:
        errors.append("共通寸法と基板の厚みが不一致")
    actual_holes = sorted([coordinate(pad.GetPosition().x), coordinate(pad.GetPosition().y), coordinate(pad.GetDrillSize().x)] for reference in hole_references if reference in footprints for pad in footprints[reference].Pads())
    expected_holes = sorted([[round(mechanical["width"] / 2 + hole[0], 4), round(mechanical["height"] / 2 - hole[1], 4), mechanical["hole_diameter"]] for hole in mechanical["mount_holes"]] + [[*hole["at"], hole["diameter"]] for hole in extra])
    if actual_holes != expected_holes:
        errors.append("共通寸法と基板の穴が不一致")
    edges = [edge for edge in board.GetDrawings() if edge.GetLayer() == pcbnew.Edge_Cuts]
    corners = {(coordinate(edge.GetStart().x), coordinate(edge.GetStart().y)) for edge in edges}
    if corners != {(0, 0), (mechanical["width"], 0), (mechanical["width"], mechanical["height"]), (0, mechanical["height"])} or len(edges) != 4:
        errors.append("共通寸法と基板の外形が不一致")
    tracks = list(board.GetTracks())
    traces = [track for track in tracks if not isinstance(track, pcbnew.PCB_VIA)]
    if not tracks:
        errors.append("配線なし")
    erc = json.loads((output / "erc.json").read_text(encoding="utf-8"))
    drc = json.loads((output / "drc.json").read_text(encoding="utf-8"))
    erc_violations = [item for sheet in erc["sheets"] for item in sheet["violations"]]
    violations = drc["violations"]
    unconnected = drc.get("unconnected_items", [])
    parity = drc.get("schematic_parity", [])
    if erc_violations or violations or unconnected or parity:
        errors.append("ERC/DRCまたは未配線が残っている")
    report = {"board": name, "status": "FAIL" if errors else "PASS", "errors": errors, "kicad_version": erc["kicad_version"],
              "footprints": len(footprints), "circuit_components": len(layout["components"]), "pads_checked": pad_count,
              "trace_segments": len(traces), "vias": len(tracks) - len(traces), "minimum_track_width_mm": min((coordinate(track.GetWidth()) for track in traces), default=None),
              "erc_violations": len(erc_violations), "erc_types": dict(Counter(item["type"] for item in erc_violations)),
              "drc_violations": len(violations), "drc_types": dict(Counter(item["type"] for item in violations)),
              "unconnected_items": len(unconnected), "schematic_parity_issues": len(parity), "drc_ignored_checks": drc.get("ignored_checks", []),
              "manufacturing_release": False,
              "scope": "幾何とネットの照合のみ。部品定格・絶縁の妥当性・現物適合・実機安全性は未検証。"}
    (output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", choices=["display", "colon", "power", "all"], default="all")
    args = parser.parse_args()
    application = initialize_gui_runtime()
    cli = find_kicad_cli()
    if not cli:
        raise RuntimeError("KiCad CLIなし")
    reports = [check(name, cli) for name in (["display", "colon", "power"] if args.board == "all" else [args.board])]
    print(json.dumps([{key: value for key, value in report.items() if key != "drc_ignored_checks"} for report in reports], ensure_ascii=False, indent=2))
    if application is not None:
        application.Destroy()
    return 0 if all(report["status"] == "PASS" for report in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
