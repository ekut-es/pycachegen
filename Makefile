all: bin
	cd register_file && $(MAKE) all
	cp register_file/obj_dir/VRegisterFile_tb bin/
	cd memory_access_unit && $(MAKE) all
	cp memory_access_unit/obj_dir/VMemoryAccessUnit_tb bin/

bin:
	mkdir -p bin

test: all
	./bin/VRegisterFile_tb
	./bin/VMemoryAccessUnit_tb

.PHONY clean:
	-rm -rf bin
	cd register_file && $(MAKE) clean
