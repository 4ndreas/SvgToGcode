from xml.etree.ElementTree import Element, ElementTree

from svg_to_gcode.svg_parser import parse_file, Transformation, debug_methods
from svg_to_gcode.geometry import LineSegmentChain

from svg_to_gcode import TOLERANCES

name_space = 'http://www.w3.org/2000/svg'

TOLERANCES['approximation'] = 0.1


def run_test(svg_file_name, debug_file_name):
    curves = parse_file(svg_file_name)

    success = True
    approximations = []
    count = 0
    for curve in curves:
        approximation = LineSegmentChain.line_segment_approximation(curve)
        approximations.append(approximation)
        count += approximation.chain_size()

    generate_debug(approximations, svg_file_name, debug_file_name)

    return success


def generate_debug(approximations, svg_file_name, debug_file_name):
    tree = ElementTree()
    tree.parse(svg_file_name)

    root = tree.getroot()

    height_str = root.get("height")
    canvas_height = float(height_str) if height_str.isnumeric() else float(height_str[:-2])

    for path in root.iter("{%s}path" % name_space):
        path.set("fill", "none")
        path.set("stroke", "black")
        path.set("stroke-width", f"{TOLERANCES['approximation']}mm")

        style = path.get("style")
        if style and "display:none" in style:
            path.set("style", "display:none")
        elif style and ("visibility:hidden" in style or "visibility:collapse" in style):
            path.set("style", "visibility:hidden")
        else:
            path.set("style", "")

    group = Element("{%s}g" % name_space)

    change_origin = Transformation()
    change_origin.add_scale(1, -1)
    change_origin.add_translation(0, -canvas_height)

    group.append(debug_methods.arrow_defs())
    for approximation in approximations:
        path = debug_methods.to_svg_path(approximation, color="red", stroke_width=f"{TOLERANCES['approximation']/2}mm",
                                         transformation=change_origin, draw_arrows=True)
        group.append(path)

    root.append(group)

    tree.write(debug_file_name)

