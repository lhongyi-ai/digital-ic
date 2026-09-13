// Implementation probe only; this is never used as the application's bitstream.
module known_pnr_probe #(
    parameter integer LANES=4,
    parameter MODEL_DIR="artifacts/acoustic-known-release-v1/id00",
    parameter signed [31:0] BIAS=0,THRESHOLD=0,
    parameter integer LOG_CONSTANT=128145
)(input wire clk,rst,in_valid,in_last,input wire signed [15:0] in_sample,
   output wire in_ready,out_valid,observation);
    reg [31:0] frame_id;
    always @(posedge clk) if(rst) frame_id<=0;else if(in_valid&&in_ready&&in_last) frame_id<=frame_id+1;
    wire signed [31:0] score;
    wire [31:0] out_id,pre,dft,power_cycles,nn,total,errors,accepted;
    wire out_class;wire [7:0] out_error;
    known_spectral_core #(.N(1024),.WINDOWS(156),.LANES(LANES),.MODEL_DIR(MODEL_DIR),
        .BIAS(BIAS),.THRESHOLD(THRESHOLD),.LOG_CONSTANT(LOG_CONSTANT)) core(
        .clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),.in_sample(in_sample),.in_last(in_last),.in_frame_id(frame_id),
        .out_valid(out_valid),.out_ready(1'b1),.out_score(score),.out_frame_id(out_id),.out_class(out_class),.out_error(out_error),
        .cycles_pre(pre),.cycles_dft(dft),.cycles_power(power_cycles),.cycles_nn(nn),.cycles_total(total),
        .protocol_errors(errors),.accepted_samples(accepted),.dbg_valid(),.dbg_kind(),.dbg_frame(),.dbg_index(),.dbg_value());
    assign observation=^{score,out_id,out_class,out_error,pre,dft,power_cycles,nn,total,errors,accepted};
endmodule
