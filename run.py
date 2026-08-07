import typing
import warnings
import math

from svg_to_gcode.compiler.interfaces import Interface, cutterInterface
from svg_to_gcode.geometry import Curve, Line
from svg_to_gcode.geometry import LineSegmentChain
from svg_to_gcode import UNITS, TOLERANCES

from svg_to_gcode.geometry import Vector
from svg_to_gcode.svg_parser import parse_file, getMinMax, sortCurves,scaleLines, openFile,getOutputFileName, drawOpts
from svg_to_gcode.compiler import Compiler,CompilerPC, interfaces
from svg_to_gcode import formulas

verbose = False


# working
offsetX = -82 # 4mm offset + 78mm tool distance
offsetZ = 57.5
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
gcode_compiler = CompilerPC(cutterInterface, movement_speed=25000, cutting_speed=3000, pass_depth=1,custom_header=custom_header,custom_footer=custom_footer)


# filename = "dice.svg"
# filename = "box100.svg"
# filename = "Elephant_small_8.svg"
# filename = "Rhombische_Dodekaeder_solidModel_0.svg"
# from svg_to_gcode.svg_parser import drawOpts
# filename = "elephant_10x_0.svg"
# filename = "12eck.svg"
# filename = "elephant_2022_r2.svg"
# filename = "huhn_v3.svg"
# filename = "HEV_Chest_scale.svg"
# filename = "HEVMIR.svg"
# filename = "HEV Belt-unfold 32 inch.svg"
# filename = "HEV_Chest_scale.svg"

filename = "random_rectangles.svg"

# filename = openFile("E:/Documents/surrealLabor/")

dOpts = drawOpts()
dOpts.doFiltering = True

### Pepakura Files ###
# groves
dOpts.filter = 'stroke-dasharray' # for groves for Pepakura Files
groves = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

print("Size Groves")
maxXg,maxYg,minXg,minYg = getMinMax(groves)

#cuts
dOpts.filter = None # for cuts for Pepakura Files
cuts = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

print("Size Cuts")
maxXg,maxYg,minXg,minYg = getMinMax(cuts)

Xoffset = 0
Yoffset = 1500 - max(maxYg, maxYg) - 20


# add(groves)
gcode_compiler.append_code([f"; Groves"])
gcode_compiler.cutting_speed = 5000
gcode_compiler.slopeMax = math.radians(180)
gcode_compiler.append_curves(groves,0,Xoffset,Yoffset)

# add(cuts)
gcode_compiler.append_code([f"; Cuts"])
gcode_compiler.cutting_speed = 3000
gcode_compiler.slopeMax = math.radians(10)
gcode_compiler.append_curves(cuts,1,Xoffset,Yoffset) 

# final cut 
gcode_compiler.append_code([f"; Final Cut"])
finalCut = cuts[0]
finalCut.start.x = -10
finalCut.end.x = 1250 + abs(offsetX)
finalCut.end.y = Yoffset -20
finalCut.start.y = Yoffset -20
finalCuts = []
finalCuts.append(finalCut)
gcode_compiler.append_curves(finalCuts,1,0,0) 

gcode_compiler.append_code([f"; End Code"])


# Output File
print("Final Size")
outputFilename = filename.replace('.svg','_5.gcode')
gcode_compiler.compile_to_file(outputFilename, passes=1)
gcode_compiler.interface.view()



### Other SVG Files ###
# dOpts.filter = None
# dOpts.filter = "plot"
# plots = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves
# gcode_compiler.cutting_speed = 3000
# gcode_compiler.slopeMax = math.radians(10)
# gcode_compiler.append_curves(plots,1) 
