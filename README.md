# Setup Verilator
## Packages Ubuntu 20.04 & WSL
```
sudo apt install git perl python3 make autoconf g++ flex bison ccache libgoogle-perftools-dev numactl perl-doc libfl2 libfl-dev zlibc zlib1g zlib1g-dev cmake ninja
```

## Build
```
export VERILATOR_ROOT="/your/path/to/verilator"
git clone https://github.com/verilator/verilator ${VERILATOR_ROOT}
cd ${VERILATOR_ROOT}
git checkout v4.218
autoconf
./configure
make
```

Verilator is now usable from `${VERILATOR_ROOT}`

# Build Project
```
export VERILATOR_ROOT="/your/path/to/verilator"
mkdir build
cd build
cmake -GNinja ..
ninja
```