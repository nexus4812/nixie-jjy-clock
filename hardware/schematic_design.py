"""Phase 2レビュー用の回路定義。配線の正本。未確定値を製造値として扱わない。"""

import json
from pathlib import Path


CONTROL_LAYOUT = json.loads((Path(__file__).parent / "pcb/control_layout.json").read_text(encoding="utf-8"))

def pin(number, name, kind="passive"):
    return {"number": str(number), "name": name, "kind": kind}


SYMBOLS = {
    "R": {"style": "resistor", "left": [pin(1, "~")], "right": [pin(2, "~")], "sources": []},
    "C": {"style": "capacitor", "left": [pin(1, "~")], "right": [pin(2, "~")], "sources": []},
    "D": {"style": "diode", "left": [pin(1, "K")], "right": [pin(2, "A")], "sources": ["S36"]},
    "LED": {"style": "led", "left": [pin(1, "K")], "right": [pin(2, "A")], "sources": []},
    "Switch": {"style": "switch", "left": [pin(1, "~")], "right": [pin(2, "~")], "sources": []},
    "Fuse": {"style": "fuse", "left": [pin(1, "~")], "right": [pin(2, "~")], "sources": []},
    "Cell": {"style": "battery", "left": [pin(1, "+", "power_out")], "right": [pin(2, "-", "passive")], "sources": ["S06"]},
    "PWR_FLAG": {"style": "block", "left": [pin(1, "SOURCE", "power_out")], "right": [], "sources": []},
    "Nano_ATmega328P": {
        "left": [pin(5 + index, f"D{index + 2}", "bidirectional") for index in range(12)] + [pin(1, "TX/D1", "bidirectional"), pin(2, "RX/D0", "bidirectional")],
        "right": [pin(19 + index, f"A{index}", "bidirectional") for index in range(8)] + [pin(27, "5V", "power_in"), pin(4, "GND", "power_in"), pin(29, "GND", "power_in"), pin(30, "VIN", "power_in"), pin(17, "3V3", "power_out"), pin(18, "AREF", "input"), pin(3, "RESET", "input"), pin(28, "RESET", "input")],
        "sources": ["S13", "S14"], "risks": ["R03", "R11"]},
    "SN74HCT595": {
        "left": [pin(14, "SER", "input"), pin(11, "SRCLK", "input"), pin(12, "RCLK", "input"), pin(13, "~{OE}", "input"), pin(10, "~{SRCLR}", "input"), pin(16, "VCC", "power_in"), pin(8, "GND", "power_in")],
        "right": [pin(number, f"Q{index}", "output") for index, number in enumerate([15, 1, 2, 3, 4, 5, 6, 7])] + [pin(9, "Q7S", "output")], "sources": ["S04", "S05"]},
    "DS3231S": {
        "left": [pin(16, "SCL", "input"), pin(15, "SDA", "bidirectional"), pin(3, "INT/SQW", "open_collector"), pin(4, "~{RST}", "open_collector"), pin(1, "32kHz", "open_collector")],
        "right": [pin(2, "VCC", "power_in"), pin(14, "VBAT", "power_in"), pin(13, "GND", "power_in")] + [pin(number, "N.C._GND") for number in range(5, 13)], "sources": ["S06"], "risks": ["R10"]},
    "MCP1700_3002_TO": {"left": [pin(2, "VIN", "power_in"), pin(1, "GND", "power_in")], "right": [pin(3, "VOUT", "power_out")], "sources": ["S33"]},
    "SN74HCT125": {
        "left": [pin(1, "~{OE1}", "input"), pin(2, "A1", "input"), pin(4, "~{OE2}", "input"), pin(5, "A2", "input"), pin(10, "~{OE3}", "input"), pin(9, "A3", "input"), pin(13, "~{OE4}", "input"), pin(12, "A4", "input")],
        "right": [pin(3, "Y1", "tri_state"), pin(6, "Y2", "tri_state"), pin(8, "Y3", "tri_state"), pin(11, "Y4", "tri_state"), pin(14, "VCC", "power_in"), pin(7, "GND", "power_in")], "sources": ["S32"]},
    "MPSA42": {"left": [pin(2, "B", "input")], "right": [pin(3, "C", "passive"), pin(1, "E", "passive")], "sources": ["S17"]},
    "RCCM_6181B_JJY": {"left": [pin(1, "VDD", "power_in"), pin(2, "GND", "power_in"), pin(3, "PDN2", "input"), pin(5, "PDN1", "input")], "right": [pin(4, "OUT", "output")], "sources": ["S08", "S09"], "risks": ["R04", "R05"]},
    "K155ID1": {
        "left": [pin(3, "X1/1", "input"), pin(6, "X2/2", "input"), pin(7, "X3/4", "input"), pin(4, "X4/8", "input"), pin(5, "VCC", "power_in"), pin(12, "GND", "power_in")],
        "right": [pin(number, f"Y{digit}", "open_collector") for digit, number in enumerate([16, 15, 8, 9, 13, 14, 11, 10, 1, 2])], "sources": ["S03"], "risks": ["R02", "R04"]},
    "IN_12B": {"left": [pin(1, "ANODE")], "right": [pin(number, f"K{digit}") for digit, number in enumerate([2, 11, 10, 9, 8, 7, 6, 5, 4, 3])] + [pin(12, "COMMA")], "sources": ["S01"], "risks": ["R01", "R04"]},
    "Neon": {"left": [pin(1, "ELECTRODE")], "right": [pin(2, "ELECTRODE")], "sources": ["S18"], "risks": ["R07"]},
    "BUCK_INTERFACE": {"left": [pin("VIN", "VIN", "power_in"), pin("GND", "GND", "power_in")], "right": [pin("5V", "5V", "power_out")], "sources": [], "risks": ["R06"], "interface": True},
    "NCH6100HV_INTERFACE": {"left": [pin("VIN", "VIN", "power_in"), pin("GND", "GND", "power_in"), pin("SHDN", "SHDN", "input")], "right": [pin("HV", "HV+", "power_out")], "sources": ["S12"], "risks": ["R06"], "interface": True},
}

