include <generated/layout.scad>

part = "assembly";
show_internal = true;
show_tubes = true;
show_digit_preview = true;
exploded = 0;
$fn = 64;

module rounded_window(width, height, radius) {
    hull() {
        for (offset_x = [-width / 2 + radius, width / 2 - radius])
            for (offset_z = [-height / 2 + radius, height / 2 - radius])
                translate([offset_x, offset_z]) circle(r = radius);
    }
}

module front_profile() {
    difference() {
        translate([-case_size[0] / 2, 0]) square([case_size[0], case_size[2]]);
        for (center = tube_centers)
            translate([center[0], center[2]])
                rounded_window(tube_size[0] + 2 * tube_radial_gap,
                               tube_size[2] + 2 * tube_radial_gap, tube_corner_radius);
        for (center_z = colon_centers_z)
            translate([colon_center_x, center_z]) circle(d = colon_aperture_diameter);
        for (hole = panel_mount_holes)
            translate(hole) circle(d = panel_hole_diameter);
    }
}

module front_panel() {
    rotate([90, 0, 0]) linear_extrude(height = brass_thickness) front_profile();
}

module rear_profile() {
    difference() {
        translate([-case_size[0] / 2 + case_wall, case_wall])
            square([case_size[0] - 2 * case_wall, case_size[2] - 2 * case_wall]);
        for (center_x = button_centers_x)
            translate([center_x, button_center_z]) circle(d = button_hole_diameter);
        translate(power_jack_center) circle(d = power_jack_hole_diameter);
        translate(status_led_center) circle(d = status_led_hole_diameter);
    }
}

module rear_panel() {
    translate([0, case_size[1], 0]) rotate([90, 0, 0])
        linear_extrude(height = rear_thickness) rear_profile();
}

module wood_shell() {
    difference() {
        translate([-case_size[0] / 2, 0, 0]) cube(case_size);
        translate([-case_size[0] / 2 + case_wall, -1, case_wall])
            cube([case_size[0] - 2 * case_wall, case_size[1] + 2, case_size[2] - 2 * case_wall]);
    }
}

module pcb_shape(board) {
    difference() {
        translate([-board[3] / 2, -board[4] / 2, -board[5] / 2]) cube([board[3], board[4], board[5]]);
        for (hole = board[6])
            translate([hole[0], hole[1], -board[5]]) cylinder(h = 3 * board[5], d = board[7]);
    }
}

module board_assembly(board) {
    translate(board[2]) {
        if (board[1] == "XZ") rotate([90, 0, 0]) pcb_shape(board);
        else pcb_shape(board);
    }
}

module tube_envelopes() {
    for (center = tube_centers)
        translate([center[0], center[1] + tube_size[1] / 2, center[2]])
            rotate([90, 0, 0]) linear_extrude(height = tube_size[1], center = true)
                rounded_window(tube_size[0], tube_size[2], 5);
    for (center_z = colon_centers_z)
        translate([colon_center_x, colon_front_y + colon_depth / 2, center_z]) rotate([90, 0, 0]) cylinder(h = colon_depth, d = colon_lamp_diameter, center = true);
}

module antenna() {
    translate(antenna_center) rotate([0, 90, 0]) cylinder(h = antenna_length, d = antenna_diameter, center = true);
}

module digit_preview() {
    digits = ["1", "2", "3", "4"];
    for (index = [0 : len(tube_centers) - 1])
        translate([tube_centers[index][0], tube_centers[index][1] - 0.3, tube_centers[index][2]])
            rotate([90, 0, 0]) linear_extrude(height = 0.2)
                text(digits[index], size = 18, halign = "center", valign = "center");
}

module hv_cover() {
    outer = hv_size + [2 * (hv_cover_wall + hv_cover_gap), 2 * (hv_cover_wall + hv_cover_gap), hv_cover_gap + hv_cover_wall];
    translate(hv_center) difference() {
        translate([0, 0, (hv_cover_gap + hv_cover_wall) / 2]) cube(outer, center = true);
        translate([0, 0, hv_cover_gap / 2 - hv_cover_wall])
            cube([outer[0] - 2 * hv_cover_wall, outer[1] - 2 * hv_cover_wall, outer[2] + hv_cover_wall], center = true);
    }
}

if (part == "front_2d") front_profile();
else if (part == "rear_2d") rear_profile();
else if (part == "front") front_panel();
else if (part == "rear") rear_panel();
else if (part == "shell") wood_shell();
else if (part == "hv_cover") hv_cover();
else if (part == "assembly") {
    color([0.22, 0.12, 0.08]) wood_shell();
    color([0.68, 0.52, 0.25]) translate([0, -exploded, 0]) front_panel();
    color([0.22, 0.12, 0.08]) translate([0, exploded, 0]) rear_panel();
    if (show_tubes) color([0.8, 0.87, 0.9, 0.45]) tube_envelopes();
    if (show_tubes && show_digit_preview) color([1, 0.38, 0.08]) digit_preview();
    if (show_internal) {
        for (board = boards) color([0.1, 0.35, 0.22]) board_assembly(board);
        color([0.14, 0.14, 0.14]) antenna();
        color([0.7, 0.24, 0.12, 0.5]) translate(hv_center) cube(hv_size, center = true);
        color([0.65, 0.65, 0.67, 0.25]) hv_cover();
    }
}
else assert(false, "Unknown part");
