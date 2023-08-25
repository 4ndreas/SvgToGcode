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
        self.Zlift = 5.0
        self.ZPark = 25.0
        self.ZCut = 0
        self.ZFeed = 7000

        self.overCut = 0.3  # value the cut extends over the point
        self.preCut = -0.75 # value the cut begins before the point (negative to extend the line, positive to reduce the line cut)

        # cutting and grove rotation speed 
        self.ABFeed = 25000
        self.slope = [0.0, 0.0] #[rad]

        # self.position = Vector(0, 0)
        self.position = None

        self.position_history_travel= [(0,0,0,0,0,0)]
        self.position_history_t0 = [(0,0,0,0,0,0)]
        self.position_history_t1 = [(0,0,0,0,0,0)]
        self.orientation_history = [(0,0,0,0,0,0)]

        self.xMax = 0
        self.yMax = 0

        self.positionZ = 0.0 # z u v 
        self.currentMove = -1
        self.tool = 0
        self.toolOffset = [(0, 0, 0,0)]
        self.toolOffset.append((-78,0,0,0))

    def addHistory(self,move):
        if self.currentMove==0:
            # self.position_history_t0.append((self.position.x, self.position.y, self.positionZ))
            self.position_history_t0.append(move)
        elif self.currentMove==1:
            # self.position_history_t1.append((self.position.x, self.position.y, self.positionZ))
            self.position_history_t1.append(move)
        else:
            self.position_history_travel.append(move)
            # self.position_history_travel.append((self.position.x, self.position.y, self.positionZ))
        # if move[0] > self.xMax:
        #     self.xMax = move[0]
        # if move[1] > self.yMax:
        #     self.yMax = move[1]          

    def addOverCut(self, tool, amount, dir):
        command = "G1"
        # extend cut (G1 cutting)
        if dir > 0:
            slope = self.slope[tool]    #[rad]
            comment = " ; overCut"
        else:
        # move back to start cut early normaly G0 but since it is such a small amount we go with G1
        # this should only happen if the tool head is up 
            slope = self.slope[tool]    #[rad]
            slope += 2*math.pi          # rotate to move backwards
            comment = " ; preCut"

        x, y = formulas.lineExtension(self.position.x,self.position.y,slope,amount)

        xMove = x + self.toolOffset[self.tool][0]
        yMove = y + self.toolOffset[self.tool][1]

        command += f" X{xMove:.{self.precision}f}"
        command += f" Y{yMove:.{self.precision}f}"
        command += f" F{self._current_speed}"
        
        return command + comment



    def toolUp(self, tool=0):
        self.tool = tool
        self.positionZ = self.ZCut + self.Zlift

        deltaZ = self.Zlift -self.positionZ
        move = (self.position.x,self.position.y,self.positionZ ,0,0,deltaZ )
        self.addHistory(move)

        if tool == 1:
            return f"G1 W{self.positionZ:.{self.precision}f} F{self.ZFeed:.{self.precision}f}; lift up"
        else:
            return f"G1 Z{self.positionZ:.{self.precision}f} F{self.ZFeed:.{self.precision}f} ; lift up"

    def toolPark(self, tool=0):
        self.tool = tool
        self.positionZ = self.ZCut + self.ZPark

        deltaZ = self.ZPark -self.positionZ
        move = (self.position.x,self.position.y,self.positionZ ,0,0,deltaZ )
        self.addHistory(move)

        if tool == 1:
            return f"G1 W{self.positionZ:.{self.precision}f} F{self.ZFeed:.{self.precision}f}; lift up"
        else:
            return f"G1 Z{self.positionZ:.{self.precision}f} F{self.ZFeed:.{self.precision}f} ; lift up"

    def toolDown(self, tool=0):
        self.tool = tool
        #to do add toolhead selection
        self.positionZ = self.ZCut

        deltaZ = self.positionZ - self.Zlift
        move = (self.position.x,self.position.y,self.positionZ ,0,0, deltaZ )
        self.addHistory(move)

        if tool == 1:
            return f"G1 W{self.positionZ:.{self.precision}f} F{self.ZFeed:.{self.precision}f} ; lift down" 
        else:
            return f"G1 Z{self.positionZ:.{self.precision}f} F{self.ZFeed:.{self.precision}f} ; lift down"   

    def setSlope(self, tool=0, slope=0):
        self.tool = tool
        #to do convert to degree
        self.slope[tool] = slope

        degSlope = math.degrees(self.slope[tool])

        sArrow = (self.position.x, self.position.y,self.positionZ, 5*math.cos(slope),5*math.sin(slope),0)
        self.orientation_history.append(sArrow)

        if tool == 1:
            
            return f"G1 B{degSlope:.{self.precision}f} F{self.ABFeed:.{self.precision}f}" 
        else:
            return f"G1 A{degSlope:.{self.precision}f} F{self.ABFeed:.{self.precision}f}" 

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

        # self.addHistory()
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

            move = (self.position.x, self.position.y, self.positionZ,
                        x-self.position.x,
                        y-self.position.y, 0)
            self.addHistory(move)

            # if(self.currentMove >= 0):
            #     self.position = Vector(x, y) + self.toolOffset[self.currentMove]
            # else:
                # self.position = Vector(x, y)
            self.position = Vector(x, y)

            # if z is None:
            #     z = self.positionZ     

        # self.addHistory()

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

        history_or = np.array(self.orientation_history)

        if backend == 'matplotlib':
            from mpl_toolkits.mplot3d import Axes3D
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            X, Y, Z = history_travel[:, 0], history_travel[:, 1], history_travel[:, 2]
            # ax.plot(X, Y, Z, "bo--")
            
            
            # Hack to keep 3D plot's aspect ratio square. See SO answer:
            # http://stackoverflow.com/questions/13685386

            print("X max:", X.max(), " min:", X.min())
            print("Y max:", Y.max(), " min:", Y.min())

            max_range = np.array([X.max()-X.min(),
                                  Y.max()-Y.min(),
                                  Z.max()-Z.min()]).max() / 2.0

            mean_x = X.mean()
            mean_y = Y.mean()
            mean_z = Z.mean()
            ax.set_xlim(mean_x - max_range, mean_x + max_range)
            ax.set_ylim(mean_y - max_range, mean_y + max_range)
            ax.set_zlim(mean_z - max_range, mean_z + max_range)

            # travel
            ax.quiver(history_travel[:,0],history_travel[:,1],history_travel[:,2],history_travel[:,3],history_travel[:,4],history_travel[:,5],color='g')
            
            # rot axis
            ax.quiver(history_or[:,0],history_or[:,1],history_or[:,2],history_or[:,3],history_or[:,4],history_or[:,5],color='y')

            # T0
            ax.quiver(history_t0[:,0],history_t0[:,1],history_t0[:,2],history_t0[:,3],history_t0[:,4],history_t0[:,5],color='b')
            # T1
            ax.quiver(history_t1[:,0],history_t1[:,1],history_t1[:,2],history_t1[:,3],history_t1[:,4],history_t1[:,5])

            # X, Y, Z = history_t0[:, 0], history_t0[:, 1], history_t0[:, 2]
            # ax.plot(X, Y, Z, color='green')

            # X, Y, Z = history_t1[:, 0], history_t1[:, 1], history_t1[:, 2]
            # ax.plot(X, Y, Z,  color='red')      

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

        code = [f";T{tool}", self.interface.toolPark(tool)]
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

            # add precut
            start.x, start.y = formulas.lineExtension(start.x, start.y, slope + 2*math.pi, self.interface.preCut)

            code = [f";T{tool}",
                    self.interface.toolUp(tool),
                    self.interface.set_movement_speed(self.movement_speed),
                    self.interface.linear_move(start.x, start.y), 
                    self.interface.setSlope(tool,slope),
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


# working
offsetX = -82 # 4mm offset + 78mm tool distance
offsetZ = 58
offsetW = 59

workingOffsetX = 10
workingOffsetY = 0

# test
# offsetZ = 48
# offsetW = 49

# offsetA = -82
# offsetB = -94


custom_header = [f"G28 X\nG92 X{offsetX}\nG0 X{workingOffsetX} Y{workingOffsetY} F10000\nG92 X0 Y0 \nG28 Z W\nG92 Z{offsetZ} W{offsetW}\nG28 A B\nG1 A0 B0 F10000\n"]
# custom_header = [f"G28 Z W\nG92 Z{offsetZ} W{offsetW}\nG28 A B\nG1 A0 B0 F10000\nG92 A{offsetA} B{offsetB}\nG1 A0 B0 F10000\n"]
# custom_header = ["G28 Z\nG92 Z20\nG28 W\nG92 W20"]  # debug 

custom_footer = [f"G1 Z{offsetZ-5} W{offsetW-5}\nG1 X0 Y0 F15000\nM9"]

# Instantiate a compiler, specifying the interface type and the speed at which the tool should move. pass_depth controls
# how far down the tool moves after every pass. Set it to 0 if your machine does not support Z axis movement.
gcode_compiler = P2Compiler(CustomInterface, movement_speed=25000, cutting_speed=3000, pass_depth=1,custom_header=custom_header,custom_footer=custom_footer)


# filename = "dice.svg"
# filename = "box100.svg"
# filename = "Elephant_small_8.svg"
# filename = "Rhombische_Dodekaeder_solidModel_0.svg"
# from svg_to_gcode.svg_parser import drawOpts
# filename = "elephant_10x_0.svg"
# filename = "12eck.svg"
# filename = "elephant_2022_r2.svg"
filename = "huhn_v3.svg"

dOpts = drawOpts()
dOpts.doFiltering = True

### Pepakura Files ###
# groves
dOpts.filter = 'stroke-dasharray' # for groves for Pepakura Files
groves = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

#cuts
dOpts.filter = None # for cuts for Pepakura Files
cuts = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

# add(groves)
gcode_compiler.cutting_speed = 5000
gcode_compiler.slopeMax = math.radians(180)
gcode_compiler.append_curves(groves,0)

# add(cuts)
gcode_compiler.cutting_speed = 3000
gcode_compiler.slopeMax = math.radians(10)
gcode_compiler.append_curves(cuts,1) 


### Other SVG Files ###
# dOpts.filter = None
# dOpts.filter = "plot"
# plots = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves
# gcode_compiler.cutting_speed = 3000
# gcode_compiler.slopeMax = math.radians(10)
# gcode_compiler.append_curves(plots,1) 



# Output File
outputFilename = filename.replace('.svg','_5.gcode')
gcode_compiler.compile_to_file(outputFilename, passes=1)
gcode_compiler.interface.view()



