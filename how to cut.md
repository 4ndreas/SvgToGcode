#how to cut

G28
G92 X-200 Y-100 ; set offset 

M8; turn Vacuum on


offset zwischen den achsen 78mm in x (offset für tool1 ist dann -78)

bei dem 120 mm stück ist die messer achse 4mm vom rand weg

-> offset zum falzrad ist 4mm + 78mm 

am besten macht man negative Y koordinaten dann kann man den 0 punkt ganz vorne machen


single cut
´´´
G28 Z W
G92 Z58 W59
G28 A B
G28 X
G1 B0
G1 W0
G1 X1280 F5000
G1 W20
G1 X0 F15000
´´´