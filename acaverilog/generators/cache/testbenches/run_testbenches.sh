#!/bin/bash

failed_testbenches=()

for filename in Vcache_wrapper_tb_*; do
    if [[ ! $filename ==  *.vcd ]] ; then
        # echo $filename
        eval "./$filename" > /dev/null 2>&1
        return_value=$?
        if [ $return_value -ne 0 ]; then
            failed_testbenches+=( ${filename} )
        fi
    fi
done

if [ ${#failed_testbenches[@]} -ne 0 ]; then
    echo "Some testbenches failed:"
    for failed_filename in ${failed_testbenches[@]}; do
        echo ${failed_filename}
    done
else
    echo "All testbenches finished without errors"
fi
