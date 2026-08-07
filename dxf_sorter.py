#!/usr/bin/env python3
import ezdxf
import math
import sys

def distance(p1, p2):
    """Berechnet den euklidischen Abstand zwischen zwei Punkten (x, y)."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def load_paths_from_dxf(filename):
    """
    Liest Pfade (in diesem Fall LINE-Entitäten) aus einer DXF-Datei
    und speichert sie als Dictionary mit Start- und Endpunkt.
    """
    try:
        doc = ezdxf.readfile(filename)
    except IOError:
        print(f"Fehler: Die Datei {filename} konnte nicht geöffnet werden.")
        sys.exit(1)
    except ezdxf.DXFStructureError:
        print(f"Fehler: Ungültige oder beschädigte DXF-Datei: {filename}")
        sys.exit(1)

    msp = doc.modelspace()
    paths = []

    for entity in msp:
        if entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            paths.append({'start': (start[0], start[1]), 'end': (end[0], end[1])})
        # Hier können weitere Entitätstypen (z. B. LWPOLYLINE) ergänzt werden.
    return paths

def chain_paths(paths):
    """
    Sortiert die Pfade so, dass der jeweils nächste (am nächsten liegende) Pfad
    an die Kette angehängt wird. Falls der näheste Punkt am Ende eines Pfades liegt,
    werden Start und Endpunkt vertauscht.
    """
    if not paths:
        return []

    # Beginne mit dem ersten Pfad in der Liste.
    current_path = paths.pop(0)
    chained = [current_path]
    current_point = current_path['end']

    while paths:
        min_dist = None
        min_index = None
        flip = False  # Gibt an, ob der Pfad umgedreht werden muss

        # Suche den Pfad, dessen Start- oder Endpunkt am nächsten zum aktuellen Punkt liegt.
        for i, path in enumerate(paths):
            dist_start = distance(current_point, path['start'])
            dist_end = distance(current_point, path['end'])

            if min_dist is None or dist_start < min_dist:
                min_dist = dist_start
                min_index = i
                flip = False
            if dist_end < min_dist:
                min_dist = dist_end
                min_index = i
                flip = True

        # Hole den nächsten Pfad und entferne ihn aus der Liste.
        next_path = paths.pop(min_index)
        if flip:
            # Falls der näheste Punkt der Endpunkt ist, tausche Start und End.
            next_path = {'start': next_path['end'], 'end': next_path['start']}
        chained.append(next_path)
        current_point = next_path['end']

    return chained

def create_new_dxf(sorted_paths, output_filename):
    """
    Erzeugt eine neue DXF-Datei und schreibt die sortierten Pfade (als LINE-Entitäten)
    in den Modelspace.
    """
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    for path in sorted_paths:
        msp.add_line(path['start'], path['end'])
    
    try:
        doc.saveas(output_filename)
        print(f"Neue DXF-Datei '{output_filename}' wurde erstellt.")
    except Exception as e:
        print("Fehler beim Speichern der neuen DXF-Datei:", e)

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_dxf> [output_dxf]")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else "sorted.dxf"
    
    paths = load_paths_from_dxf(input_filename)

    if not paths:
        print("Keine Pfade in der DXF-Datei gefunden.")
        sys.exit(0)

    sorted_paths = chain_paths(paths)
    
    # Ausgabe der sortierten Pfade
    print("Sortierte Pfade (Kette):")
    for i, path in enumerate(sorted_paths):
        print(f"Pfad {i+1}: Start {path['start']}, End {path['end']}")
    
    # Erzeuge die neue DXF-Datei mit den sortierten Pfaden
    create_new_dxf(sorted_paths, output_filename)

if __name__ == "__main__":
    main()
