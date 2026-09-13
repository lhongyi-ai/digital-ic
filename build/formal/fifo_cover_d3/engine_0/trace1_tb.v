`ifndef VERILATOR
module testbench;
  reg [4095:0] vcdfile;
  reg clock;
`else
module testbench(input clock, output reg genclock);
  initial genclock = 1;
`endif
  reg genclock = 1;
  reg [31:0] cycle = 0;
  wire [0:0] PI_clk = clock;
  fifo_harness UUT (
    .clk(PI_clk)
  );
`ifndef VERILATOR
  initial begin
    if ($value$plusargs("vcd=%s", vcdfile)) begin
      $dumpfile(vcdfile);
      $dumpvars(0, testbench);
    end
    #5 clock = 0;
    while (genclock) begin
      #5 clock = 0;
      #5 clock = 1;
    end
  end
`endif
  initial begin
`ifndef VERILATOR
    #1;
`endif
    // UUT.$auto$async2sync.\cc:116:execute$513  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$519  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$525  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$531  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$537  = 1'b1;
    UUT.accepted = 8'b00000000;
    UUT.dut.occupancy = 2'b00;
    UUT.dut.rd_ptr = 2'b00;
    UUT.dut.wr_ptr = 2'b00;
    UUT.past_valid = 1'b0;
    UUT.seen_exchange = 1'b0;
    UUT.seen_full = 1'b0;
    UUT.seen_reset_busy = 1'b0;
    UUT.dut.mem[2'b00] = 16'b0000000000000000;
    UUT.dut.mem[2'b01] = 16'b0000000000000000;

    // state 0
    UUT.in_valid = 1'b0;
    UUT.out_ready = 1'b0;
    UUT.rst = 1'b1;
    UUT.in_data = 16'b0000000000000000;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      UUT.in_valid <= 1'b1;
      UUT.out_ready <= 1'b0;
      UUT.rst <= 1'b0;
      UUT.in_data <= 16'b0000000000000000;
    end

    // state 2
    if (cycle == 1) begin
      UUT.in_valid <= 1'b1;
      UUT.out_ready <= 1'b0;
      UUT.rst <= 1'b0;
      UUT.in_data <= 16'b0000000000000000;
    end

    // state 3
    if (cycle == 2) begin
      UUT.in_valid <= 1'b1;
      UUT.out_ready <= 1'b0;
      UUT.rst <= 1'b0;
      UUT.in_data <= 16'b0000000000000000;
    end

    // state 4
    if (cycle == 3) begin
      UUT.in_valid <= 1'b1;
      UUT.out_ready <= 1'b1;
      UUT.rst <= 1'b0;
      UUT.in_data <= 16'b0000000000000000;
    end

    // state 5
    if (cycle == 4) begin
      UUT.in_valid <= 1'b0;
      UUT.out_ready <= 1'b0;
      UUT.rst <= 1'b0;
      UUT.in_data <= 16'b0000000000000000;
    end

    genclock <= cycle < 5;
    cycle <= cycle + 1;
  end
endmodule