for count in (1, 2, 3, 4, 5, 6):
    SYMBOLS[f"Conn_{count}"] = {"left": [pin(index, str(index)) for index in range(1, count + 1)], "right": [], "sources": [], "risks": ["R04"]}


def component(reference, symbol, value, nets, sources=None, risks=None, note=""):
    result = {"reference": reference, "symbol": symbol, "value": value,
            "nets": {str(number): net for number, net in nets.items()},
            "sources": sources if sources is not None else SYMBOLS[symbol].get("sources", []),
            "risks": risks if risks is not None else SYMBOLS[symbol].get("risks", []), "note": note}
    placement = CONTROL_LAYOUT["components"].get(reference)
    if placement:
        result["footprint"] = placement["footprint"]
        result["board"] = "control"
        result["risks"] = list(dict.fromkeys([*result["risks"], "R04"]))
        if placement.get("mpn"):
            result["value"] = placement["mpn"]
    return result


def two(reference, symbol, value, first, second, **metadata):
    return component(reference, symbol, value, {1: first, 2: second}, **metadata)


SHEETS = []


def sheet(name, title, note, components):
    SHEETS.append({"name": name, "title": title, "note": note, "components": components})


sheet("power", "電源・保護・HV停止制御", "市販絶縁12V DCのみ。JP1を外してUSB書込。JP2は通常未挿入。HV部はR01/R02/R06未解決・通電不可。", [
    component("J1", "Conn_2", "12V_DC_INPUT", {1: "12V_IN", 2: "GND"}, risks=["R10"]),
    two("F1", "Fuse", "FUSE_T1A_TBD", "12V_IN", "12V_FUSED", risks=["R06"]),
    two("D1", "D", "1N5819", "12V_PROTECTED", "12V_FUSED"),
    two("C1", "C", "100u_25V", "12V_PROTECTED", "GND"),
    two("C2", "C", "100n_50V", "12V_PROTECTED", "GND"),
    component("PS1", "BUCK_INTERFACE", "12V_TO_5V_TBD", {"VIN": "12V_PROTECTED", "GND": "GND", "5V": "5V_BUCK"}),
    two("JP1", "Switch", "REMOVE_FOR_USB", "5V_BUCK", "+5V", risks=["R11"]),
    two("C3", "C", "47u_16V", "+5V", "GND"),
    two("C4", "C", "100n_50V", "+5V", "GND"),
    component("J41", "Conn_2", "EXTERNAL_5V_BUCK", {1: "5V_BUCK", 2: "GND"}, risks=["R11"]),
    component("J42", "Conn_3", "LV_CONTROL_ONLY", {1: "GND", 2: "HV_ENABLE", 3: "COLON_ENABLE"}, risks=["R06", "R08"]),
    two("JP2", "Switch", "HV_ARM_NORMALLY_OPEN", "12V_PROTECTED", "12V_HV", risks=["R06", "R11"]),
    component("PS2", "NCH6100HV_INTERFACE", "NCH6100HV_R06", {"VIN": "12V_HV", "GND": "GND", "SHDN": "HV_SHDN", "HV": "HV_RAW"}),
    two("R1", "R", "2k2_0.25W", "12V_HV", "HV_SHDN", risks=["R06"]),
    component("Q1", "MPSA42", "MPSA42", {1: "GND", 2: "HV_BASE", 3: "HV_SHDN"}, risks=["R06", "R11"]),
    two("R2", "R", "4k7", "HV_ENABLE", "HV_BASE"),
    two("R3", "R", "100k", "HV_BASE", "GND"),
    two("R4", "R", "110k_0.5W_HV", "HV_RAW", "HV_BLEED_MID", risks=["R06", "R08"]),
    two("R5", "R", "110k_0.5W_HV", "HV_BLEED_MID", "GND", risks=["R06", "R08"]),
    component("J2", "Conn_2", "HV_RAW_GUARDED_TP", {1: "HV_RAW", 2: "GND"}, risks=["R08"]),
    component("#FLG01", "PWR_FLAG", "12V_AFTER_PROTECTION", {1: "12V_PROTECTED"}),
    component("#FLG02", "PWR_FLAG", "SUPPLY_RETURN", {1: "GND"}),
    component("#FLG03", "PWR_FLAG", "5V_AFTER_MODE_JUMPER", {1: "+5V"}),
    component("#FLG04", "PWR_FLAG", "12V_AFTER_MANUAL_ARM", {1: "12V_HV"}),
])

