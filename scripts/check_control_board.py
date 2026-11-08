"""実基板の配置・パッドネット・穴とKiCad ERC/DRCを照合する。製造承認とは別。"""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew

from inspect_environment import find_kicad_cli
from kicad_runtime import initialize_gui_runtime
from mechanical import ROOT, load_layout


def coordinate(value):
    return round(pcbnew.ToMM(value), 4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-release", action="store_true")
    args = parser.parse_args()
    application = initialize_gui_runtime()
    cli = find_kicad_cli()
    if not cli:
        raise RuntimeError("KiCad CLIなし")
    output = ROOT / "build/control-board"
    output.mkdir(parents=True, exist_ok=True)
    stem = ROOT / "hardware/pcb/generated/control-board"
    log = []
    errors = []
    jobs = [
        ["sch", "erc", "--format", "json", "--severity-all", "--exit-code-violations", "-o", str(output / "erc.json"), str(stem.with_suffix(".kicad_sch"))],
        ["sch", "export", "netlist", "--format", "kicadxml", "-o", str(output / "control.xml"), str(stem.with_suffix(".kicad_sch"))],
        ["pcb", "drc", "--format", "json", "--severity-all", "--schematic-parity", "--exit-code-violations", "-o", str(output / "drc.json"), str(stem.with_suffix(".kicad_pcb"))],
        ["pcb", "export", "svg", "--layers", "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "-o", str(output / "routing.svg"), str(stem.with_suffix(".kicad_pcb"))],
        ["pcb", "export", "svg", "--layers", "F.Fab,Edge.Cuts", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "--sketch-pads-on-fab-layers", "-o", str(output / "assembly.svg"), str(stem.with_suffix(".kicad_pcb"))],
    ]
    for arguments in jobs:
        result = subprocess.run([cli, *arguments], capture_output=True, text=True, timeout=90)
        log.append({"arguments": arguments, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode:
            errors.append("CLI検査/出力失敗: " + " ".join(arguments[:3]))
    (output / "cli-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    layout = json.loads((ROOT / "hardware/pcb/control_layout.json").read_text(encoding="utf-8"))
    metadata = json.loads((stem.parent / "board-generation.json").read_text(encoding="utf-8"))
    for key, source in [("layout_sha256", "hardware/pcb/control_layout.json"), ("mechanical_sha256", "enclosure/layout.json")]:
        if metadata.get(key) != hashlib.sha256((ROOT / source).read_bytes()).hexdigest():
            errors.append("基板生成後に正本が変更されている: " + source)
    document = ET.parse(output / "control.xml")
    components = {element.attrib["ref"]: element for element in document.findall("./components/comp")}
    expected = {}
    for net in document.findall("./nets/net"):
        for node in net.findall("node"):
            expected[(node.attrib["ref"], node.attrib["pin"])] = net.attrib["name"]
    board = pcbnew.LoadBoard(str(stem.with_suffix(".kicad_pcb")))
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    if set(footprints) != set(layout["components"]) | {"H1", "H2", "H3", "H4"}:
        errors.append("基板の部品集合不一致")
    pad_count = 0
    for reference, placement in layout["components"].items():
        footprint = footprints.get(reference)
        if footprint is None:
            continue
        if footprint.GetFPIDAsString() != placement["footprint"] or footprint.GetValue() != components[reference].findtext("value"):
            errors.append("フットプリントID/値不一致: " + reference)
        actual_position = [coordinate(footprint.GetPosition().x), coordinate(footprint.GetPosition().y)]
        if actual_position != placement["at"] or footprint.GetOrientationDegrees() % 360 != placement["rotation"] % 360:
            errors.append("配置不一致: " + reference)
        for pad in footprint.Pads():
            pad_count += 1
            expected_net = expected.get((reference, pad.GetNumber()), "")
            if expected_net.startswith("unconnected-"):
                expected_net = expected_net.replace("/", "{slash}")
            if pad.GetNetname() != expected_net:
                errors.append(f"パッドネット不一致: {reference}.{pad.GetNumber()}")
    mechanical = load_layout()["control_pcb"]
    if coordinate(board.GetDesignSettings().GetBoardThickness()) != mechanical["thickness"]:
        errors.append("共通寸法と基板の厚みが不一致")
    zones = {zone.GetZoneName(): zone for zone in board.Zones()}
    if set(zones) != {constraint["name"] for constraint in layout["routing_keepouts"]}:
        errors.append("RTC配線禁止領域の集合不一致")
    for constraint in layout["routing_keepouts"]:
        zone = zones.get(constraint["name"])
        if zone is None:
            continue
        if not (zone.GetIsRuleArea() and zone.GetDoNotAllowTracks() and zone.GetDoNotAllowVias() and not zone.GetDoNotAllowPads()
                and set(zone.GetLayerSet().Seq()) == {pcbnew.F_Cu, pcbnew.B_Cu}):
            errors.append("RTC配線禁止領域の設定不一致")
        placement = layout["components"][constraint["reference"]]
        width, height = constraint["size"]
        angle = math.radians(placement["rotation"])
        expected_corners = {(round(placement["at"][0] + x * math.cos(angle) + y * math.sin(angle), 4),
                             round(placement["at"][1] - x * math.sin(angle) + y * math.cos(angle), 4))
                            for x, y in [(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)]}
        actual_corners = {(coordinate(point.x), coordinate(point.y)) for point in zone.Outline().COutline(0).CPoints()}
        if actual_corners != expected_corners:
            errors.append("RTC配線禁止領域の座標不一致")
    actual_holes = []
    for index in range(4):
        for pad in footprints[f"H{index + 1}"].Pads():
            actual_holes.append([coordinate(pad.GetPosition().x), coordinate(pad.GetPosition().y), coordinate(pad.GetDrillSize().x)])
    expected_holes = [[mechanical["width"] / 2 + hole[0], mechanical["height"] / 2 - hole[1], mechanical["hole_diameter"]] for hole in mechanical["mount_holes"]]
    if sorted(actual_holes) != sorted(expected_holes):
        errors.append("共通寸法と基板の穴が不一致")
    edges = [edge for edge in board.GetDrawings() if edge.GetLayer() == pcbnew.Edge_Cuts]
    corners = {(coordinate(edge.GetStart().x), coordinate(edge.GetStart().y)) for edge in edges}
    if corners != {(0, 0), (mechanical["width"], 0), (mechanical["width"], mechanical["height"]), (0, mechanical["height"])} or len(edges) != 4:
        errors.append("共通寸法と基板の外形が不一致")
    tracks = list(board.GetTracks())
    traces = [track for track in tracks if not isinstance(track, pcbnew.PCB_VIA)]
    vias = [track for track in tracks if isinstance(track, pcbnew.PCB_VIA)]
    if not tracks:
        errors.append("配線なし")
    for track in tracks:
        name = track.GetNetname()
        if name.startswith(("HV_", "12V", "NEON")) and name != "HV_ENABLE":
            errors.append("低電圧基板にHVネット混入: " + name)
    erc = json.loads((output / "erc.json").read_text(encoding="utf-8"))
    drc = json.loads((output / "drc.json").read_text(encoding="utf-8"))
    erc_violations = [item for sheet in erc["sheets"] for item in sheet["violations"]]
    violations = drc["violations"]
    unconnected = drc.get("unconnected_items", [])
    parity = drc.get("schematic_parity", [])
    if erc_violations or violations or unconnected or parity:
        errors.append("ERC/DRCまたは未配線が残っている")
    if args.require_release:
        errors.append("候補フットプリント・現物未照合のため製造リリース不可")
    report = {"status": "FAIL" if errors else "PASS", "errors": errors, "kicad_version": erc["kicad_version"],
              "footprints": len(footprints), "circuit_components": len(layout["components"]), "pads_checked": pad_count,
              "tracks_and_vias": len(tracks), "erc_violations": len(erc_violations), "drc_violations": len(violations),
              "trace_segments": len(traces), "vias": len(vias), "minimum_track_width_mm": min((coordinate(track.GetWidth()) for track in traces), default=None),
              "rtc_keepouts_checked": len(zones),
              "drc_types": dict(Counter(item["type"] for item in violations)), "unconnected_items": len(unconnected),
              "schematic_parity_issues": len(parity), "drc_ignored_checks": drc.get("ignored_checks", []),
              "mechanical_holes": actual_holes, "manufacturing_release": False,
              "scope": "低電圧制御基板のみ。実物・部品定格/熱・HV表示/電源板・受信性能・ケース部品高さは未検証。"}
    (output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if application is not None:
        application.Destroy()
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
