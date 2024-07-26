#!/bin/bash

echo "Running testbenches..."

failed_testbenches=()
num_testbenches="0"

for filename in Vcache_wrapper_tb_*; do
    if [[ ! $filename ==  *.vcd ]] ; then
        let "num_testbenches++"
        eval "./$filename" > /dev/null 2>&1
        return_value=$?
        if [ $return_value -ne 0 ]; then
            failed_testbenches+=( ${filename} )
        fi
    fi
done

num_failed_testbenches=${#failed_testbenches[@]}

if [ ${num_failed_testbenches} -ne 0 ]; then
    echo "${num_failed_testbenches} out of ${num_testbenches} testbenches failed:"
    for failed_filename in ${failed_testbenches[@]}; do
        echo ${failed_filename}
    done
else
    echo "Ran ${num_testbenches} testbenches without errors"
fi
