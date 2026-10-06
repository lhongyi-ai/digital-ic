// Two-point gravity correction, output signed milligravity (mg).
// RNE((raw*256-OFFSET_Q8)*GAIN_Q20,28), saturated to signed32.
// Bit-serial multiply intentionally uses no FPGA DSP, leaving MACs for spectra.
module static_calibration #(
    parameter signed [31:0] OFFSET_Q8=0,
    parameter [31:0] GAIN_Q20=32'd4096000
)(input wire clk,rst,input wire in_valid,output wire in_ready,
   input wire signed [15:0] in_raw,
   output reg out_valid,input wire out_ready,output reg signed [31:0] out_mg);
    reg busy,negative;
    reg [4:0] bit_index;
    reg [63:0] accumulator,multiplicand;
    reg [30:0] multiplier;
    wire signed [32:0] centered=($signed({{9{in_raw[15]}},in_raw,8'b0})-$signed({OFFSET_Q8[31],OFFSET_Q8}));
    wire [63:0] next_accumulator=accumulator+(multiplier[0]?multiplicand:64'd0);
    wire [35:0] rounded=next_accumulator[63:28]+((next_accumulator[27:0]>28'h8000000 ||
        (next_accumulator[27:0]==28'h8000000 && next_accumulator[28]))?36'd1:36'd0);
    assign in_ready=!rst && !busy && (!out_valid || out_ready);
    always @(posedge clk) begin
        if(rst) begin
            busy<=0;negative<=0;bit_index<=0;accumulator<=0;multiplicand<=0;
            multiplier<=0;out_valid<=0;out_mg<=0;
        end else begin
            if(out_valid && out_ready)out_valid<=0;
            if(in_valid && in_ready)begin
                busy<=1;negative<=centered[32];bit_index<=0;accumulator<=0;
                multiplicand<=centered[32]?{31'd0,$unsigned(-centered)}:{31'd0,$unsigned(centered)};
                multiplier<=GAIN_Q20[30:0];
            end else if(busy)begin
                accumulator<=next_accumulator;multiplicand<=multiplicand<<1;multiplier<=multiplier>>1;
                if(bit_index==30)begin
                    busy<=0;out_valid<=1;
                    if(negative) out_mg<=rounded>=36'h080000000 ? 32'sh80000000 : -$signed(rounded[31:0]);
                    else out_mg<=rounded>36'h07fffffff ? 32'sh7fffffff : $signed(rounded[31:0]);
                end else bit_index<=bit_index+1'b1;
            end
        end
    end
endmodule
