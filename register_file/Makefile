all: VRegisterFile_tb

VRegisterFile_tb: obj_dir/VRegisterFile
	cp obj_dir/VRegisterFile obj_dir/VRegisterFile_tb

obj_dir/VRegisterFile: obj_dir
	make -j -C obj_dir -f VRegisterFile.mk VRegisterFile

obj_dir: RegisterFile.v RegisterFile_tb.cpp
	verilator -Wall --sc --exe RegisterFile_tb.cpp RegisterFile.v

.PHONY clean:
	-rm -rf obj_dir