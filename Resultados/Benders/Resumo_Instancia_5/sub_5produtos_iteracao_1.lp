\ SCIP STATISTICS
\   Problem name     : Sub
\   Variables        : 5 (4 binary, 0 integer, 0 implicit integer, 1 continuous)
\   Constraints      : 9
Minimize
 Obj: +1 Cmax
Subject to
 c1: +1 Y30,0 +1 Y30,1 +1 Y30,2 +1 Y30,3 = +1
 c2: +1 Cmax -45 Y30,0 >= +0
 c3: +1 Cmax -45 Y30,1 >= +0
 c4: +1 Cmax -45 Y30,2 >= +0
 c5: +1 Cmax -45 Y30,3 >= +0
 c6: +25.2 Y30,0 <= +30
 c7: +25.2 Y30,1 <= +25
 c8: +25.2 Y30,2 <= +20
 c9: +25.2 Y30,3 <= +50
Bounds
 0 <= Y30,0 <= 1
 0 <= Y30,1 <= 1
 0 <= Y30,2 <= 1
 0 <= Y30,3 <= 1
 45 <= Cmax
Binaries
 Y30,0 Y30,1 Y30,2 Y30,3
End
