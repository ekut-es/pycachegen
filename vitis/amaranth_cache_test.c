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

#define WAIT_UNTIL_READY while((*axi_slave_hit_rdvalid_pready & 1) == 0)

#include <stdio.h>
#include "platform.h"
#include "xil_printf.h"
#include "xparameters.h"
#include "xbasic_types.h"


int main()
{
    init_platform();

    volatile Xuint32* axi_slave_base_addr_p = (Xuint32*) XPAR_CACHE_WRAPPER_0_S00_AXI_BASEADDR;

    volatile Xuint32* axi_slave_wstrobe_flush_reqvalid = axi_slave_base_addr_p;
    volatile Xuint32* axi_slave_address = axi_slave_base_addr_p + 1;
    volatile Xuint32* axi_slave_wdata = axi_slave_base_addr_p + 2;
    volatile Xuint32* axi_slave_hit_rdvalid_pready = axi_slave_base_addr_p + 5;
    volatile Xuint32* axi_slave_rdata = axi_slave_base_addr_p + 6;

    WAIT_UNTIL_READY;
    xil_printf("\n\rWrite to address 2\n\r");
    *axi_slave_address = 2;
    *axi_slave_wdata = 0x12345678;
    *axi_slave_wstrobe_flush_reqvalid = 0b111101;
    xil_printf("hit/rdvalid/pready: 0x%x\n\r\n", *axi_slave_hit_rdvalid_pready);

    WAIT_UNTIL_READY;
    xil_printf("Read from address 2\n\r");
    *axi_slave_address = 2;
    *axi_slave_wstrobe_flush_reqvalid = 0b000001;
    xil_printf("hit/rdvalid/pready: 0x%x\n\r", *axi_slave_hit_rdvalid_pready);
    xil_printf("rdata: 0x%x\n\r\n", *axi_slave_rdata);

    WAIT_UNTIL_READY;
    xil_printf("Read from address 2\n\r");
    *axi_slave_address = 2;
    *axi_slave_wstrobe_flush_reqvalid = 0b000001;
    xil_printf("hit/rdvalid/pready: 0x%x\n\r", *axi_slave_hit_rdvalid_pready);
    xil_printf("rdata: 0x%x\n\r\n", *axi_slave_rdata);

    WAIT_UNTIL_READY;
    xil_printf("Write to address 2\n\r");
    *axi_slave_address = 2;
    *axi_slave_wdata = 0x22;
    *axi_slave_wstrobe_flush_reqvalid = 0b000101;
    xil_printf("hit/rdvalid/pready: 0x%x\n\r\n", *axi_slave_hit_rdvalid_pready);

    WAIT_UNTIL_READY;
    xil_printf("Read from address 2\n\r");
    *axi_slave_address = 2;
    *axi_slave_wstrobe_flush_reqvalid = 0b000001;
    xil_printf("hit/rdvalid/pready: 0x%x\n\r", *axi_slave_hit_rdvalid_pready);
    xil_printf("rdata: 0x%x\n\r\n", *axi_slave_rdata);

    cleanup_platform();
    return 0;
}
