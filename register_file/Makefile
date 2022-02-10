TESTBENCH = obj_dir/VRegisterFile_tb
TARGET = $(subst _tb,, $(TESTBENCH))
CPP_FILES = RegisterFile_tb.cpp
VERILOG_FILES = RegisterFile.v

all: $(TESTBENCH)

$(TESTBENCH): $(TARGET)
	cp $< $@

$(TARGET): obj_dir
	$(MAKE) -j -C obj_dir -f VRegisterFile.mk VRegisterFile

obj_dir: $(CPP_FILES) $(VERILOG_FILE) 
	verilator -Wall --sc --exe $(CPP_FILES) $(VERILOG_FILES)

.PHONY clean:
	-rm -rf obj_dir