"""KiCad回路図ネットリストから低電圧制御基板の候補配置を作る。"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pcbnew

from kicad_runtime import initialize_gui_runtime
from mechanical import ROOT, load_layout


def vector(horizontal, vertical):
    return pcbnew.VECTOR2I(pcbnew.FromMM(horizontal), pcbnew.FromMM(vertical))


def footprint_directory(override=None):
    candidates = [override, os.environ.get("KICAD_FOOTPRINT_DIR"), "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints", "/usr/share/kicad/footprints"]
    for candidate in candidates:
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    raise RuntimeError("KiCadフットプリントの場所を--footprintsで指定してください")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--footprints")
    parser.add_argument("--session", type=Path)
    args = parser.parse_args()
    application = initialize_gui_runtime()
    definitions = json.loads((ROOT / "hardware/pcb/control_layout.json").read_text(encoding="utf-8"))
    routing = definitions["routing"]
    mechanical = load_layout()["control_pcb"]
    libraries = footprint_directory(args.footprints)
    output = ROOT / "hardware/pcb/generated"
    build = ROOT / "build/control-board"
    output.mkdir(parents=True, exist_ok=True)
    build.mkdir(parents=True, exist_ok=True)
    document = ET.parse(build / "control.xml")
    components = {element.attrib["ref"]: element for element in document.findall("./components/comp")}
    if set(components) != set(definitions["components"]):
        raise ValueError("制御基板の部品集合とネットリストが不一致")
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    settings = board.GetDesignSettings()
    settings.SetBoardThickness(pcbnew.FromMM(mechanical["thickness"]))
    settings.m_MinClearance = pcbnew.FromMM(routing["clearance"])
    settings.m_TrackMinWidth = pcbnew.FromMM(routing["minimum_track_width"])
    settings.m_CopperEdgeClearance = pcbnew.FromMM(0.5)
    settings.m_HoleClearance = pcbnew.FromMM(0.25)
    settings.m_ViasMinAnnularWidth = pcbnew.FromMM(0.15)
    settings.m_MinThroughDrill = pcbnew.FromMM(0.3)
    default_class = settings.m_NetSettings.GetDefaultNetclass()
    default_class.SetClearance(pcbnew.FromMM(routing["autorouter_clearance"]))
    default_class.SetTrackWidth(pcbnew.FromMM(routing["nominal_track_width"]))
    default_class.SetViaDiameter(pcbnew.FromMM(routing["via_diameter"]))
    default_class.SetViaDrill(pcbnew.FromMM(routing["via_drill"]))
    nets = {}
    connections = {}
    for net in document.findall("./nets/net"):
        name = net.attrib["name"]
        if name.startswith("unconnected-"):
            # KiCad XMLはピン名中の/を復元するが、PCB照合は{slash}表現を要求する。
            name = name.replace("/", "{slash}")
        if name.startswith(("HV_", "12V", "NEON")) and name != "HV_ENABLE":
            raise ValueError("低電圧基板へ禁止ネットが混入: " + name)
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
        for node in net.findall("node"):
            connections[(node.attrib["ref"], node.attrib["pin"])] = name
    metadata = {"status": "PLACEMENT_CANDIDATE_NOT_FOR_MANUFACTURE", "revision": definitions["revision"],
                "layout_sha256": hashlib.sha256((ROOT / "hardware/pcb/control_layout.json").read_bytes()).hexdigest(),
                "mechanical_sha256": hashlib.sha256((ROOT / "enclosure/layout.json").read_bytes()).hexdigest(),
                "footprints": [], "unassigned_nets": [], "layers": 2, "manufacturing_release": False}
    for reference, placement in definitions["components"].items():
        library, name = placement["footprint"].split(":")
        footprint = pcbnew.FootprintLoad(str(libraries / (library + ".pretty")), name)
        if footprint is None:
            raise ValueError("フットプリントなし: " + placement["footprint"])
        footprint.SetReference(reference)
        footprint.SetValue(components[reference].findtext("value"))
        for field in components[reference].findall("property"):
            footprint.SetField(field.attrib["name"], field.attrib["value"])
            footprint.GetField(field.attrib["name"]).SetVisible(False)
        footprint.SetFPID(pcbnew.LIB_ID(library, name))
        footprint.SetPosition(vector(*placement["at"]))
        footprint.SetOrientationDegrees(placement["rotation"])
        timestamp = components[reference].findtext("tstamps").split()[0]
        sheet_path = components[reference].find("sheetpath").attrib["tstamps"]
        path = pcbnew.KIID_PATH()
        for identifier in [*sheet_path.strip("/").split("/"), timestamp]:
            if identifier:
                path.push_back(pcbnew.KIID(identifier))
        footprint.SetPath(path)
        footprint.Value().SetVisible(False)
        footprint.Reference().SetVisible(False)
        for pad in footprint.Pads():
            net = connections.get((reference, pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        actual_pins = {pad.GetNumber() for pad in footprint.Pads()}
        source = components[reference].find("libsource")
        library_part = next(part for part in document.findall("./libparts/libpart") if part.attrib["lib"] == source.attrib["lib"] and part.attrib["part"] == source.attrib["part"])
        expected_pins = {pin.attrib["num"] for pin in library_part.findall("./pins/pin")}
        if actual_pins != expected_pins:
            raise ValueError("シンボルとフットプリントの全ピン番号が不一致: " + reference)
        board.Add(footprint)
        metadata["footprints"].append({"reference": reference, "library_id": placement["footprint"],
                                       "library_file_sha256": hashlib.sha256((libraries / (library + ".pretty") / (name + ".kicad_mod")).read_bytes()).hexdigest(),
                                       "pad_numbers": sorted(actual_pins), "at_mm": placement["at"], "rotation_deg": placement["rotation"]})
    width = mechanical["width"]
    height = mechanical["height"]
    corners = [(0, 0), (width, 0), (width, height), (0, height)]
    for index, start in enumerate(corners):
        edge = pcbnew.PCB_SHAPE(board)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetStart(vector(*start))
        edge.SetEnd(vector(*corners[(index + 1) % 4]))
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(pcbnew.FromMM(0.05))
        board.Add(edge)
    for index, hole in enumerate(mechanical["mount_holes"]):
        footprint = pcbnew.FootprintLoad(str(libraries / "MountingHole.pretty"), "MountingHole_3.2mm_M3")
        if footprint is None:
            raise ValueError("M3穴フットプリントなし")
        footprint.SetReference(f"H{index + 1}")
        footprint.SetValue("M3_NPTH_DRAFT")
        footprint.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        footprint.SetPosition(vector(width / 2 + hole[0], height / 2 - hole[1]))
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        for pad in footprint.Pads():
            if round(pcbnew.ToMM(pad.GetDrillSize().x), 4) != mechanical["hole_diameter"]:
                raise ValueError("穴フットプリントと共通寸法の径が不一致")
        board.Add(footprint)
    for constraint in definitions["routing_keepouts"]:
        placement = definitions["components"][constraint["reference"]]
        zone = pcbnew.ZONE(board)
        zone.SetIsRuleArea(True)
        zone.SetZoneName(constraint["name"])
        zone.SetLayerSet(pcbnew.LSET.AllCuMask(2))
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowPads(False)
        polygon = zone.Outline()
        polygon.NewOutline()
        width, height = constraint["size"]
        radians = math.radians(placement["rotation"])
        for horizontal, vertical in [(-width / 2,-height / 2),(width / 2,-height / 2),(width / 2,height / 2),(-width / 2,height / 2)]:
            position = vector(placement["at"][0] + horizontal * math.cos(radians) + vertical * math.sin(radians),
                              placement["at"][1] - horizontal * math.sin(radians) + vertical * math.cos(radians))
            polygon.Append(position.x, position.y)
        board.Add(zone)
    for definition in definitions["silkscreen"]:
        label = pcbnew.PCB_TEXT(board)
        label.SetText(definition["text"])
        label.SetPosition(vector(*definition["at"]))
        label.SetTextSize(vector(0.8, 0.8))
        label.SetTextThickness(pcbnew.FromMM(0.12))
        label.SetLayer(pcbnew.F_SilkS)
        board.Add(label)
    for definition in definitions["seed_tracks"]:
        for start, finish in zip(definition["points"], definition["points"][1:]):
            track = pcbnew.PCB_TRACK(board)
            track.SetStart(vector(*start))
            track.SetEnd(vector(*finish))
            track.SetWidth(pcbnew.FromMM(definition["width"]))
            track.SetLayer(pcbnew.F_Cu if definition["layer"] == "F.Cu" else pcbnew.B_Cu)
            track.SetNet(nets[definition["net"]])
            board.Add(track)
    board.BuildConnectivity()
    dsn = build / "control-board.dsn"
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN出力失敗")
    if args.session:
        receipt_path = args.session.with_suffix(".routing.json")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt["dsn_sha256"] != hashlib.sha256(dsn.read_bytes()).hexdigest():
            raise ValueError("SESの入力と現在の配置/接続/制約が不一致。再配線が必要です")
        if receipt["ses_sha256"] != hashlib.sha256(args.session.read_bytes()).hexdigest():
            raise ValueError("SESと配線記録のハッシュ不一致")
        if not pcbnew.ImportSpecctraSES(board, str(args.session.resolve())):
            raise RuntimeError("SES取り込み失敗")
        metadata["status"] = "ROUTED_CANDIDATE_NOT_FOR_MANUFACTURE"
        metadata["routing"] = {key: receipt[key] for key in ("router", "jar_sha256", "dsn_sha256", "ses_sha256")}
        widened = 0
        for track in board.GetTracks():
            if not isinstance(track, pcbnew.PCB_VIA) and track.GetWidth() < pcbnew.FromMM(routing["minimum_track_width"]):
                track.SetWidth(pcbnew.FromMM(routing["minimum_track_width"]))
                widened += 1
        # 取り込み後の拡幅も含め、実際の銅箔をKiCad DRCで再検査する。
        metadata["tracks_widened_to_minimum"] = widened
    destination = output / "control-board.kicad_pcb"
    if not pcbnew.SaveBoard(str(destination), board):
        raise RuntimeError("基板保存失敗")
    metadata["tracks_and_vias"] = len(list(board.GetTracks()))
    (output / "board-generation.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(metadata['footprints'])} candidate footprints; tracks/vias={metadata['tracks_and_vias']}")
    if application is not None:
        application.Destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
