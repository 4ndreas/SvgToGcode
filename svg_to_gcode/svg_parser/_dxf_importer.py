import sys
import ezdxf
from typing import List
from copy import deepcopy

from svg_to_gcode.svg_parser import Path,  Transformation
from svg_to_gcode.geometry import Curve,Text, Line
from svg_to_gcode.geometry._vector import Vector


def importDXF(file_path: str )-> (List[Curve],List[Curve],List[Curve]):
    canvas_height = 1500
    # cuts  = Path("", canvas_height)
    # groves  = Path("", canvas_height)
    # text =  Path("", canvas_height)
    cuts  = []
    groves  = []
    text =  []

    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    dCuts = msp.query("LINE").layer == "CutLine"

    dMountainGroves = msp.query("LINE").layer == "MountainLine"
    dValleyGroves = msp.query("LINE").layer == "ValleyLine"

    dText = msp.query("TEXT").layer == "Edge ID"

    # add cuts
    for entitie in dCuts.entities:  
        start = Vector(entitie.dxf.start.x, entitie.dxf.start.y)
        end = Vector(entitie.dxf.end.x, entitie.dxf.end.y)
        cuts.append(Line(start, end))
                    
    # add groves
    for entitie in dMountainGroves.entities:  
        start = Vector(entitie.dxf.start.x, entitie.dxf.start.y)
        end = Vector(entitie.dxf.end.x, entitie.dxf.end.y)
        groves.append(Line(start, end))

    for entitie in dValleyGroves.entities:  
        start = Vector(entitie.dxf.start.x, entitie.dxf.start.y)
        end = Vector(entitie.dxf.end.x, entitie.dxf.end.y)
        groves.append(Line(start, end))


    # add text
    for entitie in dText.entities:
        x = entitie.dxf.insert.x
        y = entitie.dxf.insert.y
        a = entitie.dxf.rotation
        tx = entitie.dxf.text
        text.append(Text(x,y,a,tx))


    return cuts,groves,text
