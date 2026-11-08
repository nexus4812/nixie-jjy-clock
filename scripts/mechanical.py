"""共有寸法の読み込みと配置検査。絶縁・温度・公差の安全認証ではない。"""

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_layout():
    return json.loads((ROOT / "enclosure/layout.json").read_text(encoding="utf-8"))


def tube_centers(layout):
    tube = layout["tube"]
    return [[offset * tube["pitch"], tube["front_y"], tube["center_z"]] for offset in tube["center_offsets"]]


def display_plane(layout):
    tube = layout["tube"]
    return tube["front_y"] + tube["envelope_depth"] + tube["socket_stack"]


def board_definitions(layout):
    boards = []
    for index, center in enumerate(tube_centers(layout)):
        board = dict(layout["display_pcb"])
        board.update({"id": f"display_{index}", "center": [center[0], display_plane(layout), center[2]], "plane": "XZ"})
        boards.append(board)
    for key, plane in (("control_pcb", "XY"), ("colon_pcb", "XZ")):
        board = dict(layout[key])
        if key == "colon_pcb":
            board["center"] = [layout["colon"]["center_x"], board["plane_y"], layout["tube"]["center_z"]]
        board.update({"id": key.removesuffix("_pcb"), "plane": plane})
        boards.append(board)
    return boards


def board_bounds(board):
    center = board["center"]
    size = [board["width"], board["height"], board["thickness"]]
    if board["plane"] == "XZ":
        size = [size[0], size[2], size[1]]
    return [[center[axis] - size[axis] / 2, center[axis] + size[axis] / 2] for axis in range(3)]


def validate(layout):
    errors = []
    case = layout["case"]
    tube = layout["tube"]
    clearance = layout["clearance"]["mechanical_minimum"]
    if layout["units"] != "mm" or layout["schema_version"] != 1:
        errors.append("未対応の単位/スキーマ")
    if len(tube_centers(layout)) != 4:
        errors.append("管中心は4本分必要")
    if tube["pitch"] <= layout["display_pcb"]["width"] + clearance:
        errors.append("表示子基板の間隔不足")
    if tube["radial_gap"] <= 0 or tube["socket_stack"] <= 0:
        errors.append("前面板の隙間/ソケット積層が不正")
    for center in tube_centers(layout):
        if abs(center[0]) + tube["width"] / 2 + tube["radial_gap"] >= case["width"] / 2 - case["wall"]:
            errors.append("管窓がケース側壁と干渉")
        if center[2] - tube["height"] / 2 - tube["radial_gap"] <= case["wall"] or center[2] + tube["height"] / 2 + tube["radial_gap"] >= case["height"] - case["wall"]:
            errors.append("管窓がケース上下壁と干渉")
    inner = [[-case["width"] / 2 + case["wall"], case["width"] / 2 - case["wall"]],
             [0, case["depth"] - case["rear_thickness"]], [case["wall"], case["height"] - case["wall"]]]
    boards = board_definitions(layout)
    for board in boards:
        for axis, limits in enumerate(board_bounds(board)):
            if limits[0] < inner[axis][0] or limits[1] > inner[axis][1]:
                errors.append(f"基板がケース内寸外: {board['id']}")
        radius = board["hole_diameter"] / 2
        for hole_x, hole_y in board["mount_holes"]:
            if abs(hole_x) + radius > board["width"] / 2 or abs(hole_y) + radius > board["height"] / 2:
                errors.append(f"穴が基板外: {board['id']}")
    for left_index, left in enumerate(boards):
        for right in boards[left_index + 1:]:
            separations = [max(first[0] - second[1], second[0] - first[1], 0)
                           for first, second in zip(board_bounds(left), board_bounds(right))]
            distance = math.sqrt(sum(value * value for value in separations))
            if distance < clearance:
                errors.append(f"基板間の予約間隔不足: {left['id']} / {right['id']}")
    antenna = layout["antenna"]
    hv = layout["hv_module_envelope"]
    antenna_box = [[antenna["center"][axis] - extent / 2, antenna["center"][axis] + extent / 2]
                   for axis, extent in enumerate([antenna["length"], antenna["diameter"], antenna["diameter"]])]
    hv_box = [[hv["center"][axis] - extent / 2, hv["center"][axis] + extent / 2]
              for axis, extent in enumerate(hv["size"])]
    cover_wall = layout["clearance"]["hv_cover_wall"]
    cover_gap = layout["clearance"]["hv_cover_gap"]
    cover_box = [[limits[0] - cover_wall - cover_gap, limits[1] + cover_wall + cover_gap] if axis < 2
                 else [limits[0], limits[1] + cover_gap + cover_wall] for axis, limits in enumerate(hv_box)]
    for name, envelope in (("アンテナ", antenna_box), ("HVカバー予約枠", cover_box)):
        for axis, limits in enumerate(envelope):
            if limits[0] < inner[axis][0] or limits[1] > inner[axis][1]:
                errors.append(f"ケース内寸外: {name}")
        for board in boards:
            distances = [max(first[0] - second[1], second[0] - first[1], 0)
                         for first, second in zip(envelope, board_bounds(board))]
            if math.sqrt(sum(value * value for value in distances)) < clearance:
                errors.append(f"予約包絡と基板が近接: {name} / {board['id']}")
    rear_holes = [[center_x, layout["buttons"]["center_z"], layout["buttons"]["hole_diameter"] / 2]
                  for center_x in layout["buttons"]["centers_x"]]
    rear_holes.append([layout["power_jack"]["center_x"], layout["power_jack"]["center_z"], layout["power_jack"]["hole_diameter"] / 2])
    rear_holes.append([layout["status_led"]["center_x"], layout["status_led"]["center_z"], layout["status_led"]["hole_diameter"] / 2])
    for hole_x, hole_z, radius in rear_holes:
        if abs(hole_x) + radius >= case["width"] / 2 - case["wall"] or hole_z - radius <= case["wall"] or hole_z + radius >= case["height"] - case["wall"]:
            errors.append("背面穴がパネル外")
    separation = [max(first[0] - second[1], second[0] - first[1], 0) for first, second in zip(antenna_box, hv_box)]
    antenna_distance = math.sqrt(sum(value * value for value in separation))
    if antenna_distance < antenna["minimum_hv_distance"]:
        errors.append("アンテナとHV予約枠の距離不足")
    return {"status": "FAIL" if errors else "PASS", "errors": errors,
            "tube_centers_mm": tube_centers(layout), "display_plane_y_mm": display_plane(layout),
            "antenna_to_hv_envelope_mm": round(antenna_distance, 3),
            "scope": "基板包絡と指定位置の概略検査。部品実形状、配線、取付金具、熱、受信性能、絶縁は未検証。"}
