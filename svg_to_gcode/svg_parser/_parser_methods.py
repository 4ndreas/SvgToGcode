from xml.etree import ElementTree
from typing import List
from copy import deepcopy

from svg_to_gcode.svg_parser import Path,  Transformation
from svg_to_gcode.geometry import Curve,Text
from svg_to_gcode.geometry._vector import Vector

NAMESPACES = {'svg': 'http://www.w3.org/2000/svg'}

class drawOpts:
    def  __init__(self):
        self.draw_hidden = False
        self.doFiltering = False
        self.filter = None
    

def _has_style(element: ElementTree.Element, key: str, value: str) -> bool:
    """
    Check if an element contains a specific key and value either as an independent attribute or in the style attribute.
    """
    return element.get(key) == value or (element.get("style") and f"{key}:{value}" in element.get("style"))


# Todo deal with viewBoxes
def parse_root(root: ElementTree.Element, transform_origin=True, canvas_height=None, dOpts=drawOpts,
               visible_root=True, root_transformation=None) -> List[Curve]:

    """
    Recursively parse an etree root's children into geometric curves.

    :param root: The etree element who's children should be recursively parsed. The root will not be drawn.
    :param canvas_height: The height of the canvas. By default the height attribute of the root is used. If the root
    does not contain the height attribute, it must be either manually specified or transform must be False.
    :param transform_origin: Whether or not to transform input coordinates from the svg coordinate system to standard
    cartesian system. Depends on canvas_height for calculations.
    :param dOpts: Whether or not to draw hidden elements based on their display, visibility and opacity attributes.
    :param visible_root: Specifies whether or the root is visible. (Inheritance can be overridden)
    :param root_transformation: Specifies whether the root's transformation. (Transformations are inheritable)
    :return: A list of geometric curves describing the svg. Use the Compiler sub-module to compile them to gcode.
    """

    if canvas_height is None:
        height_str = root.get("height")
        canvas_height = float(height_str) if height_str.isnumeric() else float(height_str[:-2])

    curves = []

    # Draw visible elements (Depth-first search)
    for element in list(root):

        # display cannot be overridden by inheritance. Just skip the element
        display = _has_style(element, "display", "none")

        if display or element.tag == "{%s}defs" % NAMESPACES["svg"]:
            continue

        transformation = deepcopy(root_transformation) if root_transformation else None

        transform = element.get('transform')
        if transform:
            transformation = Transformation() if transformation is None else transformation
            transformation.add_transform(transform)

        # Is the element and it's root not hidden?
        visible = visible_root and not (_has_style(element, "visibility", "hidden")
                                        or _has_style(element, "visibility", "collapse"))
        # Override inherited visibility
        visible = visible or (_has_style(element, "visibility", "visible"))

        draw = True
        # check for filter 
        # if dOpts.doFiltering:
        #     if dOpts.filter == None:
        #         if element.get('stroke-dasharray') != None:
        #             draw = False
        #     else:
        #         if element.get(dOpts.filter) == None:
        #             draw = False

        # if draw:
            # If the current element is opaque and visible, draw it
        if dOpts.draw_hidden or visible:
            if element.tag == "{%s}path" % NAMESPACES["svg"]:
                draw = True
                if dOpts.filter == None:
                    if element.get('stroke-dasharray') != None:
                        draw = False
                else:
                    if element.get(dOpts.filter) == None:
                        draw = False
                if draw:
                    path = Path(element.attrib['d'], canvas_height, transform_origin, transformation)
                    curves.extend(path.curves)

            elif element.tag == "{%s}text" % NAMESPACES["svg"]:
                if dOpts.filter == 'text':
                    command, arguments = transform.split('(')
                    arguments = arguments.replace(')', '')
                    arguments = [float(argument.strip()) for argument in arguments.replace(',', ' ').split()]
                    x = element.get('x')
                    y = element.get('y')
                    a = arguments[0]
                    tx = element.text
                    path = Path("", canvas_height, transform_origin, transformation)
                    path.curves.append(Text(x,y,a,tx))
                    curves.extend(path.curves)



        # Continue the recursion
        curves.extend(parse_root(element, transform_origin, canvas_height, dOpts, visible, transformation))

    # ToDo implement shapes class
    return curves


