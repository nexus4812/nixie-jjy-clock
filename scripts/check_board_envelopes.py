"""KiCad基板を読み直し、共有JSONの外形・板厚・穴と一致するか検査する。"""

import json
import sys

import pcbnew

from mechanical import ROOT, board_definitions, load_layout, validate
from kicad_runtime import initialize_gui_runtime


def millimeters(coordinate):
    return round(pcbnew.ToMM(coordinate), 4)


def main():
    application = initialize_gui_runtime()
    layout = load_layout()
    report = validate(layout)
    errors = report["errors"]
    checked = []
    for definition in board_definitions(layout):
        path = ROOT / "hardware/mechanical/generated" / (definition["id"] + ".kicad_pcb")
        if not path.exists():
            errors.append("基板なし: " + str(path))
            continue
        board = pcbnew.LoadBoard(str(path))
        edges = [edge for edge in board.GetDrawings() if edge.GetLayer() == pcbnew.Edge_Cuts]
        actual_edges = {tuple(sorted([(millimeters(edge.GetStart().x), millimeters(edge.GetStart().y)),
                                     (millimeters(edge.GetEnd().x), millimeters(edge.GetEnd().y))])) for edge in edges}
        width = definition["width"]
        height = definition["height"]
        corners = [(0, 0), (width, 0), (width, height), (0, height)]
        expected_edges = {tuple(sorted([start, corners[(index + 1) % 4]])) for index, start in enumerate(corners)}
        if actual_edges != expected_edges or len(edges) != 4:
            errors.append("外形不一致: " + definition["id"])
        if millimeters(board.GetDesignSettings().GetBoardThickness()) != definition["thickness"]:
            errors.append("板厚不一致: " + definition["id"])
        actual_holes = []
        for footprint in board.GetFootprints():
            for pad in footprint.Pads():
                if pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    errors.append("想定外の銅箔パッド: " + definition["id"])
                actual_holes.append((millimeters(pad.GetPosition().x), millimeters(pad.GetPosition().y), millimeters(pad.GetDrillSize().x)))
        expected_holes = [(round(width / 2 + hole[0], 4), round(height / 2 - hole[1], 4), definition["hole_diameter"]) for hole in definition["mount_holes"]]
        if sorted(actual_holes) != sorted(expected_holes):
            errors.append("穴座標/径不一致: " + definition["id"])
        if list(board.GetTracks()) or list(board.Zones()):
            errors.append("機械検討基板に想定外の配線/ゾーンあり: " + definition["id"])
        checked.append({"board": definition["id"], "edge_segments": len(edges), "holes": len(actual_holes)})
    report.update({"status": "FAIL" if errors else "PASS", "checked_boards": checked, "manufacturing_release": False})
    output = ROOT / "build/enclosure/board-consistency.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if application is not None:
        application.Destroy()
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
