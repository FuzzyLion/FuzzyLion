# The bear on the profile: three of Qi's pictures (awake, dozing, hibernating), each cut out and
# dithered by hw/bear_dither.sv. The status line in the README picks which one is shown.
#
#   make prep    resize and level bear/<state>.jpg into bear/<state>.pgm, and cut the bear out
#                into bear/<state>-mask.pgm (macOS only: sips and the Vision framework)
#   make         for every state: simulate the RTL in Verilator, check it bit for bit against
#                tools/golden.py, and render bear/<state>-light.png and -dark.png from the RTL's output
#   make status  refresh the status line and the picture in README.md from the last public push

PY     ?= python3
STATES := awake dozing hibernating
SIZE   := 160
LEVELS := --black 22 --white 140 --gamma 1.0

# Vision drops the mug and the dark sweater front in the awake picture, so its lower rows are filled
# in by hand (see tools/mask.swift). It finds the whole bear in the other two.
FILL_awake := 0.62

all: $(STATES:%=render-%)
prep: $(STATES:%=prep-%)
check: $(STATES:%=check-%)

prep-%:
	mkdir -p build
	sips -z $(SIZE) $(SIZE) -s format bmp bear/$*.jpg --out build/$*.bmp >/dev/null
	$(PY) tools/prep.py build/$*.bmp bear/$*.pgm $(LEVELS)
	swift tools/mask.swift bear/$*.jpg bear/$*-mask.pgm $(SIZE) $(FILL_$*)

build/Vtb: hw/bear_dither.sv hw/tb_bear_dither.sv
	mkdir -p build
	verilator --binary -Wall --top-module tb_bear_dither -Mdir build/obj -o ../Vtb \
	  hw/tb_bear_dither.sv hw/bear_dither.sv

build/%_rtl.pbm: build/Vtb bear/%.pgm bear/%-mask.pgm
	build/Vtb +in=bear/$*.pgm +mask=bear/$*-mask.pgm +out=$@

check-%: build/%_rtl.pbm
	$(PY) tools/golden.py bear/$*.pgm build/$*_golden.pbm --mask bear/$*-mask.pgm --compare $<

render-%: check-%
	$(PY) tools/render.py build/$*_rtl.pbm bear/$*-light.png bear/$*-dark.png \
	  --mask bear/$*-mask.pgm --outline light --scale 4

status:
	$(PY) tools/bear_status.py README.md

clean:
	rm -rf build

.PHONY: all prep check status clean
