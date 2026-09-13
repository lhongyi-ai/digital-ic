// Independent mathematical specification and assertions for extracted RTL.
// This is not a reference made by copying the production rounding functions.
module quant_functions_harness #(parameter integer HIDDEN_SHIFT=8) (input wire clk);
    (* anyseq *) reg signed [39:0] value;
    (* anyseq *) reg [5:0] shift;
    wire signed [39:0] rounded;
    wire signed [15:0] clipped12, clipped16;
    wire [7:0] hidden_quantized;
    quant_functions_kernel #(.HIDDEN_SHIFT(HIDDEN_SHIFT)) dut(.*);

    // Sign-magnitude formulation. Production uses arithmetic floor shifts and
    // two's-complement remainder bits. The extra bit handles -2^39 exactly.
    function automatic signed [41:0] nearest;
        input signed [39:0] x;
        input [5:0] s;
        reg signed [40:0] extended;
        reg [40:0] magnitude, whole, residue;
        reg [41:0] twice_residue, unit_step, rounded_magnitude;
        begin
            extended = {x[39],x};
            magnitude = x[39] ? -extended : extended;
            whole = magnitude >> s;
            residue = magnitude - (whole << s);
            twice_residue = {1'b0,residue} << 1;
            unit_step = 42'd1 << s;
            rounded_magnitude = {1'b0,whole} +
                ((twice_residue > unit_step ||
                  (twice_residue == unit_step && whole[0])) ? 42'd1 : 42'd0);
            nearest = x[39] ? -$signed(rounded_magnitude) : $signed(rounded_magnitude);
        end
    endfunction
    wire signed [41:0] expected = nearest(value,shift);
    wire signed [41:0] hidden_rounded = nearest(value,6'(HIDDEN_SHIFT));
    always @* begin
        assume(shift <= 39);
        assert($signed({{2{rounded[39]}},rounded}) == expected);
        if (value > 2047) assert(clipped12 == 2047);
        else if (value < -2048) assert(clipped12 == -2048);
        else assert($signed(clipped12) == value);
        assert(clipped12 >= -2048 && clipped12 <= 2047);
        if (value > 32767) assert(clipped16 == 32767);
        else if (value < -32768) assert(clipped16 == -32768);
        else assert($signed(clipped16) == value);
        if (hidden_rounded <= 0) assert(hidden_quantized == 0);
        else if (hidden_rounded >= 127) assert(hidden_quantized == 127);
        else assert(hidden_quantized == hidden_rounded);
        assert(hidden_quantized <= 127);

        cover(value == 10 && shift == 2 && rounded == 2); // F01 positive tie, even stays
        cover(value == 6 && shift == 2 && rounded == 2); // F02 positive tie, odd increments
        cover(value == -10 && shift == 2 && rounded == -2); // F03 negative tie, even stays
        cover(value == -6 && shift == 2 && rounded == -2); // F04 negative tie, odd increments
        cover(value == -40'sh8000000000 && shift == 0 && rounded == value); // F05 INT40_MIN identity
        cover(value == 40'sh7fffffffff && shift == 39 && rounded == 1); // F06 high shift
        cover(value == 2048 && clipped12 == 2047); // F07 sat12 upper overflow
        cover(value == -2049 && clipped12 == -2048); // F08 sat12 lower overflow
        cover(value == 32768 && clipped16 == 32767); // F09 sat16 upper overflow
        cover(value == -32769 && clipped16 == -32768); // F10 sat16 lower overflow
        cover(value == 0 && hidden_quantized == 0); // F11 ReLU zero
        cover(value == (40'sd3 << HIDDEN_SHIFT) && hidden_quantized == 3); // F12 hidden interior
        cover(value == (40'sd128 << HIDDEN_SHIFT) && hidden_quantized == 127); // F13 hidden saturation
    end
endmodule

module quant_serial_harness(input wire clk);
    // One arbitrary operand/configuration tuple per formal trace. The whole
    // 33-bit power / 8-bit shift / 4-bit index spaces are quantified, not sampled.
    (* anyconst *) reg [32:0] in_power;
    (* anyconst *) reg [7:0] in_shift;
    (* anyconst *) reg [3:0] in_index;
    (* anyseq *) reg rst, start;
    wire ready, out_valid, shifting;
    wire [7:0] out_value, stored_value;
    wire [3:0] out_index, out_kind;
    quant_serial_kernel dut(.*);

    function automatic [7:0] expected_quantized;
        input [32:0] power;
        input [7:0] shift;
        reg [33:0] whole, residue, double_residue, unit_step, nearest;
        begin
            if (shift > 33) expected_quantized = 0;
            else begin
                whole = {1'b0,power} >> shift;
                residue = {1'b0,power} - (whole << shift);
                double_residue = residue << 1;
                unit_step = 34'd1 << shift;
                nearest = whole + ((double_residue > unit_step ||
                            (double_residue == unit_step && whole[0])) ? 34'd1 : 34'd0);
                expected_quantized = nearest > 127 ? 8'd127 : nearest[7:0];
            end
        end
    endfunction
    wire [7:0] expected = expected_quantized(in_power,in_shift);
    wire [7:0] latency = in_shift > 0 && in_shift <= 33 ? in_shift + 8'd2 : 8'd2;
    reg past_valid=0, pending=0, saw_abort=0;
    reg [6:0] age=0;
    always @(posedge clk) begin
        past_valid <= 1;
        if (!past_valid) assume(rst);
        if (rst) begin
            if (pending && shifting) saw_abort <= 1;
            pending <= 0;
            age <= 0;
        end else begin
            if (past_valid && $past(rst)) assert(!out_valid);
            if (start && ready) begin
                assert(!pending);
                pending <= 1;
                age <= 0;
            end
            if (pending) begin
                assert(age <= latency);
                if (age == latency) assert(out_valid);
                if (!out_valid) age <= age+1;
            end
            if (out_valid) begin
                assert(pending);
                assert(age == latency);
                assert(out_value == expected);
                assert(stored_value == expected);
                assert(out_index == in_index && out_kind == 5);
                assert(out_value <= 127);
                pending <= 0;
            end
            cover(out_valid && in_shift > 33 && out_value == 0); // Q35 oversized shifts
            cover(out_valid && in_shift == 1 && in_power == 5 && out_value == 2); // Q36 even tie
            cover(out_valid && in_shift == 1 && in_power == 3 && out_value == 2); // Q37 odd tie
            cover(out_valid && in_shift == 1 && in_power == 255 && out_value == 127); // Q38 rounding into saturation
            cover(out_valid && in_shift == 0 && in_power == 33'h1ffffffff && out_value == 127); // Q39 max power
            cover(out_valid && in_shift == 33 && in_power == 33'h100000000 && out_value == 0); // Q40 half to even zero
            cover(out_valid && in_shift == 33 && in_power == 33'h100000001 && out_value == 1); // Q41 above half
            cover(out_valid && in_power == 91 && in_shift == 2 && out_value == 23); // Q42 exported CWRU example
            cover(out_valid && in_index == 15); // Q43 final feature -> NN_INIT
            cover(out_valid && in_index == 0); // Q44 next feature -> POWER_RE_MUL
            cover(out_valid && saw_abort); // Q45 reset during shift, then successful retry
        end
    end
    genvar s;
    generate for(s=0;s<=33;s=s+1) begin: g_each_shift
        always @(posedge clk) if(past_valid && !rst)
            cover(out_valid && in_shift == s); // Q01..Q34 complete each supported iteration count
    end endgenerate
endmodule
