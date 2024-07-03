/******************************************************************************
* Copyright (C) 2023 Advanced Micro Devices, Inc. All Rights Reserved.
* SPDX-License-Identifier: MIT
******************************************************************************/
/*
 * helloworld.c: simple test application
 *
 * This application configures UART 16550 to baud rate 9600.
 * PS7 UART (Zynq) is not initialized by this application, since
 * bootrom/bsp configures it to baud rate 115200
 *
 * ------------------------------------------------
 * | UART TYPE   BAUD RATE                        |
 * ------------------------------------------------
 *   uartns550   9600
 *   uartlite    Configurable only in HW design
 *   ps7_uart    115200 (configured by bootrom/bsp)
 */

#include <stdio.h>
#include "platform.h"
#include "xil_printf.h"
#include "xparameters.h"
#include "xbasic_types.h"

const int trace_timeout = 100000;
const int cache_read_timeout = 100;
const int address_width = 8;
const int trace_data_width = 32;
//const int data_width = 16;

// Functions for creating read/write instructions for the trace
int write(int address, int write_data) {
	return (1 << (trace_data_width  -1)) | (write_data << address_width) | address;
}

int read(int address) {
	return address;
}


int main()
{
	volatile Xuint32* cache_baseaddr_p = (Xuint32*) XPAR_AXI_SLAVE_BRAM_CACHE_0_S00_AXI_BASEADDR;
	volatile Xuint32* stats_bram_baseaddr_p = (Xuint32*) XPAR_BRAM_0_BASEADDR;
	volatile Xuint32* trace_bram_baseaddr_p = (Xuint32*) XPAR_BRAM_1_BASEADDR;

	volatile Xuint32* cache_flush_sel_wval_addrval = cache_baseaddr_p;
	volatile Xuint32* cache_address = cache_baseaddr_p + 1;
	volatile Xuint32* cache_write_data = cache_baseaddr_p + 2;
	volatile Xuint32* cache_trace_length = cache_baseaddr_p + 3;
	volatile Xuint32* cache_hit_rdval_wdone_pready = cache_baseaddr_p + 5;
	volatile Xuint32* cache_read_data = cache_baseaddr_p + 6;
	volatile Xuint32* cache_trace_done = cache_baseaddr_p + 7;

	int mem_trace[] = {
			write(0, 0x1111), // miss
			write(1, 0x2222), // miss
			write(2, 0xdead), // miss
			write(3, 0xbeef), // miss
			read(0), // miss
			write(0, 0x1001), // hit
			read(0), // hit
			read(1), // miss
			read(2), // miss
			read(3), // miss
			read(3), // hit
			write(4, 0x4444), // miss
			read(4), // miss
			read(0) // miss
	};
	int expected_execution_time = 11 * 8 + 3 * 6 + 6 * 16 + 6 * 11;
	int trace_length = sizeof(mem_trace) / sizeof(mem_trace[0]);

    init_platform();

    xil_printf("Writing the trace to the BRAM...\n\r");
    for (int i = 0; i < trace_length; i++) {
    	*(trace_bram_baseaddr_p + i) = mem_trace[i];
    }
    xil_printf("Reading the trace from the BRAM...\n\r");
    for (int i = 0; i < trace_length; i++) {
    	xil_printf("Trace at address 0x%x: 0x%x\n\r", i, *(trace_bram_baseaddr_p + i));
    }

    xil_printf("Starting trace processing.\n\r");
    *cache_trace_length = trace_length; // no idea why * 4 is needed here

    for (int i = 0; i < trace_timeout; i++) {
    	if (*cache_trace_done == 1) {
    		xil_printf("Trace processed (iteration %d)\n\r", i);
    		break;
    	}
    	if (i == trace_timeout - 1) {
    		xil_printf("Timeout - the cache has not yet finished processing the trace.\n\r");
    	}
    }

    xil_printf("Reading from cache...\n\r");
    for (int i = 0; i < trace_length; i++){
    	*cache_address = i;
    	*cache_flush_sel_wval_addrval = 0b0001;
    	*cache_flush_sel_wval_addrval = 0b0000;

    	xil_printf("Reading from address 0x%x... ", i);

    	for(int j = 0; j < cache_read_timeout; j++){
    		if((*cache_hit_rdval_wdone_pready & 0b0101) == 0b0101) {
    			xil_printf("0x%x\n\r", *cache_read_data);
    			break;
    		}
    		if (j == 99){
    			xil_printf("Timeout - the cache has not yet processed the read request.\n\r");
    		}
    	}
    }

    int execution_time = *stats_bram_baseaddr_p;
	xil_printf("Trace execution has finished. Total execution time: %d cycles ", execution_time);

	if (execution_time == expected_execution_time) {
		xil_printf("(SUCCESS)\n\r");
	} else {
		xil_printf("(ERROR - expected %d)\n\r", expected_execution_time);
	}

    cleanup_platform();
    return 0;
}
