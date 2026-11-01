#!/bin/bash
# Turn a gmsh mesh into a ready-to-run OpenFOAM case, built from case_template.
# Run from ~/coldplate-cfd with OpenFOAM switched on:
#   bash src/make_case.sh <mesh file> <case name>
set -e #makes the script stop at the first error

mesh=$(realpath "$1") #takes the first word you type (the mesh file), and realpath turns it into its full path, so it can still be found after the script changes folder. $1 means the first word after the script name
case_dir=runs/$2 #builds the case folder name from the second word you type

mkdir -p "$case_dir"
cp -r case_template/* "$case_dir"/
cd "$case_dir"

gmshToFoam "$mesh" > log.gmshToFoam #converts the mesh
foamDictionary constant/polyMesh/boundary -entry entry0/frontAndBack/type -set empty > /dev/null
foamDictionary constant/polyMesh/boundary -entry entry0/walls/type -set wall > /dev/null
foamDictionary constant/polyMesh/boundary -entry entry0/heated_walls/type -set wall > /dev/null
foamDictionary system/controlDict -entry endTime -set 3000 > /dev/null #alloes up to 3000 iterations
foamDictionary system/controlDict -entry writeInterval -set 500 > /dev/null #saves results every 500 iterations
foamDictionary system/controlDict -entry functions/temperature/writeControl -set writeTime > /dev/null #makes T save only with the other results, /dev/null is Linux's bin
topoSet > log.topoSet #makes the channel's zone for the heat source
checkMesh > log.checkMesh

grep -E "cells:|Mesh OK|Failed" log.checkMesh
echo "Case ready: $case_dir"
