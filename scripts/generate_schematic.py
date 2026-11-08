"""確認済みのKiCad S式書式でレビュー用階層回路図を生成する。"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "nixie-jjy-clock"
NAMESPACE = uuid.UUID("73bddc36-ed4a-4b27-9b17-5d7224895edc")


def quoted(value):
    return json.dumps(str(value), ensure_ascii=False)


def identity(value):
    return str(uuid.uuid5(NAMESPACE, value))


def effect(size=1.0, hidden=False, justify=""):
    return f'(effects (font (size {size} {size}))' + (' (hide yes)' if hidden else '') + (f' (justify {justify})' if justify else '') + ')'


def property_text(name, value, horizontal, vertical, hidden=False):
    return f'(property {quoted(name)} {quoted(value)} (at {horizontal:g} {vertical:g} 0) {effect(hidden=hidden)})'


def geometry(definition):
    count = max(len(definition["left"]), len(definition["right"]), 1)
    half_height = max(5.08, (count + 1) * 1.27)
    half_width = 16.51 if count > 12 else 12.7
    if definition.get("style") in ("resistor", "capacitor", "diode", "led", "switch", "battery", "fuse"):
        half_width, half_height = 2.54, 2.54
    pins = []
    for side in ("left", "right"):
        rows = definition[side]
        for index, pin in enumerate(rows):
            pins.append({**pin, "horizontal": (-1 if side == "left" else 1) * (half_width + 5.08),
                         "vertical": (len(rows) - 1) * 1.27 - index * 2.54,
                         "angle": 0 if side == "left" else 180, "side": side})
    return half_width, half_height, pins


def polyline(points):
    locations = " ".join(f'(xy {horizontal:g} {vertical:g})' for horizontal, vertical in points)
    return f'(polyline (pts {locations}) (stroke (width 0.254) (type default)) (fill (type none)))'


def symbol_definition(name, definition, library_id=False):
    half_width, half_height, pins = geometry(definition)
    symbol_name = "JJYClock:" + name if library_id else name
    content = [f'(symbol {quoted(symbol_name)} (pin_names (offset 0.762)) (in_bom yes) (on_board yes)',
               property_text("Reference", "U", 0, half_height + 3), property_text("Value", name, 0, -half_height - 3),
               property_text("Footprint", "", 0, 0, True), property_text("Datasheet", "", 0, 0, True),
               f'(symbol {quoted(name + "_0_1")}']
    style = definition.get("style", "block")
    if style in ("capacitor", "battery"):
        content.extend([polyline([(-half_width, 0), (-0.8, 0)]), polyline([(0.8, 0), (half_width, 0)]),
                        polyline([(-0.8, -2.54), (-0.8, 2.54)]), polyline([(0.8, -2.54), (0.8, 2.54)])])
        if style == "battery":
            content[-1] = polyline([(0.8, -1.27), (0.8, 1.27)])
    elif style in ("diode", "led"):
        content.extend([polyline([(-2.54, 0), (-1.27, 0)]), polyline([(1.27, 0), (2.54, 0)]),
                        polyline([(-1.27, -2.54), (-1.27, 2.54)]), polyline([(-1.27, 0), (1.27, 2.54), (1.27, -2.54), (-1.27, 0)])])
        if style == "led":
            content.extend([polyline([(-0.5, 3), (-2, 4.5), (-1, 4.25)]), polyline([(1, 3.5), (-0.5, 5), (0.5, 4.75)])])
    elif style == "switch":
        content.extend([polyline([(-2.54, 0), (-1.27, 0), (1.27, 2.54)]), polyline([(1.27, 0), (2.54, 0)])])
    else:
        content.append(f'(rectangle (start {-half_width:g} {half_height:g}) (end {half_width:g} {-half_height:g}) (stroke (width 0.254) (type default)) (fill (type background)))')
        if style == "fuse":
            content.append(polyline([(-2.54, 0), (2.54, 0)]))
    content.extend([')', f'(symbol {quoted(name + "_1_1")}'])
    for pin in pins:
        content.append(f'(pin {pin["kind"]} line (at {pin["horizontal"]:g} {pin["vertical"]:g} {pin["angle"]}) (length 5.08) (name {quoted(pin["name"])} {effect(0.9)}) (number {quoted(pin["number"])} {effect(0.9)}))')
    content.extend([')', ')'])
    return "\n".join(content)


def text(content, horizontal, vertical, size=1.27):
    return f'(text {quoted(content)} (at {horizontal:g} {vertical:g} 0) {effect(size, justify="left")} (uuid {quoted(identity(content + str(horizontal) + str(vertical)))}))'


def header(document_id, title, paper="A2"):
    return [f'(kicad_sch (version 20250114) (generator "nixie_jjy_clock") (generator_version "0.1") (uuid {quoted(document_id)}) (paper {quoted(paper)})',
            f'(title_block (title {quoted(title)}) (date "2026-11-08") (rev "phase2-r0-DRAFT") (company "nixie-jjy-clock") (comment 1 "REVIEW ONLY - NOT FOR MANUFACTURE - R01/R02/R04/R06 OPEN"))']


def render_sheet(sheet, symbols, root_id, sheet_id):
    compact = len(sheet["components"]) <= 9
    columns = 3 if compact else 4
    content = header(identity("document/" + sheet["name"]), sheet["title"], "A4" if compact else "A3")
    used = sorted({component["symbol"] for component in sheet["components"]})
    content.append('(lib_symbols ' + "\n".join(symbol_definition(name, symbols[name], True) for name in used) + ')')
    content.append(text(sheet["title"], 20, 20, 2.0))
    content.append(text(sheet["note"], 20, 28, 1.1))
    content.append(text("同名のネットラベルは階層を越えて接続。未確定値/TBDは発注不可。端子配置はSources欄を参照。", 20, 34, 1.0))
    for index, component in enumerate(sheet["components"]):
        horizontal = 48.26 + (index % columns) * (88.9 if compact else 99.06)
        vertical = 62.23 + (index // columns) * (43.18 if compact else 36.83)
        name = component["symbol"]
        half_width, half_height, pins = geometry(symbols[name])
        expected = {pin["number"] for pin in pins}
        if set(component["nets"]) != expected:
            raise ValueError(f'{component["reference"]}: ピン定義不一致 {expected ^ set(component["nets"])}')
        reference = component["reference"]
        identifier = identity("component/" + reference)
        content.extend([f'(symbol (lib_id {quoted("JJYClock:" + name)}) (at {horizontal:g} {vertical:g} 0) (unit 1) (in_bom {"no" if reference.startswith("#") else "yes"}) (on_board {"no" if reference.startswith("#") else "yes"}) (dnp no) (uuid {quoted(identifier)})',
                        property_text("Reference", reference, horizontal, vertical - half_height - 4),
                        property_text("Value", component["value"], horizontal, vertical - half_height - 1.5),
                        property_text("Footprint", component.get("footprint", ""), horizontal, vertical, True),
                        property_text("Datasheet", "", horizontal, vertical, True),
                        property_text("Sources", ";".join(component["sources"]), horizontal, vertical, True),
                        property_text("OpenRisks", ";".join(component["risks"]), horizontal, vertical, True),
                        property_text("ReviewStatus", "HOLD" if component["risks"] or "TBD" in component["value"] else "DRAFT", horizontal, vertical, True),
                        property_text("Board", component.get("board", "offboard_or_pending"), horizontal, vertical, True),
                        property_text("Notes", component["note"], horizontal, vertical, True)])
        for pin in pins:
            content.append(f'(pin {quoted(pin["number"])} (uuid {quoted(identity(reference + "/pin/" + pin["number"]))}))')
        content.append(f'(instances (project {quoted(PROJECT)} (path {quoted("/" + root_id + "/" + sheet_id)} (reference {quoted(reference)}) (unit 1)))))')
        for pin in pins:
            pin_x = round(horizontal + pin["horizontal"], 4)
            pin_y = round(vertical - pin["vertical"], 4)
            net = component["nets"][pin["number"]]
            pin_key = reference + "/" + pin["number"]
            if net is None:
                content.append(f'(no_connect (at {pin_x:g} {pin_y:g}) (uuid {quoted(identity("nc/" + pin_key))}))')
                continue
            label_x = round(pin_x + (-6.35 if pin["side"] == "left" else 6.35), 4)
            angle = 180 if pin["side"] == "left" else 0
            content.append(f'(wire (pts (xy {pin_x:g} {pin_y:g}) (xy {label_x:g} {pin_y:g})) (stroke (width 0) (type default)) (uuid {quoted(identity("wire/" + pin_key))}))')
            content.append(f'(global_label {quoted(net)} (shape input) (at {label_x:g} {pin_y:g} {angle}) {effect(0.9, justify="left")} (uuid {quoted(identity("label/" + pin_key))}))')
    content.append('(embedded_fonts no))')
    return "\n".join(content) + "\n"


def main():
    global PROJECT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--variant", choices=["system", "control"], default="system")
    args = parser.parse_args()
    specification = importlib.util.spec_from_file_location("clock_design", ROOT / "hardware/schematic_design.py")
    design = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(design)
    control_variant = args.variant == "control"
    if control_variant:
        PROJECT = "control-board"
        selected_sheets = []
        for original in design.SHEETS:
            selected = [component for component in original["components"] if component.get("board") == "control" or component["reference"] in design.CONTROL_LAYOUT["flags"]]
            if selected:
                selected_sheets.append({**original, "components": selected})
        design.SHEETS = selected_sheets
    output = ROOT / ("hardware/pcb/generated" if control_variant else "hardware/schematic/generated")
    output.mkdir(parents=True, exist_ok=True)
    root_id = identity("control/root" if control_variant else "root")
    root = header(root_id, "JJYニキシー管時計・回路検討初版", "A3")
    root.append('(lib_symbols)')
    root.extend([text("JJY / IN-12B ×4 / Arduino Nano 5V / DS3231", 20, 20, 2.0),
                 text("レビュー用初版：HV電圧・K155ID1保護・部品/ソケット現物・コネクター定格は未確定。通電・発注不可。", 20, 30),
                 text("機械寸法の正本：enclosure/layout.json。制御基板は候補配置・現物未照合。HV回路は別基板・保留。", 20, 38)])
    artifacts = {}
    for index, sheet in enumerate(design.SHEETS):
        sheet_id = identity("sheet/" + sheet["name"])
        horizontal = 25.4 + (index % 3) * 127
        vertical = 58.42 + (index // 3) * 43.18
        root.append(f'(sheet (at {horizontal:g} {vertical:g}) (size 111.76 25.4) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {quoted(sheet_id)})'
                    + property_text("Sheetname", sheet["title"], horizontal + 55.88, vertical - 2)
                    + property_text("Sheetfile", sheet["name"] + ".kicad_sch", horizontal + 55.88, vertical + 28)
                    + f'(instances (project {quoted(PROJECT)} (path {quoted("/" + root_id)} (page {quoted(index + 2)})))))')
        artifacts[sheet["name"] + ".kicad_sch"] = render_sheet(sheet, design.SYMBOLS, root_id, sheet_id)
    root.append('(sheet_instances (path "/" (page "1"))) (embedded_fonts no))')
    artifacts[PROJECT + ".kicad_sch"] = "\n".join(root) + "\n"
    project = {"meta": {"filename": PROJECT + ".kicad_pro", "version": 1}, "text_variables": {"DESIGN_STATUS": "DRAFT_NOT_FOR_MANUFACTURE"}}
    if control_variant:
        routing = design.CONTROL_LAYOUT["routing"]
        project["board"] = {"design_settings": {"rules": {
            "min_clearance": routing["clearance"], "min_track_width": routing["minimum_track_width"], "min_copper_edge_clearance": 0.5,
            "min_hole_clearance": 0.25, "min_hole_to_hole": 0.25,
            "min_through_hole_diameter": 0.3, "min_via_annular_width": 0.15, "min_via_diameter": 0.6,
            "min_text_height": 0.8, "min_text_thickness": 0.08}, "drc_exclusions": []}}
        project["net_settings"] = {"meta": {"version": 4}, "classes": [{"name": "Default", "clearance": routing["clearance"],
            "track_width": routing["nominal_track_width"], "via_diameter": routing["via_diameter"], "via_drill": routing["via_drill"],
            "diff_pair_width": 0.25, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
            "microvia_diameter": 0.3, "microvia_drill": 0.1}], "netclass_assignments": {}, "netclass_patterns": []}
        footprint_libraries = sorted({"MountingHole", *[placement["footprint"].split(":")[0] for placement in design.CONTROL_LAYOUT["components"].values()]})
        artifacts["fp-lib-table"] = '(fp_lib_table (version 7) ' + ' '.join(f'(lib (name {quoted(name)}) (type "KiCad") (uri "${{KICAD10_FOOTPRINT_DIR}}/{name}.pretty") (options "") (descr "KiCad 10 standard library"))' for name in footprint_libraries) + ')\n'
    artifacts[PROJECT + ".kicad_pro"] = json.dumps(project, indent=2) + "\n"
    artifacts["JJYClock.kicad_sym"] = '(kicad_symbol_lib (version 20231120) (generator "nixie_jjy_clock")\n' + "\n".join(symbol_definition(name, definition) for name, definition in sorted(design.SYMBOLS.items())) + ')\n'
    artifacts["sym-lib-table"] = '(sym_lib_table (version 7) (lib (name "JJYClock") (type "KiCad") (uri "${KIPRJMOD}/JJYClock.kicad_sym") (options "") (descr "Project-specific reviewed pin maps")))\n'
    artifacts["generation.json"] = json.dumps({"schema_version": 1, "generator": "scripts/generate_schematic.py", "variant": args.variant, "design_sha256": hashlib.sha256((ROOT / "hardware/schematic_design.py").read_bytes()).hexdigest(), "layout_sha256": hashlib.sha256((ROOT / "hardware/pcb/control_layout.json").read_bytes()).hexdigest(), "status": "DRAFT_NOT_FOR_MANUFACTURE", "sheet_count": len(design.SHEETS) + 1, "component_count": sum(not component["reference"].startswith("#") for sheet in design.SHEETS for component in sheet["components"])}, indent=2) + "\n"
    mismatches = []
    for filename, content in artifacts.items():
        path = output / filename
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                mismatches.append(filename)
        else:
            path.write_text(content, encoding="utf-8")
    if mismatches:
        print("再生成が必要: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print(f'{"Checked" if args.check else "Generated"} {len(design.SHEETS) + 1} schematic sheets')
    return 0


if __name__ == "__main__":
    sys.exit(main())
