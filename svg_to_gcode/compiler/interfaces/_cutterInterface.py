import typing
import warnings
import math


from svg_to_gcode.geometry import Curve, Line
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES

from svg_to_gcode.geometry import Vector
from svg_to_gcode.compiler import interfaces
from svg_to_gcode import formulas

verbose = False

class cutterInterface(interfaces.Gcode):
    def __init__(self):
        super().__init__()
        self.Zlift = 5.5
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

    def getSlope(self,tool=0, slope=0):
        self.tool = tool
        #to do convert to degree
        self.slope[tool] = slope

        degSlope = math.degrees(self.slope[tool])

        sArrow = (self.position.x, self.position.y,self.positionZ, 5*math.cos(slope),5*math.sin(slope),0)
        self.orientation_history.append(sArrow)

        return degSlope
           
    def setSlope(self, tool=0, slope=0):
        degSlope = self.getSlope(tool, slope)

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

    def combinedLinearMove(self, x=None, y=None, z=None, tool=0, slope=0):
        linearMove = self.linear_move( x, y, z)
        degSlope = self.getSlope(tool, slope)

        if tool == 1:
            slopeGC=  f" B{degSlope:.{self.precision}f}" 
        else:
            slopeGC=  f" A{degSlope:.{self.precision}f}" 

        return  linearMove.replace(f" F", slopeGC + f" F", 1)

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
            # plt.show(block=False)
        elif backend == 'mayavi':
            from mayavi import mlab
            mlab.plot3d(history[:, 0], history[:, 1], history[:, 2])
        else:
            raise Exception("Invalid plotting backend! Choose one of mayavi or matplotlib.")


