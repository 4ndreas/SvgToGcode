import typing
import warnings
import math


from svg_to_gcode.compiler.interfaces import Interface
from svg_to_gcode.geometry import Curve, Line
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES

from svg_to_gcode.geometry import Vector
from svg_to_gcode.svg_parser import parse_file, drawOpts
from svg_to_gcode.compiler import Compiler, interfaces
from svg_to_gcode import formulas

verbose = False

class CustomInterface(interfaces.Gcode):
    def __init__(self):
        super().__init__()
        self.Zlift = 4.0
        self.ZCut = 0
        self.ZFeed = 5000
        self.ABFeed = 15000
        self.slope = [0.0, 0.0]
        # self.position = Vector(0, 0)
        self.position = None
        self.position_history_travel = [(0, 0, 0)]
        self.position_history_t0 = [(0, 0, 0)]
        self.position_history_t1 = [(0, 0, 0)]
        self.positionZ = 0.0 # z u v 
        self.currentMove = -1
        self.tool = 0
        self.toolOffset = [(0, 0, 0,0)]
        self.toolOffset.append((-78,0,0,0))

    def addHistory(self):
        if self.currentMove==0:
            self.position_history_t0.append((self.position.x, self.position.y, self.positionZ))
        elif self.currentMove==1:
            self.position_history_t1.append((self.position.x, self.position.y, self.positionZ))
        else:
            self.position_history_travel.append((self.position.x, self.position.y, self.positionZ))

    def toolUp(self, tool=0):
        self.tool = tool
        self.positionZ = self.ZCut + self.Zlift
        self.addHistory()
        if tool == 1:
            return f"G1 W{self.positionZ} F{self.ZFeed}; lift up"
        else:
            return f"G1 Z{self.positionZ} F{self.ZFeed} ; lift up"

    def toolDown(self, tool=0):
        self.tool = tool
        #to do add toolhead selection
        self.positionZ = self.ZCut
        self.addHistory()
        if tool == 1:
            return f"G1 W{self.positionZ} F{self.ZFeed} ; lift down" 
        else:
            return f"G1 Z{self.positionZ} F{self.ZFeed} ; lift down"   

    def setSlope(self, tool=0, slope=0):
        self.tool = tool
        #to do convert to degree
        self.slope[tool] = slope
        self.addHistory()

        degSlope = math.degrees(self.slope[tool])

        degSlope = degSlope - 90
        if degSlope <0:
            degSlope = degSlope + 360
        degSlope = 360 - degSlope

        if tool == 1:
            
            return f"G1 B{degSlope} F{self.ABFeed}" 
        else:
            return f"G1 A{degSlope} F{self.ABFeed}" 

    def append_curves(self, curves: [typing.Type[Curve]], tool):
        """
        Draws curves by approximating them as line segments and calling self.append_line_chain(). The resulting code is
        appended to self.body
        """
        self.tool = tool

        for curve in curves:
            line_chain = LineSegmentChain()

            approximation = LineSegmentChain.line_segment_approximation(curve)

            line_chain.extend(approximation)

            self.append_line_chain(line_chain,tool)
        
    def linear_move(self, x=None, y=None, z=None):

        self.addHistory()
        if self._next_speed is None:
            raise ValueError("Undefined movement speed. Call set_movement_speed before executing movement commands.")

        # Don't do anything if linear move was called without passing a value.
        if x is None and y is None and z is None:
            warnings.warn("linear_move command invoked without arguments.")
            return ''

        # Todo, investigate G0 command and replace movement speeds with G1 (normal speed) and G0 (fast move)
        if self.currentMove >= 0:
            command = "G1"
        else:
            command = "G0"

        if self._current_speed != self._next_speed:
            self._current_speed = self._next_speed
        
        # add tool offset
        xMove = x + self.toolOffset[self.tool][0]
        yMove = y + self.toolOffset[self.tool][1]

        # Move if not 0 and not None
        #add offset only to output not internal position compiler
        command += f" X{xMove:.{self.precision}f}" if x is not None else ''
        command += f" Y{yMove:.{self.precision}f}" if y is not None else ''
        command += f" Z{z:.{self.precision}f}" if z is not None else ''
        
        # allways add speed 
        command += f" F{self._current_speed}"

        if self.position is not None or (x is not None and y is not None):
            if x is None:
                x = self.position.x

            if y is None:
                y = self.position.y

            # if(self.currentMove >= 0):
            #     self.position = Vector(x, y) + self.toolOffset[self.currentMove]
            # else:
                # self.position = Vector(x, y)
            self.position = Vector(x, y)

            # if z is None:
            #     z = self.positionZ     

        self.addHistory()

        if verbose:
            print(f"Move to {x}, {y}, {z}")

        return command + ';'

    def view(self, backend='matplotlib'):
        """ View the generated Gcode.
        Parameters
        ----------
        backend : str (default: 'matplotlib')
            The plotting backend to use, one of 'matplotlib' or 'mayavi'.
        """

        import numpy as np
        history_travel = np.array(self.position_history_travel)
        history_t0 = np.array(self.position_history_t0)
        history_t1 = np.array(self.position_history_t1)

        if backend == 'matplotlib':
            from mpl_toolkits.mplot3d import Axes3D
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            X, Y, Z = history_travel[:, 0], history_travel[:, 1], history_travel[:, 2]
            ax.plot(X, Y, Z, "bo--")

      

            # Hack to keep 3D plot's aspect ratio square. See SO answer:
            # http://stackoverflow.com/questions/13685386

            max_range = np.array([X.max()-X.min(),
                                  Y.max()-Y.min(),
                                  Z.max()-Z.min()]).max() / 2.0

            mean_x = X.mean()
            mean_y = Y.mean()
            mean_z = Z.mean()
            ax.set_xlim(mean_x - max_range, mean_x + max_range)
            ax.set_ylim(mean_y - max_range, mean_y + max_range)
            ax.set_zlim(mean_z - max_range, mean_z + max_range)

            X, Y, Z = history_t0[:, 0], history_t0[:, 1], history_t0[:, 2]
            ax.plot(X, Y, Z, color='green')

            X, Y, Z = history_t1[:, 0], history_t1[:, 1], history_t1[:, 2]
            ax.plot(X, Y, Z,  color='red')      

            plt.show()
        elif backend == 'mayavi':
            from mayavi import mlab
            mlab.plot3d(history[:, 0], history[:, 1], history[:, 2])
        else:
            raise Exception("Invalid plotting backend! Choose one of mayavi or matplotlib.")


