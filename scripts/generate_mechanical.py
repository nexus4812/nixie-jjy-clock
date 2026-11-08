"""共有JSONからOpenSCAD用定数、正面/上面SVG、穴一覧を生成する。"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from xml.sax.saxutils import escape

from mechanical import ROOT, board_definitions, display_plane, load_layout, tube_centers, validate


def scad_parameters(layout):
    values = {"layout_revision": layout["revision"], "layout_sha256": hashlib.sha256((ROOT / "enclosure/layout.json").read_bytes()).hexdigest(),
              "case_size": [layout["case"][key] for key in ("width", "depth", "height")],
              "case_wall": layout["case"]["wall"], "rear_thickness": layout["case"]["rear_thickness"],
              "brass_thickness": layout["case"]["brass_thickness"],
              "tube_centers": tube_centers(layout), "tube_size": [layout["tube"][key] for key in ("width", "envelope_depth", "height")],
              "tube_radial_gap": layout["tube"]["radial_gap"], "tube_corner_radius": layout["tube"]["aperture_corner_radius"],
              "display_plane_y": display_plane(layout),
              "colon_centers_z": [layout["tube"]["center_z"] + offset for offset in layout["colon"]["center_offsets_z"]],
              "colon_aperture_diameter": layout["colon"]["aperture_diameter"], "colon_lamp_diameter": layout["colon"]["lamp_diameter"],
              "colon_center_x": layout["colon"]["center_x"], "colon_front_y": layout["colon"]["front_y"], "colon_depth": layout["colon"]["envelope_depth"],
              "panel_mount_holes": layout["panel_mount_holes"], "panel_hole_diameter": layout["panel_hole_diameter"],
              "button_centers_x": layout["buttons"]["centers_x"], "button_center_z": layout["buttons"]["center_z"],
              "button_hole_diameter": layout["buttons"]["hole_diameter"],
              "power_jack_center": [layout["power_jack"]["center_x"], layout["power_jack"]["center_z"]],
              "power_jack_hole_diameter": layout["power_jack"]["hole_diameter"],
              "status_led_center": [layout["status_led"]["center_x"], layout["status_led"]["center_z"]],
              "status_led_hole_diameter": layout["status_led"]["hole_diameter"],
              "antenna_center": layout["antenna"]["center"], "antenna_length": layout["antenna"]["length"],
              "antenna_diameter": layout["antenna"]["diameter"], "hv_center": layout["hv_module_envelope"]["center"],
              "hv_size": layout["hv_module_envelope"]["size"], "hv_cover_wall": layout["clearance"]["hv_cover_wall"],
              "hv_cover_gap": layout["clearance"]["hv_cover_gap"],
              "boards": [[board["id"], board["plane"], board["center"], board["width"], board["height"], board["thickness"],
                          board["mount_holes"], board["hole_diameter"]] for board in board_definitions(layout)]}
    return "\n".join(f"{key} = {json.dumps(value, ensure_ascii=False)};" for key, value in values.items()) + "\n"


def drawing(layout):
    case = layout["case"]
    width = case["width"]
    height = case["height"]
    tube = layout["tube"]
    items = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-135 -25 270 270" width="1080" height="1080">',
             '<rect x="-135" y="-25" width="270" height="270" fill="#f2ede3"/>',
             '<g fill="#28231f" font-family="sans-serif" font-size="4">',
             f'<text x="-120" y="-14">JJY NIXIE / {escape(layout["revision"])} / DRAFT — mm</text>',
             f'<rect x="{-width/2}" y="0" width="{width}" height="{height}" rx="2" fill="#4b3027"/>',
             f'<rect x="{-width/2+2}" y="2" width="{width-4}" height="{height-4}" rx="1" fill="#ba9b59"/>']
    for index, center in enumerate(tube_centers(layout)):
        aperture_width = tube["width"] + 2 * tube["radial_gap"]
        aperture_height = tube["height"] + 2 * tube["radial_gap"]
        items.append(f'<rect x="{center[0]-aperture_width/2}" y="{height-center[2]-aperture_height/2}" width="{aperture_width}" height="{aperture_height}" rx="5" fill="#181514"/>')
        items.append(f'<text x="{center[0]}" y="{height-center[2]+9}" text-anchor="middle" font-size="25" fill="#ed8b34">{[1,2,3,4][index]}</text>')
        items.append(f'<text x="{center[0]}" y="{height-8}" text-anchor="middle">X={center[0]:g}</text>')
    for offset in layout["colon"]["center_offsets_z"]:
        items.append(f'<circle cx="{layout["colon"]["center_x"]}" cy="{height-tube["center_z"]-offset}" r="{layout["colon"]["aperture_diameter"] / 2}" fill="#ed8b34"/>')
    for hole_x, hole_z in layout["panel_mount_holes"]:
        items.append(f'<circle cx="{hole_x}" cy="{height-hole_z}" r="1.6" fill="#352d28"/>')
    items.extend([f'<text x="-120" y="102">FRONT: {width} × {height}; tube pitch {tube["pitch"]}; aperture {tube["width"] + 2 * tube["radial_gap"]} × {tube["height"] + 2 * tube["radial_gap"]} (draft)</text>',
                  '<g transform="translate(0,120)">',
                  f'<rect x="{-width/2}" y="0" width="{width}" height="{case["depth"]}" fill="#e1d6c1" stroke="#4b3027"/>'])
    for board in board_definitions(layout):
        center = board["center"]
        depth = board["height"] if board["plane"] == "XY" else board["thickness"]
        items.append(f'<rect x="{center[0]-board["width"]/2}" y="{center[1]-depth/2}" width="{board["width"]}" height="{depth}" fill="#527b60" fill-opacity="0.7" stroke="#315b40" stroke-width="0.3"/>')
    antenna = layout["antenna"]
    items.append(f'<rect x="{antenna["center"][0]-antenna["length"]/2}" y="{antenna["center"][1]-antenna["diameter"]/2}" width="{antenna["length"]}" height="{antenna["diameter"]}" rx="5" fill="#3a4143"/>')
    hv = layout["hv_module_envelope"]
    items.append(f'<rect x="{hv["center"][0]-hv["size"][0]/2}" y="{hv["center"][1]-hv["size"][1]/2}" width="{hv["size"][0]}" height="{hv["size"][1]}" fill="#c97a5f"/>')
    items.extend(['<text x="52" y="76">HV reservation</text>', '<text x="-95" y="82">JJY antenna</text>',
                  '<text x="-85" y="65">CONTROL PCB</text>', '</g>',
                  '<text x="-120" y="240">TOP: component envelopes only / NOT FOR FABRICATION</text>', '</g></svg>'])
    return "\n".join(items) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    layout = load_layout()
    report = validate(layout)
    if report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    output = ROOT / "enclosure/generated/layout.scad"
    rendered = scad_parameters(layout)
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != rendered:
            report["errors"].append("OpenSCADパラメーターが共有JSONと不一致。再生成が必要")
            report["status"] = "FAIL"
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        build = ROOT / "build/enclosure"
        build.mkdir(parents=True, exist_ok=True)
        (build / "layout.svg").write_text(drawing(layout), encoding="utf-8")
        with (build / "board-holes.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["board", "plane", "hole_x_from_center_mm", "hole_y_from_center_mm", "diameter_mm"])
            for board in board_definitions(layout):
                for hole in board["mount_holes"]:
                    writer.writerow([board["id"], board["plane"], *hole, board["hole_diameter"]])
        (build / "geometry-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
