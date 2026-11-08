"""KiCad回路図ネットリストから表示/コロン/電源基板の候補配置を作る。製造承認ではない。"""

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
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


def apply_netclass_clearances(dsn, definitions, net_names):
    """DSNへHV/カソード用クラスを追加し、自動配線にHV間隔を伝える。"""
    routing = definitions["routing"]
    text = dsn.read_text(encoding="utf-8")
    groups = {"HV": [], "CATHODE": []}
    for name in net_names:
        if name in definitions["hv_nets"]:
            groups["HV"].append(name)
        elif any(fnmatch.fnmatch(name, pattern) for pattern in definitions["cathode_patterns"]):
            groups["CATHODE"].append(name)
    clearance = {"HV": routing.get("dsn_hv_clearance", routing["hv_lv_clearance"]) * 1000, "CATHODE": routing.get("dsn_cathode_clearance", routing["cathode_lv_clearance"]) * 1000}
    match = re.search(r'\(class\s+"?kicad_default"?(?P<body>.*?)\(circuit', text, re.S)
    if not match:
        raise RuntimeError("DSNの既定ネットクラスが見つからない")
    tail = text[match.end():]
    circuit = tail[:tail.index("(rule")]
    blocks = ""
    body = match.group("body")
    for group, names in groups.items():
        if not names:
            continue
        for name in names:
            body = re.sub(r'(?<=[\s"])' + re.escape(f'"{name}"') + r'(?=[\s)])', "", body) if f'"{name}"' in body else re.sub(r'(?<=\s)' + re.escape(name) + r'(?=[\s)])', "", body)
        quoted = " ".join(f'"{name}"' for name in names)
        blocks += f'(class {group} {quoted} (circuit{circuit}(rule (width {routing["nominal_track_width"] * 1000:g}) (clearance {clearance[group]:g})))\n    '
    text = text[:match.start("body")] + body + text[match.end("body"):]
    text = text[:match.start()] + blocks + text[match.start():]
    inset = routing.get("dsn_boundary_inset", 0) * 1000
    if inset:
        match = re.search(r"\(boundary\s*\(path\s+pcb\s+\S+\s+(?P<points>[-\d.\s]+)\)", text)
        if not match:
            raise RuntimeError("DSNの基板外形が見つからない")
        values = [float(value) for value in match.group("points").split()]
        xs, ys = values[0::2], values[1::2]
        low_x, high_x, low_y, high_y = min(xs), max(xs), min(ys), max(ys)
        moved = []
        for horizontal, vertical in zip(xs, ys):
            moved += [horizontal + inset if horizontal == low_x else horizontal - inset, vertical + inset if vertical == low_y else vertical - inset]
        text = text[:match.start("points")] + " ".join(f"{value:g}" for value in moved) + "  " + text[match.end("points"):]
    dsn.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", choices=["display", "colon", "power"], required=True)
    parser.add_argument("--footprints")
    parser.add_argument("--session", type=Path)
    args = parser.parse_args()
    application = initialize_gui_runtime()
    layout_path = ROOT / f"hardware/pcb/{args.board}_layout.json"
    definitions = json.loads(layout_path.read_text(encoding="utf-8"))
    routing = definitions["routing"]
    mechanical = load_layout()[definitions["mechanical_key"]]
    libraries = footprint_directory(args.footprints)
    stem = args.board + "-board"
    output = ROOT / f"hardware/pcb/generated_{args.board}"
    build = ROOT / "build" / stem
    build.mkdir(parents=True, exist_ok=True)
    document = ET.parse(build / (args.board + ".xml"))
    components = {element.attrib["ref"]: element for element in document.findall("./components/comp")}
    if set(components) != set(definitions["components"]):
        raise ValueError(f"部品集合とネットリストが不一致: {set(components) ^ set(definitions['components'])}")
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
            name = name.replace("/", "{slash}")
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
        for node in net.findall("node"):
            connections[(node.attrib["ref"], node.attrib["pin"])] = name
    metadata = {"status": "PLACEMENT_CANDIDATE_NOT_FOR_MANUFACTURE", "revision": definitions["revision"],
                "layout_sha256": hashlib.sha256(layout_path.read_bytes()).hexdigest(),
                "mechanical_sha256": hashlib.sha256((ROOT / "enclosure/layout.json").read_bytes()).hexdigest(),
                "footprints": [], "layers": 2, "manufacturing_release": False}
    width, height = mechanical["width"], mechanical["height"]
    for reference, placement in definitions["components"].items():
        library, name = placement["footprint"].split(":")
        library_path = ROOT / "hardware/pcb/JJYClock.pretty" if library == "JJYClock" else libraries / (library + ".pretty")
        footprint = pcbnew.FootprintLoad(str(library_path), name)
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
        actual_pins = {pad.GetNumber() for pad in footprint.Pads() if pad.GetNumber()}
        source = components[reference].find("libsource")
        library_part = next(part for part in document.findall("./libparts/libpart") if part.attrib["lib"] == source.attrib["lib"] and part.attrib["part"] == source.attrib["part"])
        expected_pins = {pin.attrib["num"] for pin in library_part.findall("./pins/pin")}
        if actual_pins != expected_pins:
            raise ValueError("シンボルとフットプリントの全ピン番号が不一致: " + reference)
        board.Add(footprint)
        if placement["side"] == "B":
            footprint.Flip(footprint.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        metadata["footprints"].append({"reference": reference, "library_id": placement["footprint"],
                                       "library_file_sha256": hashlib.sha256((library_path / (name + ".kicad_mod")).read_bytes()).hexdigest(),
                                       "pad_numbers": sorted(actual_pins), "at_mm": placement["at"], "rotation_deg": placement["rotation"], "side": placement["side"]})
    corners = [(0, 0), (width, 0), (width, height), (0, height)]
    for index, start in enumerate(corners):
        edge = pcbnew.PCB_SHAPE(board)
        edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
        edge.SetStart(vector(*start))
        edge.SetEnd(vector(*corners[(index + 1) % 4]))
        edge.SetLayer(pcbnew.Edge_Cuts)
        edge.SetWidth(pcbnew.FromMM(0.05))
        board.Add(edge)
    holes = [([width / 2 + hole[0], height / 2 - hole[1]], mechanical["hole_diameter"]) for hole in mechanical["mount_holes"]]
    holes += [(hole["at"], hole["diameter"]) for hole in definitions.get("extra_holes", [])]
    for index, (position, diameter) in enumerate(holes):
        name = "MountingHole_3.2mm_M3" if diameter == 3.2 else "MountingHole_2.2mm_M2"
        footprint = pcbnew.FootprintLoad(str(libraries / "MountingHole.pretty"), name)
        if footprint is None:
            raise ValueError("穴フットプリントなし: " + name)
        footprint.SetReference(f"H{index + 1}")
        footprint.SetValue("NPTH_DRAFT")
        footprint.SetAttributes(pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        footprint.SetPosition(vector(*position))
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        for pad in footprint.Pads():
            if round(pcbnew.ToMM(pad.GetDrillSize().x), 4) != diameter:
                raise ValueError("穴フットプリントと共通寸法の径が不一致")
        board.Add(footprint)
    for definition in definitions["silkscreen"]:
        label = pcbnew.PCB_TEXT(board)
        label.SetText(definition["text"])
        label.SetPosition(vector(*definition["at"]))
        label.SetTextSize(vector(0.9, 0.9))
        label.SetTextThickness(pcbnew.FromMM(0.13))
        label.SetLayer(pcbnew.F_SilkS if definition["layer"] == "F" else pcbnew.B_SilkS)
        label.SetMirrored(definition["layer"] == "B")
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
    for definition in definitions.get("copper_zones", []):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(pcbnew.F_Cu if definition["layer"] == "F.Cu" else pcbnew.B_Cu)
        zone.SetNet(nets[definition["net"]])
        zone.SetLocalClearance(pcbnew.FromMM(definition["clearance"]))
        zone.SetMinThickness(pcbnew.FromMM(0.3))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        polygon = zone.Outline()
        polygon.NewOutline()
        margin = definition["edge_margin"]
        for corner in [(margin, margin), (width - margin, margin), (width - margin, height - margin), (margin, height - margin)]:
            point = vector(*corner)
            polygon.Append(point.x, point.y)
        board.Add(zone)
    board.BuildConnectivity()
    dsn = build / (stem + ".dsn")
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN出力失敗")
    apply_netclass_clearances(dsn, definitions, list(nets))
    if args.session:
        receipt = json.loads(args.session.with_suffix(".routing.json").read_text(encoding="utf-8"))
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
        metadata["tracks_widened_to_minimum"] = widened
        # 自動配線が片面にしか接続しないビアを残すことがある。接続に寄与しないので除去し、DRCで再検査する。
        removed = 0
        for via in [item for item in board.GetTracks() if isinstance(item, pcbnew.PCB_VIA)]:
            position = via.GetPosition()
            attached = {track.GetLayer() for track in board.GetTracks() if not isinstance(track, pcbnew.PCB_VIA) and track.GetNetCode() == via.GetNetCode() and (track.GetStart() == position or track.GetEnd() == position)}
            if len(attached) < 2:
                board.Remove(via)
                removed += 1
        metadata["dangling_vias_removed"] = removed
    if definitions.get("copper_zones"):
        # 配線後の銅箔でベタを計算する。隙間はDRCで再検査する。
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if not pcbnew.SaveBoard(str(output / (stem + ".kicad_pcb")), board):
        raise RuntimeError("基板保存失敗")
    metadata["tracks_and_vias"] = len(list(board.GetTracks()))
    (output / "board-generation.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dump = {reference: {pad.GetNumber(): [round(pcbnew.ToMM(pad.GetPosition().x), 3), round(pcbnew.ToMM(pad.GetPosition().y), 3), pad.GetNetname()] for pad in footprint.Pads()}
            for reference, footprint in ((fp.GetReference(), fp) for fp in board.GetFootprints())}
    (build / "pads.json").write_text(json.dumps(dump, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {len(metadata['footprints'])} candidate footprints on {stem}; tracks/vias={metadata['tracks_and_vias']}")
    if application is not None:
        application.Destroy()
    return 0


if __name__ == "__main__":
    sys.exit(main())
