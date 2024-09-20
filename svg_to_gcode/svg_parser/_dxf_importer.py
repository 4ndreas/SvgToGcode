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
    if len(dText.entities) == 0:
        dText = msp.query("TEXT").layer == "Edge_ID"

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

def splitPolyLine(entitie):
    lines  = []
    a = entitie.explode()
    for entitie in a.entities:  
        if entitie.DXFTYPE == 'LINE':
            lines.extend(getLine(entitie))
    # lines  = []
    # start = Vector(entitie.dxf.start.x, entitie.dxf.start.y)
    # end = Vector(entitie.dxf.end.x, entitie.dxf.end.y)
    # lines.append(Line(start, end))    
    # # if hasattr(entitie.dxf, '_entity'):
    # #     lines.extend(getLine(entitie.dxf._entity))
    return lines

def getLine(entitie):
    lines  = []
    start = Vector(entitie.dxf.start.x, entitie.dxf.start.y)
    end = Vector(entitie.dxf.end.x, entitie.dxf.end.y)
    lines.append(Line(start, end))    
    # if hasattr(entitie.dxf, '_entity'):
    #     lines.extend(getLine(entitie.dxf._entity))
    return lines

def importAllDXF(file_path: str )-> (List[Curve]):
    canvas_height = 1500

    lines  = []

    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    dAll = msp.query() # gets all entries 
    dLines = msp.query("LINE")

    # add lines
    for entitie in dAll.entities:  
        if entitie.DXFTYPE == 'POLYLINE':
            lines.extend(splitPolyLine(entitie))
        if entitie.DXFTYPE == 'LINE':
            lines.extend(getLine(entitie))
        # start = Vector(entitie.dxf.start.x, entitie.dxf.start.y)
        # end = Vector(entitie.dxf.end.x, entitie.dxf.end.y)
        # lines.append(Line(start, end))
        
                    

    return lines