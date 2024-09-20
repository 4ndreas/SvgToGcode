import math

from svg_to_gcode.compiler.interfaces import cutterInterface
from svg_to_gcode.svg_parser import parse_file, getMinMax, sortCurves,scaleLines, openFile,getOutputFileName, drawOpts
from svg_to_gcode.compiler import CompilerPC
from svg_to_gcode.svg_parser._dxf_importer import importDXF, importAllDXF
from svg_to_gcode.geometry import Text, Line
from svg_to_gcode.geometry._vector import Vector

verbose = False
removeXoffset = True
removeYoffset = True

globalYOffset = 1500

# working
offsetX = -82 # 4mm offset + 78mm tool distance
offsetZ = 58
offsetW = 59

penOffsetX = 0
penOffsetY = -42.5

workingOffsetX = 10
workingOffsetY = 0

# test
# offsetZ = 48
# offsetW = 49

# offsetA = -82
# offsetB = -94


custom_header = [f"G28 Z W\nG92 Z{offsetZ} W{offsetW}\n@penhome\nG28 A B\nG1 A0 B0 F10000\nG28 X Y\nG92 X{offsetX}\nG0 X{workingOffsetX} Y{workingOffsetY} F10000\nG92 X0 Y0 \n"]

custom_footer = [f"G1 Z{offsetZ-5} W{offsetW-5}\nG1 X0 Y0 F15000\nM9"]

gcode_compiler = CompilerPC(cutterInterface, movement_speed=25000,
                             cutting_speed=3000, 
                             pass_depth=1,
                             custom_header=custom_header,
                             custom_footer=custom_footer)

gcode_compiler.append_code([f";T{0}", gcode_compiler.interface.toolPark(0)])
gcode_compiler.append_code([f";T{1}", gcode_compiler.interface.toolPark(1)])


scale = 1.0
finalCutMM = 15

# filename = "E:/Documents/Inventor/ato/sq60.dxf"
# filename = openFile("E:/Documents/Inventor/Halter/huhnProject")
filename = "E:/Documents/Inventor/Halter/huhnProject/Box200mm_cut2.dxf"
print("\r\nOpen File: " + filename + "\r\n")
cuts = importAllDXF(filename)
cuts = sortCurves(cuts)
cuts = scaleLines(cuts,scale,scale)

# filename2 = openFile("E:/Documents/Inventor/Halter/huhnProject")
filename2 = "E:/Documents/Inventor/Halter/huhnProject/Box200mm_grove2.dxf"
# print("\r\nOpen File: " + filename2 + "\r\n")
groves = list()
groves = importAllDXF(filename2)
groves = sortCurves(groves)
groves = scaleLines(groves,scale,scale)

text =  []

print("Size Groves")
maxXg,maxYg,minXg,minYg = getMinMax(groves)
print("Size Cuts")
maxXc,maxYc,minXc,minYc = getMinMax(cuts)

Xoffset = 0.0
Yoffset = 0.0

if removeXoffset:
    # shift to left
    Xoffset = -min(minXg,minXc)

if removeYoffset:
    # shift up
    Yoffset = globalYOffset - max(maxYg, maxYc) - 20.0 


# GRID
for n in range(0,1):
    gridOffset = 0
    if n == 0:
        gOffsetX = Xoffset
        gOffsetY = Yoffset 
    else:
        gOffsetX = 400
        gOffsetY = 0
    ## add(Text)
    if len(text) > 0:
        gcode_compiler.append_code([f"; Text"])
        gcode_compiler.append_text(text, 2, 2500, Xoffset + penOffsetX + gOffsetX, Yoffset + penOffsetY + gOffsetY)

    ## add(groves)
    if len(groves) > 0:
        gcode_compiler.append_code([f"; Groves"])
        gcode_compiler.cutting_speed = 5000
        gcode_compiler.slopeMax = math.radians(180)
        gcode_compiler.append_curves(groves,0, gOffsetX, gOffsetY)

    ## add(cuts)
    if len(cuts) > 0:
        gcode_compiler.append_code([f"; Cuts"])
        gcode_compiler.cutting_speed = 7500
        gcode_compiler.slopeMax = math.radians(15)
        gcode_compiler.append_curves(cuts,1, gOffsetX, gOffsetY) 

# final cut 
gcode_compiler.append_code([f"; Final Cut"])

cutY = Yoffset = globalYOffset - (max(maxYg, maxYc) - min(minYc,minYc) ) - 20
start = Vector(-16, cutY -20)
end = Vector(1280, cutY -20)

finalCut = Line(start, end)
finalCuts = []
finalCuts.append(finalCut)
gcode_compiler.append_curves(finalCuts,1,0,0) 

gcode_compiler.append_code([f"; End Code"])

# Output File
outputFilename = getOutputFileName(filename)
gcode_compiler.compile_to_file(outputFilename, passes=1)
print("\r\nFile saved to: " + outputFilename + "\r\n")


print("Final Size")
print("final Cut Y {}".format(cutY))
gcode_compiler.interface.view()


