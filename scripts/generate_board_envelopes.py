"""KiCad付属Python/pcbnewで、共有寸法による無配線の機械検討用基板を生成する。"""

import json
import sys

import pcbnew

from mechanical import ROOT, board_definitions, load_layout, validate
from kicad_runtime import initialize_gui_runtime


def vector(horizontal, vertical):
    return pcbnew.VECTOR2I(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))


def main():
    application = initialize_gui_runtime()
    layout = load_layout()
    report = validate(layout)
    if report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    output = ROOT / "hardware/mechanical/generated"
    output.mkdir(parents=True, exist_ok=True)
    metadata = {"revision": layout["revision"], "kicad": pcbnew.GetBuildVersion(), "status": "MECHANICAL_ONLY_UNROUTED", "boards": []}
    for definition in board_definitions(layout):
        board = pcbnew.BOARD()
        board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(definition["thickness"]))
        width = definition["width"]
        height = definition["height"]
        corners = [(0, 0), (width, 0), (width, height), (0, height)]
        for index, start in enumerate(corners):
            edge = pcbnew.PCB_SHAPE(board)
            edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
            edge.SetStart(vector(*start))
            edge.SetEnd(vector(*corners[(index + 1) % len(corners)]))
            edge.SetLayer(pcbnew.Edge_Cuts)
            edge.SetWidth(pcbnew.FromMM(0.05))
            board.Add(edge)
        for index, hole in enumerate(definition["mount_holes"]):
            footprint = pcbnew.FOOTPRINT(board)
            footprint.SetReference(f"H{index + 1}")
            footprint.SetValue("MECHANICAL_DRAFT_NPTH")
            footprint.SetPosition(vector(width / 2 + hole[0], height / 2 - hole[1]))
            pad = pcbnew.PAD(footprint)
            pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
            pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
            pad.SetSize(vector(definition["hole_diameter"], definition["hole_diameter"]))
            pad.SetDrillSize(vector(definition["hole_diameter"], definition["hole_diameter"]))
            footprint.Add(pad)
            board.Add(footprint)
        filename = definition["id"] + ".kicad_pcb"
        if not pcbnew.SaveBoard(str(output / filename), board):
            raise RuntimeError("KiCad基板保存失敗: " + filename)
        metadata["boards"].append({"id": definition["id"], "file": filename, "size_mm": [width, height],
                                   "assembly_center_mm": definition["center"], "assembly_plane": definition["plane"],
                                   "holes_pcb_mm": [[width / 2 + hole[0], height / 2 - hole[1]] for hole in definition["mount_holes"]]})
    (output / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(metadata['boards'])} MECHANICAL-ONLY boards; no circuit footprints or routing")
    if application is not None:
        application.Destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
