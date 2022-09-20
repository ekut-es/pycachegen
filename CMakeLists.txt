cmake_minimum_required(VERSION 3.16)
project(acaverilog)

find_package(Git)

# download submodules if they aren't present
if(GIT_FOUND AND EXISTS "${PROJECT_SOURCE_DIR}/.git")
    # update submodules
    option(GIT_SUBMODULE "Check submodules during build" ON)
    if (GIT_SUBMODULE)
        message(STATUS "Submodule update")
        execute_process(COMMAND ${GIT_EXECUTABLE} submodule update --init --recursive
                WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
                RESULT_VARIABLE GIT_SUBMOD_RESULT)
        if (NOT GIT_SUBMOD_RESULT EQUAL "0")
            message(FATAL_ERROR "git submodule update --init --recursive failed with $GIT_SUBMOD_RESULT}, please check git log")
        endif()
    endif()
endif()

# Dummy output which is never actually produced. Anything that depends on this will always be rebuilt.
add_custom_command(
    OUTPUT always_rebuild
    COMMAND cmake -E echo
)

# Custom target will always cause its dependencies to be evaluated and is run by default
add_custom_target(dummy_target ALL
    DEPENDS verilator systemc
)

# Verilator
add_custom_target(verilator_autoconf
	COMMAND autoconf
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/verilator
)

add_custom_target(verilator_configure
	DEPENDS verilator_autoconf
	COMMAND ./configure
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/verilator
)

add_custom_target(verilator
	DEPENDS verilator_configure always_rebuild
	COMMAND make
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/verilator
)

# SystemC
set(ENV{SYSTEMC_HOME} ${CMAKE_CURRENT_LIST_DIR}/systemc-2.3.3)

add_custom_target(systemc_build_dir
	COMMAND mkdir -p build
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/systemc
)

add_custom_target(systemc_cmake
	DEPENDS systemc_build_dir
	COMMAND cmake -GNinja -DENABLE_PTHREADS=ON -DENABLE_PHASE_CALLBACKS_TRACING=OFF -DCMAKE_CXX_STANDARD=17 ..
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/systemc/build
)

add_custom_target(systemc_ninja
	DEPENDS systemc_cmake
	COMMAND ninja
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/systemc/build
)

add_custom_target(systemc
	DEPENDS systemc_ninja always_rebuild
	COMMAND ninja install
	WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/external/systemc/build
)
