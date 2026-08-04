param J := 20;
param K := 6; #p
param M := 10;

set trabalhos := {1..J};
set lotes := {1..K};
set maquinas := {1..M};

param tamanhos{trabalhos} >= 0; #tamanhos
param tempos{trabalhos} >= 0; #pesos
param capacidade{maquinas} >= 0;

###Variaveis###
var x {j in trabalhos, k in lotes, m in maquinas} binary >= 0;  #=1 se o trabalho j for designado ao lote K e processado na máquina m
var P {k in lotes, m in maquinas} >= 0;  #tempo de execucao do lote k na maquina m
var C >= 0; #makespam
#
###Funcao objetivo###
        minimize mks: C;

###Restricoes###
#trabalho j designado ao lote K e processado na máquina m uma unica vez
        subject to un{j in trabalhos}: sum{k in lotes, m in maquinas} x[j,k,m]=1;

#respeitar a capacidade da maquina (S=4)
        subject to ca{k in lotes}: sum{j in trabalhos, m in maquinas} tamanhos[j]*x[j,k,m] <= 40;

#duracao para executr o lote k na mquina m
       subject to du{j in trabalhos, k in lotes, m in maquinas}: tempos[j]*x[j,k,m] - P[k,m] <= 0;

#makespam
       subject to ma{m in maquinas}: sum{k in lotes} P[k,m] - C <= 0;

#
data;

param tamanhos :=
1	2
2	4
3	2
4	3
5	4
6	2
7	3
8	2
9	2
10	4
11	4
12	2
13	3
14	4
15	3
16	2
17	3
18	2
19	2
20	3;

param tempos :=
 1	11
2	26
3	37
4	24
5	35
6	30
7	38
8	39
9	28
10	39
11	23
12	34
13	20
14	31
15	15
16	26
17	39
18	38
19	35
20	14;

param capacidade:=
M1	60
M2	60
M3	45
M4	45
M5	35
M6	35
M7	30
M8	25
M9	25
M10	25;

end;