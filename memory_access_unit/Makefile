TESTBENCH = obj_dir/VMemoryAccessUnit_tb
TARGET = $(subst _tb,, $(TESTBENCH))
CPP_FILES = MemoryAccessUnit_tb.cpp
VERILOG_FILES = MemoryAccessUnit.v

all: $(TESTBENCH)

$(TESTBENCH): $(TARGET)
	cp $< $@

$(TARGET): obj_dir FORCE
	$(MAKE) -j -C obj_dir -f VMemoryAccessUnit.mk VMemoryAccessUnit

obj_dir: $(CPP_FILES) $(VERILOG_FILE) FORCE
	verilator --trace --sc --exe -Mdir $@ $(CPP_FILES) $(VERILOG_FILES)

FORCE: ;

.PHONY clean:
	-rm -rf obj_dir