nano_nets = {number: None for number in [1, 2, 3, 17, 18, 22, 25, 26, 28, 30]}
nano_nets.update({4: "GND", 29: "GND", 27: "+5V", 5: "JJY_DATA", 6: "RTC_SQW", 7: "PDN1_PULL_LOW", 8: "PDN2_PULL_LOW", 9: "HV_ENABLE", 10: "COLON_ENABLE", 11: None, 12: "STATUS_LED", 13: "SR_LATCH", 14: "SR_DATA", 15: None, 16: "SR_CLOCK", 19: "BUTTON_SET", 20: "BUTTON_PLUS", 21: "BUTTON_MINUS", 23: "I2C_SDA", 24: "I2C_SCL"})
control = [component("A1", "Nano_ATmega328P", "NANO_328P_5V16MHz", nano_nets),
           two("R10", "R", "100R", "SR_CLOCK", "SR_CLOCK_BUS"),
           two("R11", "R", "100R", "SR_LATCH", "SR_LATCH_BUS"),
           two("R12", "R", "100R", "SR_DATA", "SR_DATA_BUS"),
           two("R13", "R", "10k", "SR_CLOCK_BUS", "GND"),
           two("R14", "R", "10k", "SR_LATCH_BUS", "GND")]
for index in range(2):
    nets = {16: "+5V", 8: "GND", 13: "GND", 10: "+5V", 11: "SR_CLOCK_BUS", 12: "SR_LATCH_BUS",
            14: "SR_DATA_BUS" if index == 0 else "SR_CASCADE", 9: "SR_CASCADE" if index == 0 else None}
    for output_index, number in enumerate([15, 1, 2, 3, 4, 5, 6, 7]):
        nets[number] = f"BCD{index * 2 + output_index // 4}_{output_index % 4}"
    control.append(component(f"U{index + 1}", "SN74HCT595", "74HCT595_PACKAGE_TBD", nets, risks=["R04"]))
    control.append(two(f"C{10 + index}", "C", "100n_50V", "+5V", "GND"))
control.append(two("C12", "C", "10u_16V", "+5V", "GND"))
for index in range(4):
    control.append(component(f"J{50 + index}", "Conn_6", f"TO_DIGIT{index}_LV", {1: "+5V", 2: "GND", **{bit + 3: f"BCD{index}_{bit}" for bit in range(4)}}))