class P2Compiler(Compiler):
    def __init__(self, *args, **kwargs):
        super(P2Compiler, self).__init__(*args, **kwargs)
        self.slopeMax = math.radians(10)
        # self.slopeMax = 0.25
        
    def append_curves(self, curves: [typing.Type[Curve]], tool):
        """
        Draws curves by approximating them as line segments and calling self.append_line_chain(). The resulting code is
        appended to self.body
        """

        for curve in curves:
            line_chain = LineSegmentChain()

            approximation = LineSegmentChain.line_segment_approximation(curve)

            line_chain.extend(approximation)

            self.append_line_chain(line_chain,tool)

        code = [f"T{tool}", self.interface.toolUp(tool)]
        self.body.extend(code)

    def append_line_chain(self, line_chain: LineSegmentChain,tool):
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
        # slope = line_chain.get(0).slopeRad
        slope = formulas.line_slopeRad(start, end)

        #set to fast move
        self.interface.currentMove = -1
        # # Don't dwell and turn off laser if the new start is at the current position
        if self.interface.position is None or abs(self.interface.position - start) > TOLERANCES["operation"]:
            # print("move")
            if self.interface.position  == None:
                self.interface.position = Vector(0,0)

            code = [f"T{tool}",
                    self.interface.toolUp(tool),
                    self.interface.set_movement_speed(self.movement_speed),
                    self.interface.linear_move(start.x, start.y), 
                    self.interface.setSlope(tool,slope),
                    self.interface.toolDown(tool),
                    self.interface.set_movement_speed(self.cutting_speed)]

        
        for line in line_chain:
            # print(slope)
            # 
            # print(slope)
            # print(math.degrees(slope))

            slope = formulas.line_slopeRad(self.interface.position , line.end)
            deltaS = slope - self.interface.slope[tool]
            # slope = formulas.line_slopeRad(line.start , line.end)

            # print(f"{self.interface.slope[tool]} {line.slope} {deltaS}")

            if abs(deltaS) > self.slopeMax:
                code.append(self.interface.toolUp(tool))
                code.append(self.interface.setSlope(tool,slope))
                code.append(self.interface.toolDown(tool))
            else:
                if abs(self.interface.slope[tool]- slope) > TOLERANCES["operation"]:
                    code.append(self.interface.setSlope(tool,slope))
            
            #set to tool move
            self.interface.currentMove = tool
            self.interface.tool = tool
            code.append(self.interface.linear_move(line.end.x, line.end.y))
            
        self.body.extend(code)


offsetZ = 58
offsetW = 65
offsetA = 8
offsetB = -4


custom_header = [f"G28 Z W\nG92 Z{offsetZ} W{offsetW}\nG28 A B\nG1 A0 B0 F10000\nG92 A{offsetA} B{offsetB}\nG1 A0 B0 F10000\n"]
# custom_header = ["G28 Z\nG92 Z20\nG28 W\nG92 W20"]  # debug 

custom_footer = ["G1 Z20 W20\nG1 X0 Y0 F10000\nM9"]

# Instantiate a compiler, specifying the interface type and the speed at which the tool should move. pass_depth controls
# how far down the tool moves after every pass. Set it to 0 if your machine does not support Z axis movement.
gcode_compiler = P2Compiler(CustomInterface, movement_speed=7500, cutting_speed=2000, pass_depth=1,custom_header=custom_header,custom_footer=custom_footer)


# gcode_compiler.interface.toolOffset[0]
# filename = "dice.svg"

# filename = "box100.svg"
# filename = "Elephant_small_8.svg"
# filename = "Rhombische_Dodekaeder_solidModel_0.svg"
# from svg_to_gcode.svg_parser import drawOpts
filename = "elephant_10x_0.svg"

dOpts = drawOpts()
dOpts.doFiltering = True

dOpts.filter = 'stroke-dasharray' 
groves = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

dOpts.filter = None
cuts = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

# dOpts.filter = "plot"
# plots = parse_file(filename,True,None,dOpts) # Parse an svg file into geometric curves

# print(curves)
gcode_compiler.append_curves(groves,0) 
gcode_compiler.append_curves(cuts,1) 

# z axis offset at home = 200

outputFilename = "drawing.gcode"
outputFilename = "elephant_10x_0.gcode"


gcode_compiler.compile_to_file(outputFilename, passes=1)
gcode_compiler.interface.view()



