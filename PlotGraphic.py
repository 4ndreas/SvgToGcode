import math

from svg_to_gcode.compiler.interfaces import cutterInterface
from svg_to_gcode.svg_parser import parse_file, getMinMax, sortCurves, openFile,getOutputFileName, drawOpts
from svg_to_gcode.compiler import CompilerPC
from svg_to_gcode.svg_parser._dxf_importer import importDXF
from svg_to_gcode.geometry import Text, Line
from svg_to_gcode.geometry._vector import Vector

verbose = False
removeXoffset = False
removeYoffset = False

globalYOffset = 1500

plotText = False
TextSize = 2

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

filename = openFile()
print("\r\nOpen File: " + filename + "\r\n")

if filename.__contains__(".svg"):
    dOpts = drawOpts()
    dOpts.doFiltering = True
    ### SVG Files ###

    #cuts
    dOpts.filter = None # for cuts for Pepakura Files
    graphics = parse_file(filename,True,None,dOpts) # Parse an svg file into geometric curves
    # grafics = sortCurves(grafics)

    #text
    dOpts.filter = 'text' # for cuts for Pepakura Files
    text = parse_file(filename,True,None,dOpts) # Parse an svg file into geometric curves

# elif filename.__contains__(".dxf"):
#     grafics, groves,text = importDXF(filename)
#     groves = sortCurves(groves)
#     grafics = sortCurves(grafics)


print("Size Cuts")
maxXc,maxYc,minXc,minYc = getMinMax(graphics)

Xoffset = 0.0
Yoffset = 0.0

if removeXoffset:
    # shift to left
    Xoffset = -minXc

if removeYoffset:
    # shift up
    Yoffset = globalYOffset -  maxYc - 20.0 

# add(Text)
if len(text) > 0 and plotText:
    gcode_compiler.append_code([f"; Text"])
    gcode_compiler.append_text(text, TextSize, 2500, Xoffset + penOffsetX, Yoffset + penOffsetY)

# add(Grafic)
if len(graphics) > 0:
    gcode_compiler.append_code([f"; Grafic"])
    gcode_compiler.cutting_speed = 2500
    gcode_compiler.overCut = 0.0
    gcode_compiler.preCut = 0.0
    gcode_compiler.slopeMax = math.radians(360)
    gcode_compiler.append_curves(graphics,2,Xoffset + penOffsetX, Yoffset + penOffsetY)


gcode_compiler.append_code([f"; End Code"])

# Output File
outputFilename = getOutputFileName(filename)
gcode_compiler.compile_to_file(outputFilename, passes=1)
print("\r\nFile saved to: " + outputFilename + "\r\n")


print("Final Size")
# gcode_compiler.interface.view()

