\ SCIP STATISTICS
\   Problem name     : Problema do Transporte
\   Variables        : 6 (0 binary, 0 integer, 0 implicit integer, 6 continuous)
\   Constraints      : 5
Minimize
 Obj: +2.5 x_0_0 +1.7 x_0_1 +1.8 x_0_2 +2.5 x_1_0 +1.8 x_1_1 +1.4 x_1_2
Subject to
 cap. 0: +1 x_0_0 +1 x_0_1 +1 x_0_2 <= +350
 cap. 1: +1 x_1_0 +1 x_1_1 +1 x_1_2 <= +650
 dem. 0: +1 x_0_0 +1 x_1_0 >= +300
 dem. 1: +1 x_0_1 +1 x_1_1 >= +300
 dem. 2: +1 x_0_2 +1 x_1_2 >= +300
Bounds
End
