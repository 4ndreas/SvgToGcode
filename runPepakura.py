import math

from svg_to_gcode.compiler.interfaces import cutterInterface
from svg_to_gcode.svg_parser import parse_file, getMinMax, drawOpts
from svg_to_gcode.compiler import CompilerPC

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

custom_footer = [f"G1 Z{offsetZ-5} W{offsetW-5}\nG1 X0 Y0 F15000\nM9"]

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
filename = "HEV_Chest_scale.svg"

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
finalCut.end.x = 1280 + abs(offsetX)
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
