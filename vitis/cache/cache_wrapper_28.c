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

int main()
{
    init_platform();

    volatile Xuint32* axi_slave_base_addr_p = (Xuint32*) XPAR_CACHE_WRAPPER_1_0_S00_AXI_BASEADDR;

    volatile Xuint32* axi_slave_flush_sel_wval_addrval = axi_slave_base_addr_p;
    volatile Xuint32* axi_slave_address = axi_slave_base_addr_p + 1;
    volatile Xuint32* axi_slave_write_data = axi_slave_base_addr_p + 2;
    volatile Xuint32* axi_slave_fdone_hit_rdval_wdone_pready = axi_slave_base_addr_p + 5;
    volatile Xuint32* axi_slave_read_data = axi_slave_base_addr_p + 6;

    xil_printf("Writing and reading from an existing address\n\r");
    *axi_slave_address = 42;
    *axi_slave_write_data = 4242;
    *axi_slave_flush_sel_wval_addrval = 0b0111;
    *axi_slave_flush_sel_wval_addrval = 0b0000;
    xil_printf("f_done/hit/rd_valid/w_done/p_ready: 0x%x\n\r", *axi_slave_fdone_hit_rdval_wdone_pready);
    *axi_slave_address = 42;
    *axi_slave_flush_sel_wval_addrval = 0b0001;
    *axi_slave_flush_sel_wval_addrval = 0b0000;
    xil_printf("Read data: %d\n\r", *axi_slave_read_data);
    xil_printf("f_done/hit/rd_valid/w_done/p_ready: 0x%x\n\r", *axi_slave_fdone_hit_rdval_wdone_pready);
    *axi_slave_address = 48;
    *axi_slave_write_data = 4848;
    *axi_slave_flush_sel_wval_addrval = 0b0111;
    *axi_slave_flush_sel_wval_addrval = 0b0000;
    xil_printf("f_done/hit/rd_valid/w_done/p_ready: 0x%x\n\r", *axi_slave_fdone_hit_rdval_wdone_pready);
    *axi_slave_address = 48;
    *axi_slave_flush_sel_wval_addrval = 0b0001;
    *axi_slave_flush_sel_wval_addrval = 0b0000;
    xil_printf("Read data: %d\n\r", *axi_slave_read_data);
    xil_printf("f_done/hit/rd_valid/w_done/p_ready: 0x%x\n\r", *axi_slave_fdone_hit_rdval_wdone_pready);

    print("Successfully ran Hello World application");
    cleanup_platform();
    return 0;
}
