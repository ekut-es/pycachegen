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
#include "test_trace_32_16.h"

const int trace_data_width = 32;


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

	unsigned char trace_data[] = test_trace_32_16_bin;
	unsigned int trace_len = test_trace_32_16_bin_len;
	unsigned int trace_bytes_per_word = (trace_data_width / 8);

    init_platform();

    xil_printf("Writing the trace to the BRAM...\n\r");
	for(int i = 0; i < trace_len; i += trace_bytes_per_word){
		unsigned int word = 0;
		for(int j = 0; j < trace_bytes_per_word; j++){
			word |= (trace_data[i+j] << (trace_data_width - (j + 1) * 8));
		}
    	*(trace_bram_baseaddr_p + i) = word;
	}

    xil_printf("Reading the trace start from the BRAM...\n\r");
    for (int i = 0; i < 10; i++) {
    	xil_printf("Trace at address 0x%x: 0x%x\n\r", i, *(trace_bram_baseaddr_p + i));
    }

    xil_printf("Starting trace processing.\n\r");
    *cache_trace_length = trace_len;

    while(true){
    	if(*cache_trace_done == 1) {
    		break;
    	}
    }

    int execution_time = *stats_bram_baseaddr_p;
    xil_printf("Trace processed. Total execution time: %d cycles.\n\r", execution_time);

    xil_printf("Reading from cache...\n\r");
    for (int i = 0; i < 10; i++){
    	*cache_address = i;
    	*cache_flush_sel_wval_addrval = 0b0001;
    	*cache_flush_sel_wval_addrval = 0b0000;

    	xil_printf("Reading from address 0x%x... ", i);

    	while(true){
    		if((*cache_hit_rdval_wdone_pready & 0b0101) == 0b0101) {
    			xil_printf("0x%x\n\r", *cache_read_data);
    			break;
    		}
    	}
    }

    cleanup_platform();
    return 0;
}
