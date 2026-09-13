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
  quant_serial_harness UUT (
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
    // UUT.$auto$async2sync.\cc:107:execute$851  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$857  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$863  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$869  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$899  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$855  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$861  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$867  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$873  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$879  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$885  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$891  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$897  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$903  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$909  = 1'b1;
    UUT._witness_.anyinit_procdff_842 = 1'b0;
    UUT.age = 7'b0000000;
    UUT.dut.dbg_index = 16'b0000000000000000;
    UUT.dut.dbg_kind = 4'b0000;
    UUT.dut.dbg_valid = 1'b0;
    UUT.dut.dbg_value = 40'b0000000000000000000000000000000000000000;
    UUT.dut.feature_index = 4'b0000;
    UUT.dut.power_sum = 33'b000000000000000000000000000000000;
    UUT.dut.quant_guard = 1'b0;
    UUT.dut.quant_remaining = 8'b00000000;
    UUT.dut.quant_work = 33'b000000000000000000000000000000000;
    UUT.dut.state = 5'b00000;
    UUT.past_valid = 1'b0;
    UUT.pending = 1'b0;
    UUT.in_power = 33'b000000000000000000000000001111101;
    UUT.in_shift = 8'b00000001;
    UUT.in_index = 4'b0011;
    UUT.dut.feature_shifts[4'b0000] = 8'b00000000;
    UUT.dut.feature_shifts[4'b0011] = 8'b00000001;
    UUT.dut.feature_shifts[4'b0100] = 8'b00000000;
    UUT.dut.features[4'b0000] = 8'b00111111;
    UUT.dut.features[4'b0011] = 8'b00111111;

    // state 0
    UUT.rst = 1'b1;
    UUT.start = 1'b0;
  end
  always @(posedge clock) begin
    // state 1
    if (cycle == 0) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 2
    if (cycle == 1) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 3
    if (cycle == 2) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 4
    if (cycle == 3) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 5
    if (cycle == 4) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 6
    if (cycle == 5) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    genclock <= cycle < 6;
    cycle <= cycle + 1;
  end
endmodule
