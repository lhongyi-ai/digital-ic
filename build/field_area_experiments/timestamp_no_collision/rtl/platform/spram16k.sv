// Isolate the iCE40-specific 16K x 16 single-port RAM primitive.
// Behavioral model has the same one-clock read latency; no reset of RAM data.
module spram16k(input wire clk, input wire [13:0] address,
    input wire write_enable, input wire [15:0] write_data,
    output wire [15:0] read_data);
`ifdef ICE40
    SB_SPRAM256KA ram(.ADDRESS(address), .DATAIN(write_data), .MASKWREN(4'b1111),
        .WREN(write_enable), .CHIPSELECT(1'b1), .CLOCK(clk), .STANDBY(1'b0),
        .SLEEP(1'b0), .POWEROFF(1'b1), .DATAOUT(read_data));
`else
    reg [15:0] memory [0:16383];
    reg [15:0] q;
    always @(posedge clk) begin
        if (write_enable) memory[address] <= write_data;
        q <= memory[address];
    end
    assign read_data = q;
`endif
endmodule
