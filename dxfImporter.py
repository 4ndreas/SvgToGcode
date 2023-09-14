import sys
import ezdxf
from svg_to_gcode.svg_parser import parse_file, getMinMax, sortCurves, openFile,getOutputFileName, drawOpts
from svg_to_gcode.geometry import Line


filename = openFile()

# try:
#     doc = ezdxf.readfile(filename)
#     pass
# except IOError:
#     print(f"Not a DXF file or a generic I/O error.")
#     sys.exit(1)
# except ezdxf.DXFStructureError:
#     print(f"Invalid or corrupted DXF file.")
#     sys.exit(2)

doc = ezdxf.readfile(filename)


msp = doc.modelspace()

lines = msp.query("LINE")



cuts = msp.query("LINE").layer == "CutLine"

groves = msp.query("LINE").layer == "MountainLine"
groves2 = msp.query("LINE").layer == "ValleyLine"

text = msp.query("TEXT").layer == "Edge ID"

for tx in text.entities:
    x = tx.dxf.insert.x
    y = tx.dxf.insert.y
    a = tx.dxf.rotation
    tx = tx.dxf.text
    # text.curves.append(Text(x,y,a,tx))


print("end")