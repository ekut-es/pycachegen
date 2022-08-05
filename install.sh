#!/bin/bash
git submodule update --init --recursive
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# compile systemc
export SYSTEMC_HOME=${SCRIPT_DIR}/systemc-2.3.3
pushd external/systemc
mkdir build
pushd build
cmake -GNinja -DENABLE_PTHREADS=ON -DCMAKE_CXX_STANDARD=17 -DENABLE_PHASE_CALLBACKS_TRACING=OFF ..
ninja
ninja install
popd
popd

# compile verilator
export VERILATOR_ROOT=${SCRIPT_DIR}/verilator
pushd external/verilator
autoconf
./configure
make -j4
