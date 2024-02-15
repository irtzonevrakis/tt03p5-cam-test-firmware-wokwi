# Use bash with a "sane" configuration:
# * Exit on failed status
# * Err on unset variables
# * Pipeline fails if one command in it has failed
SHELL := bash
.SHELLFLAGS := -euo pipefail

# Default compile rule
.PHONY: all
all: wokwi_chip

# Default clean rule
.PHONY: clean
clean:
	rm -rf dist

wokwi_chip: dist/ dist/wokwi.json dist/wokwi.wasm dist/wokwi_cxxrtl.h

dist/:
	mkdir dist

dist/wokwi.json: chip.json
	cp chip.json dist/wokwi.json

dist/wokwi.wasm: dist/wokwi_cxxrtl.h src/c++/main.cpp
	emcc -O3 --std=c++14 -I`yosys-config --datdir`/include -Idist \
		src/c++/main.cpp --no-entry -sERROR_ON_UNDEFINED_SYMBOLS=0 \
		-sINITIAL_MEMORY=128kb -sALLOW_MEMORY_GROWTH \
		-sTOTAL_STACK=64kb -o dist/wokwi.wasm

dist/wokwi_cxxrtl.h: src/verilog/top.v src/verilog/tt03p5-content-addressable-memory/src/array.v src/verilog/tt03p5-content-addressable-memory/src/top.v
	yosys -p "read_verilog $^; write_cxxrtl dist/wokwi_cxxrtl.h"
