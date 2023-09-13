from svg_to_gcode.geometry import Vector
from svg_to_gcode.geometry import Curve
from svg_to_gcode import formulas
import math

# A line segment
class Text(Curve):
    """The Line class inherits from the abstract Curve class and describes a straight line segment."""

    __slots__ = 'pos','slope','text'

    def __init__(self, x, y, a, text):
        self.pos = Vector(x,y)
        self.slope = a
        self.text = text

    def __repr__(self):
        return f"Text(pos:{self.start}, slope:{self.slope}, text:{self.text})"

    def length(self):
        return 0

    def point(self, t):
        x = self.start.x
        y = self.start.y
        return Vector(x, y)

    def derivative(self, t):
        return self.slope
