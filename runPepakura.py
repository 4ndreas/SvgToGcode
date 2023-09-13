import math

from svg_to_gcode.compiler.interfaces import cutterInterface
from svg_to_gcode.svg_parser import parse_file, getMinMax, openFile,getOutputFileName, drawOpts
from svg_to_gcode.compiler import CompilerPC
# from svg_to_gcode.TextToGcode.ttgLib.TextToGcode import ttg

verbose = False

# working
offsetX = -82 # 4mm offset + 78mm tool distance
offsetZ = 57.5
offsetW = 59
penOffsetX = 0
penOffsetY = 0

workingOffsetX = 10
workingOffsetY = 0

# test
# offsetZ = 48
# offsetW = 49

# offsetA = -82
# offsetB = -94


custom_header = [f"G28 X\nG92 X{offsetX}\nG0 X{workingOffsetX} Y{workingOffsetY} F10000\nG92 X0 Y0 \nG28 Z W\nG92 Z{offsetZ} W{offsetW}\nG28 A B\nG1 A0 B0 F10000\n"]

custom_footer = [f"G1 Z{offsetZ-5} W{offsetW-5}\nG1 X0 Y0 F15000\nM9"]

gcode_compiler = CompilerPC(cutterInterface, movement_speed=25000,
                             cutting_speed=3000, 
                             pass_depth=1,
                             custom_header=custom_header,
                             custom_footer=custom_footer)

filename = openFile()
print("\r\nOpen File: " + filename + "\r\n")


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

Xoffset = 0.0
Yoffset = 1500.0 - max(maxYg, maxYg) - 20.0

#text
dOpts.filter = 'text' # for cuts for Pepakura Files
text = parse_file(filename,False,None,dOpts) # Parse an svg file into geometric curves

# add(Text)
gcode_compiler.append_code([f"; Text"])
gcode_compiler.append_text(text, 2500, Xoffset, Yoffset)

# add(groves)
gcode_compiler.append_code([f"; Groves"])
gcode_compiler.cutting_speed = 5000
gcode_compiler.slopeMax = math.radians(180)
gcode_compiler.append_curves(groves,0,Xoffset + penOffsetX , Yoffset + penOffsetY)

# add(cuts)
gcode_compiler.append_code([f"; Cuts"])
gcode_compiler.cutting_speed = 3000
gcode_compiler.slopeMax = math.radians(10)
gcode_compiler.append_curves(cuts,1,Xoffset,Yoffset) 

# final cut 
gcode_compiler.append_code([f"; Final Cut"])
finalCut = cuts[0]
finalCut.start.x = -10
finalCut.end.x = 1260 # + abs(offsetX)
finalCut.end.y = Yoffset -20
finalCut.start.y = Yoffset -20
finalCuts = []
finalCuts.append(finalCut)
gcode_compiler.append_curves(finalCuts,1,0,0) 

gcode_compiler.append_code([f"; End Code"])

# Output File
outputFilename = getOutputFileName(filename)
gcode_compiler.compile_to_file(outputFilename, passes=1)
print("\r\nFile saved to: " + outputFilename + "\r\n")


print("Final Size")
gcode_compiler.interface.view()

