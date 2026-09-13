// Low-pin-count implementation probe, not the application's board top.
// Parity observes every output so synthesis retains diagnostics/counters.
module core_pnr_probe #(
    parameter integer N=1024,
    parameter integer LANES=4,
    parameter integer BANDS=1,
    parameter integer HIDDEN_SHIFT=8,
    parameter MODEL_DIR="artifacts/model"
)(
    input wire clk, rst, in_valid, in_last,
    input wire signed [15:0] in_sample,
    output wire in_ready, out_valid, observation
);
    reg [31:0] frame_id;
    always @(posedge clk) begin
        if (rst) frame_id<=0;
        else if (in_valid && in_ready && in_last) frame_id<=frame_id+1;
    end
    wire [31:0] output_id, pre, dft, power_cycles, nn_cycles, total, errors;
    wire [95:0] logits;
    wire [1:0] class_id;
    wire [7:0] error_flags;
    wire dbg_valid;
    wire [3:0] dbg_kind;
    wire [15:0] dbg_index;
    wire signed [39:0] dbg_value;
    vibration_core #(.N(N),.LANES(LANES),.BANDS(BANDS),.HIDDEN_SHIFT(HIDDEN_SHIFT),.MODEL_DIR(MODEL_DIR)) core(
        .clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),.in_sample(in_sample),
        .in_frame_id(frame_id),.in_last(in_last),.out_valid(out_valid),.out_ready(1'b1),
        .out_frame_id(output_id),.out_logits(logits),.out_class(class_id),.out_error(error_flags),
        .cycles_pre(pre),.cycles_dft(dft),.cycles_power(power_cycles),.cycles_nn(nn_cycles),
        .cycles_total(total),.protocol_errors(errors),.dbg_valid(dbg_valid),.dbg_kind(dbg_kind),
        .dbg_index(dbg_index),.dbg_value(dbg_value)
    );
    assign observation = ^{output_id,logits,class_id,error_flags,pre,dft,power_cycles,
                            nn_cycles,total,errors,dbg_valid,dbg_kind,dbg_index,dbg_value};
endmodule
