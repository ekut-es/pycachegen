all: bin
	cd register_file && $(MAKE) all
	cp register_file/obj_dir/VRegisterFile_tb bin/

bin:
	mkdir -p bin

.PHONY clean:
	-rm -rf bin
	cd register_file && $(MAKE) clean
