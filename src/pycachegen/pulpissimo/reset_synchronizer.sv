module reset_synchronizer (
    input  logic clk_i,
    input  logic arst_ni,  // Active-low asynchronous reset
    output logic rst_o     // Active-high synchronous reset
);
    logic reset_ff1, reset_ff2;

    assign rst_o = reset_ff2;

    always_ff @(posedge clk_i or negedge arst_ni) begin
        if (!arst_ni)
            {reset_ff1, reset_ff2} <= 2'b11;
        else
            {reset_ff1, reset_ff2} <= {reset_ff2, 1'b0};
    end

endmodule
