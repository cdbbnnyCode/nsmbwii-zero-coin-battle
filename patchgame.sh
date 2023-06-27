#!/bin/bash

set -euo pipefail
set -x

cd asm
./assemble main.s
cd ..

python patcher.py patch.json

cp d_basesNP.rel game/data/files/rels
