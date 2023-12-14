import typing
import warnings
import math

from svg_to_gcode.compiler import Compiler
from svg_to_gcode.compiler.interfaces import Interface
from svg_to_gcode.geometry import Curve, Line, Text
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES
from svg_to_gcode import formulas
from svg_to_gcode.geometry import Vector

from svg_to_gcode.TextToGcode.ttgLib.TextToGcode import ttg

class CompilerPC(Compiler):
    def __init__(self, *args, **kwargs):
        super(CompilerPC, self).__init__(*args, **kwargs)
        self.slopeMax = math.radians(10)

    def append_code(self,code):
        self.body.extend(code)
    

    def append_curves(self, curves: [typing.Type[Curve]], tool,offsetX = 0, offsetY = 0):
        """
        Draws curves by approximating them as line segments and calling self.append_line_chain(). The resulting code is
        appended to self.body
        """
        if len(curves) == 0:
            return()

        for curve in curves:
            line_chain = LineSegmentChain()

            approximation = LineSegmentChain.line_segment_approximation(curve)

            line_chain.extend(approximation)

            self.append_line_chain(line_chain,tool,offsetX,offsetY)

        code = [f";T{tool}", self.interface.toolPark(tool)]
        self.body.extend(code)

    def append_line_chain(self, line_chain: LineSegmentChain,tool, offsetX = 0, offsetY = 0):
        """
        Draws a LineSegmentChain by calling interface.linear_move() for each segment. The resulting code is appended to
        self.body
        """

        if line_chain.chain_size() == 0:
            warnings.warn("Attempted to parse empty LineChain")
            return []

        code = []

        start = line_chain.get(0).start
        end = line_chain.get(0).end
        
        for line in line_chain:
            line.start.x += offsetX
            line.end.x += offsetX
            line.start.y += offsetY
            line.end.y += offsetY

        # slope = line_chain.get(0).slopeRad
        slope = formulas.line_slopeRad(start, end)

        #set to fast move
        self.interface.currentMove = -1
        # # Don't dwell and turn off laser if the new start is at the current position
        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:
            # print("move")
            if self.interface.position  == None:
                self.interface.position = Vector(0,0)

            # add precut
            start.x, start.y = formulas.lineExtension(start.x, start.y, slope + 2*math.pi, self.interface.preCut)

            code = [f";T{tool}",
                    self.interface.toolUp(tool),
                    self.interface.set_movement_speed(self.movement_speed),
                    # self.interface.linear_move(start.x, start.y), 
                    # self.interface.setSlope(tool,slope),
                    self.interface.combinedLinearMove(start.x, start.y, None,tool,slope),
                    self.interface.toolDown(tool),
                    self.interface.set_movement_speed(self.cutting_speed)]

        
        for line in line_chain:

            lastSlope = self.interface.slope[tool]

            slope = formulas.line_slopeRad(self.interface.position , line.end)
            deltaS = slope - self.interface.slope[tool]
            # slope = formulas.line_slopeRad(line.start , line.end)

            # print(f"{self.interface.slope[tool]} {line.slope} {deltaS}")

            if abs(deltaS) > self.slopeMax:
                #add overcut 
                code.append(self.interface.addOverCut(tool, self.interface.overCut, 1))
                code.append(self.interface.toolUp(tool))
                code.append(self.interface.setSlope(tool,slope))
                #add precut 
                code.append(self.interface.addOverCut(tool, self.interface.preCut, -1))
                code.append(self.interface.toolDown(tool))
            else:
                if abs(self.interface.slope[tool]- slope) > TOLERANCES["operation"]:
                    code.append(self.interface.setSlope(tool,slope))
            
            #set to tool move
            self.interface.currentMove = tool
            self.interface.tool = tool
            code.append(self.interface.linear_move(line.end.x, line.end.y))
            
        self.body.extend(code)


    def append_text(self, curves: [typing.Type[Curve]],size = 1, feedrate=1000, offsetX = 0.0, offsetY = 0.0):
        """
        Draws curves by approximating them as line segments and calling self.append_line_chain(). The resulting code is
        appended to self.body
        """
        # penDown = f"G1 Z{self.interface.ZPenDown} F{self.interface.ZFeed:.{self.interface.precision}f}"
        # penUp = f"G1 Z{self.interface.ZPenUp} F{self.interface.ZFeed:.{self.interface.precision}f}"

        penDown = "@penDown"
        penUp = "@penUp"
        ## To Do add Pen start code and offset
        
        gcode = [f";T3", 
                 "G1 Z{self.interface.ZPark} W{self.interface.ZPark} F7000.0000 ;",
                 "@pendeploy"]
               
        self.body.extend(gcode)
        
        for text in curves:
            # text = Text(text)
            x = float(text.pos.x) + offsetX
            y = float(text.pos.y) + offsetY
            gcode = [f";Text: {text.text}",
                     penUp,
                     f"G0 X{x} Y{y} F{self.movement_speed}"]
            self.body.extend(gcode)

            gcode = ttg(text.text,size,int(text.slope),x,y,"return",feedrate).toGcode(penDown,penUp,"G0","G1")
            # print(gcode)
            
            self.body.extend(gcode)
                        

        ## To Do add Pen endcode code and offset        
        gcode = [f";T3 end", 
                 "G1 Z{self.interface.ZPark} W{self.interface.ZPark} F7000.0000 ;",
                 "@penraise"]
               
        self.body.extend(gcode)             