sheet("control", "Arduino Nano・16bit静的BCD駆動", "595 OEはGND固定。データをラッチするまでHVを許可しない。D8予備。D0/D1はUSB診断用。", control)

sheet("rtc", "DS3231・非充電バックアップ", "DS3231S/SN。N.C.の5〜12番はGND。CR2032は充電しない。RST外部プルアップなし。", [
    component("U3", "DS3231S", "DS3231S_OR_SN", {1: None, 2: "+5V", 3: "RTC_SQW", 4: None, **{number: "GND" for number in range(5, 14)}, 14: "VBAT", 15: "I2C_SDA", 16: "I2C_SCL"}),
    two("BT1", "Cell", "CR2032_NO_CHARGER", "VBAT", "GND"),
    two("C20", "C", "100n_50V", "+5V", "GND"),
    two("R20", "R", "4k7", "+5V", "I2C_SDA"),
    two("R21", "R", "4k7", "+5V", "I2C_SCL"),
    two("R22", "R", "10k", "+5V", "RTC_SQW"),
    component("J3", "Conn_4", "I2C_TEST", {1: "+5V", 2: "GND", 3: "I2C_SDA", 4: "I2C_SCL"}),
])

jjy = [two("R30", "R", "100R", "+5V", "JJY_LDO_IN"),
       two("C30", "C", "10u_16V", "JJY_LDO_IN", "GND"),
       two("C31", "C", "100n_50V", "JJY_LDO_IN", "GND"),
       component("U4", "MCP1700_3002_TO", "MCP1700-3002E_TO", {1: "GND", 2: "JJY_LDO_IN", 3: "+3V_JJY"}),
       two("C32", "C", "1u_EFFECTIVE_MIN", "+3V_JJY", "GND", sources=["S33"]),
       two("C33", "C", "100n_50V", "+3V_JJY", "GND"),
       component("RX1", "RCCM_6181B_JJY", "RCCM-6181B-JJY", {1: "+3V_JJY", 2: "GND", 3: "JJY_PDN2", 4: "JJY_OUT_RAW", 5: "JJY_PDN1"}),
       two("R31", "R", "1k", "JJY_OUT_RAW", "JJY_OUT_BUFFER_IN"),
       component("U5", "SN74HCT125", "SN74HCT125N", {1: "GND", 2: "JJY_OUT_BUFFER_IN", 3: "JJY_DATA", 4: "+5V", 5: "GND", 6: None, 7: "GND", 8: None, 9: "GND", 10: "+5V", 11: None, 12: "GND", 13: "+5V", 14: "+5V"}),
       two("C34", "C", "100n_50V", "+5V", "GND"),
       component("J4", "Conn_3", "JJY_DIAGNOSTIC", {1: "GND", 2: "JJY_OUT_RAW", 3: "JJY_DATA"}, risks=["R05"]),
       component("J45", "Conn_5", "TO_EXTERNAL_JJY", {1: "+3V_JJY", 2: "GND", 3: "JJY_PDN2", 4: "JJY_OUT_RAW", 5: "JJY_PDN1"}, risks=["R04", "R05"]),
       component("#FLG05", "PWR_FLAG", "5V_AFTER_RC_FILTER", {1: "JJY_LDO_IN"}, note="R30を介した5V給電。ERCは受動部品越しの電源を追跡しないため宣言。LDO電圧の実測保証ではない")]
for index in range(2):
    selected = index + 1
    jjy.extend([
        two(f"R{32 + index * 3}", "R", "47k", "+3V_JJY", f"JJY_PDN{selected}"),
        two(f"R{33 + index * 3}", "R", "47k", f"PDN{selected}_PULL_LOW", f"PDN{selected}_BASE"),
        two(f"R{34 + index * 3}", "R", "100k", f"PDN{selected}_BASE", "GND"),
        component(f"Q{2 + index}", "MPSA42", "MPSA42", {1: "GND", 2: f"PDN{selected}_BASE", 3: f"JJY_PDN{selected}"}),
    ])
sheet("jjy", "JJY 3V電源・40/60kHz選局・µA出力バッファ", "H/H停止。Nano D4=HighでPDN1をLow、D5=HighでPDN2をLow。RAW OUTへプルアップやLEDを接続しない。", jjy)

