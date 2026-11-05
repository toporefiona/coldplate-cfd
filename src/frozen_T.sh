#!/bin/bash
# Solve the temperature on a frozen, converged flow (one-way coupling).
# Run from ~/coldplate-cfd with OpenFOAM switched on:
#   bash src/frozen_T.sh <flow case> <new case name> [heat source in K/s]
set -e

flow=runs/$1
heat=runs/$2
source_rate=${3:-0.304}
latest=$(cd "$flow" && foamListTimes -latestTime | tail -1)

mkdir -p "$heat"
cp -r "$flow/constant" "$flow/system" "$heat/"
cp -r "$flow/$latest" "$heat/0"
cd "$heat"
rm -rf 0/uniform processor*
[ -f 0/T ] || cp "../$1/0/T" 0/T

cat > constant/fvOptions << EOF
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvOptions;
}

batteryHeat
{
    type            scalarSemiImplicitSource;
    selectionMode   cellZone;
    cellZone        channels;
    volumeMode      specific;
    injectionRateSuSp
    {
        T           ($source_rate 0);
    }
}
EOF

cat > constant/transportProperties << 'EOF'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}

transportModel  Newtonian;
nu              8.9e-07;
DT              [0 2 -1 0 0 0 0] 1.44e-7;
EOF

cat > system/controlDict << 'EOF'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}

application     scalarTransportFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         2000;
deltaT          1;
writeControl    timeStep;
writeInterval   2000;
writeFormat     ascii;
writePrecision  6;
timeFormat      general;
runTimeModifiable true;
EOF

foamDictionary system/fvSchemes -entry ddtSchemes/default -set steadyState > /dev/null
foamDictionary system/fvSolution -entry relaxationFactors -set "{ equations { T 0.7; } }" > /dev/null
foamDictionary system/fvSolution -entry solvers/T -set "{ solver PBiCGStab; preconditioner DILU; tolerance 1e-8; relTol 0; }" > /dev/null
sed -i "s/div(phi,T).*/div(phi,T)      bounded Gauss upwind;/" system/fvSchemes

scalarTransportFoam > log.scalarTransportFoam 2>&1
cp 0/U 0/p 0/phi 2000/

echo "Temperature solved on the flow from $flow (time $latest): $heat"