def parse_string(svg_string: str, transform_origin=True, canvas_height=None, dOpts=drawOpts) -> List[Curve]:
    """
        Recursively parse an svg string into geometric curves. (Wrapper for parse_root)

        :param svg_string: The etree element who's children should be recursively parsed. The root will not be drawn.
        :param canvas_height: The height of the canvas. By default the height attribute of the root is used. If the root
        does not contain the height attribute, it must be either manually specified or transform_origin must be False.
        :param transform_origin: Whether or not to transform input coordinates from the svg coordinate system to standard cartesian
         system. Depends on canvas_height for calculations.
        :param dOpts: Whether or not to draw hidden elements based on their display, visibility and opacity attributes.
        :return: A list of geometric curves describing the svg. Use the Compiler sub-module to compile them to gcode.
    """
    root = ElementTree.fromstring(svg_string)
    return parse_root(root, transform_origin, canvas_height, dOpts)


def parse_file(file_path: str, transform_origin=True, canvas_height=None, dOpts=drawOpts) -> List[Curve]:
    """
            Recursively parse an svg file into geometric curves. (Wrapper for parse_root)

            :param file_path: The etree element who's children should be recursively parsed. The root will not be drawn.
            :param canvas_height: The height of the canvas. By default the height attribute of the root is used. If the root
            does not contain the height attribute, it must be either manually specified or transform_origin must be False.
            :param transform_origin: Whether or not to transform input coordinates from the svg coordinate system to standard cartesian
             system. Depends on canvas_height for calculations.
            :param dOpts: Whether or not to draw hidden elements based on their display, visibility and opacity attributes.
            :return: A list of geometric curves describing the svg. Use the Compiler sub-module to compile them to gcode.
        """
    if dOpts == None:
        dOpts.draw_hidden= False
        dOpts.Filter = None

    root = ElementTree.parse(file_path).getroot()
    return parse_root(root, transform_origin, canvas_height, dOpts)

# def getDistance(a,b):
#     x = a.x - b.x
#     y = a.y - b.y

#     return x*x+ y * y

#  https://stackoverflow.com/questions/59580164/path-optimization-tsp-in-python

# simple stort 
def sortCurves(curves ):
    
    newOrder = []
    start = curves[0].end
    newOrder.append(curves.pop(0))
    
    while curves:
        shortest = float("Inf") 

        for curve in curves:
            x = start.x - curve.start.x
            y = start.y - curve.start.y
            d = x*x* + y*y

            if d < shortest:
                shortest = d
                selection = curve

        newOrder.append(selection)

        curves.remove(selection)
        start = selection.end
    return newOrder

def getMinMax(LineList):
    t1 = max(LineList,key=lambda x: x.start.x)
    t2 = max(LineList,key=lambda x: x.end.x)
    maxX = max(t1.start.x, t2.end.x)

    t1 = max(LineList,key=lambda x: x.start.y)
    t2 = max(LineList,key=lambda x: x.end.y)
    maxY = max(t1.start.y, t2.end.y)

    t1 = min(LineList,key=lambda x: x.start.x)
    t2 = min(LineList,key=lambda x: x.end.x)
    minX = min(t1.start.x, t2.end.x)

    t1 = min(LineList,key=lambda x: x.start.y)
    t2 = min(LineList,key=lambda x: x.end.y)
    minY = min(t1.start.y, t2.end.y)

    print("X max:", maxX, " min:", minX)
    print("Y max:", maxY, " min:", minY)

    return( maxX,maxY,minX,minY)
