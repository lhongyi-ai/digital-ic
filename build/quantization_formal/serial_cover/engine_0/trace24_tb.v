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
    // UUT.$auto$async2sync.\cc:107:execute$1093  = 1'b0;
    // UUT.$auto$async2sync.\cc:107:execute$919  = 1'b0;
    // UUT.$auto$async2sync.\cc:116:execute$1001  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1007  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1013  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1019  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1025  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1031  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1037  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1043  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1049  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1055  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1061  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1067  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1073  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1079  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1085  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1091  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1097  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1103  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1109  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1115  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1121  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1127  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1133  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1139  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1145  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1151  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1157  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1163  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1169  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1175  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1181  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$1187  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$923  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$929  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$935  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$941  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$947  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$953  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$959  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$965  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$971  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$977  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$983  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$989  = 1'b1;
    // UUT.$auto$async2sync.\cc:116:execute$995  = 1'b1;
    UUT.dut.dbg_index = 16'b0000000000000000;
    UUT.dut.dbg_kind = 4'b0000;
    UUT.dut.dbg_valid = 1'b0;
    UUT.dut.dbg_value = 40'b0000000000000000000000000000000000000000;
    UUT.dut.feature_index = 4'b0000;
    UUT.dut.power_sum = 33'b000000000000000000000000000000000;
    UUT.dut.quant_guard = 1'b0;
    UUT.dut.quant_remaining = 8'b00000000;
    UUT.dut.quant_sticky = 1'b0;
    UUT.dut.quant_work = 33'b000000000000000000000000000000000;
    UUT.dut.state = 5'b00000;
    UUT.past_valid = 1'b0;
    UUT.pending = 1'b0;
    UUT.saw_abort = 1'b0;
    UUT.in_index = 4'b0001;
    UUT.in_power = 33'b000000000000000000000000000000000;
    UUT.in_shift = 8'b00010001;
    UUT.dut.feature_shifts[4'b0000] = 8'b00000000;
    UUT.dut.feature_shifts[4'b0001] = 8'b00010001;
    UUT.dut.feature_shifts[4'b0010] = 8'b00000000;
    UUT.dut.features[4'b0000] = 8'b00000000;
    UUT.dut.features[4'b0001] = 8'b00000000;

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
      UUT.start <= 1'b1;
    end

    // state 7
    if (cycle == 6) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 8
    if (cycle == 7) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    // state 9
    if (cycle == 8) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    // state 10
    if (cycle == 9) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 11
    if (cycle == 10) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 12
    if (cycle == 11) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 13
    if (cycle == 12) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 14
    if (cycle == 13) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    // state 15
    if (cycle == 14) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 16
    if (cycle == 15) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    // state 17
    if (cycle == 16) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 18
    if (cycle == 17) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    // state 19
    if (cycle == 18) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 20
    if (cycle == 19) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b1;
    end

    // state 21
    if (cycle == 20) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    // state 22
    if (cycle == 21) begin
      UUT.rst <= 1'b0;
      UUT.start <= 1'b0;
    end

    genclock <= cycle < 22;
    cycle <= cycle + 1;
  end
endmodule