ui = [two("R40", "R", "1k", "STATUS_LED", "LED_ANODE"), two("D2", "LED", "AMBER_STATUS", "GND", "LED_ANODE")]
ui.append(component("J40", "Conn_5", "REAR_UI_HARNESS", {1: "GND", 2: "BUTTON_SET", 3: "BUTTON_PLUS", 4: "BUTTON_MINUS", 5: "LED_ANODE"}))
for index, name in enumerate(["SET", "PLUS", "MINUS"]):
    ui.extend([two(f"SW{index + 1}", "Switch", name, f"BUTTON_{name}", "GND"),
               two(f"R{41 + index}", "R", "10k", "+5V", f"BUTTON_{name}"),
               two(f"C{40 + index}", "C", "100n_50V", f"BUTTON_{name}", "GND")])
sheet("ui", "背面操作・JJY状態表示", "SET / + / -。状態LEDの点滅はファームウェアで定義。共有位置データはenclosure/layout.json。", ui)

for index in range(4):
    cathodes = {digit: f"DIGIT{index}_K{digit}" for digit in range(10)}
    driver_nets = {3: f"BCD{index}_0", 6: f"BCD{index}_1", 7: f"BCD{index}_2", 4: f"BCD{index}_3", 5: "+5V", 12: "GND"}
    driver_nets.update({number: cathodes[digit] for digit, number in enumerate([16, 15, 8, 9, 13, 14, 11, 10, 1, 2])})
    tube_nets = {1: f"DIGIT{index}_ANODE", 12: None}
    tube_nets.update({number: cathodes[digit] for digit, number in enumerate([2, 11, 10, 9, 8, 7, 6, 5, 4, 3])})
    offset = 100 + 10 * index
    sheet(f"display_{index}", f"表示子{index + 1}・IN-12Bソケット候補", "未解決R01/R02: HV電圧・抵抗・非選択出力保護が未確定。これは接続検討図であり通電・発注用ではない。", [
        component(f"U{10 + index}", "K155ID1", "K155ID1_R02_HOLD", driver_nets),
        component(f"V{1 + index}", "IN_12B", "IN-12B_SOCKET_R04", tube_nets),
        two(f"R{offset}", "R", "TBD_R01_ANODE", "HV_RAW", f"DIGIT{index}_ANODE", risks=["R01", "R02", "R08"]),
        two(f"C{offset}", "C", "100n_50V", "+5V", "GND"),
        component(f"J{10 + index}", "Conn_6", f"DIGIT{index}_LOGIC", {1: "+5V", 2: "GND", **{bit + 3: f"BCD{index}_{bit}" for bit in range(4)}}),
        component(f"J{20 + index}", "Conn_2", f"DIGIT{index}_HV_GUARDED", {1: "HV_RAW", 2: "GND"}, risks=["R04", "R08"]),
        two(f"R{offset + 1}", "R", "1M_0.25W_HV", "HV_RAW", "GND", risks=["R06", "R08"], note="配線分離後の子板放電。アノード側追加容量なし。最終容量と経路を要確認"),
    ])

colon = []
for index in range(2):
    colon.extend([
        two(f"R{150 + index}", "R", "TBD_R07_NEON", "HV_RAW", f"NEON{index}_ANODE", risks=["R01", "R07", "R08"]),
        two(f"NE{index + 1}", "Neon", "ORANGE_NEON_R07", f"NEON{index}_ANODE", "NEON_CATHODES"),
    ])
colon.extend([
    component("Q4", "MPSA42", "MPSA42", {1: "GND", 2: "COLON_BASE", 3: "NEON_CATHODES"}),
    two("R152", "R", "10k", "COLON_ENABLE", "COLON_BASE"),
    two("R153", "R", "100k", "COLON_BASE", "GND"),
    two("R154", "R", "1M_0.25W_HV", "HV_RAW", "GND", risks=["R06", "R08"]),
    component("J30", "Conn_3", "COLON_HARNESS_GUARDED", {1: "HV_RAW", 2: "GND", 3: "COLON_ENABLE"}, risks=["R04", "R08"]),
])
sheet("colon", "橙色ネオン2灯・個別電流制限", "ネオン各枝に独立抵抗。維持/始動電圧・暗所特性と抵抗定格はR07で確認。HVと信号のコネクター混在は要配置レビュー。", colon)
