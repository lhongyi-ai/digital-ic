// Simulation-only passive probes. The unmodified core receives complete raw frames;
// no features, weights, accumulators, or state are forced by this wrapper.
module nn_edges_tb #(
    parameter integer LANES = 4,
    parameter MODEL_DIR = "build/nn_edges/active_model"
) (
    input wire clk, rst,
    input wire in_valid,
    output wire in_ready,
    input wire signed [15:0] in_sample,
    input wire [31:0] in_frame_id,
    input wire in_last,
    output wire out_valid,
    input wire out_ready,
    output wire [31:0] out_frame_id,
    output wire [95:0] out_logits,
    output wire [1:0] out_class,
    output wire [7:0] out_error,
    output wire [31:0] cycles_pre, cycles_dft, cycles_power, cycles_nn, cycles_total,
    output wire [31:0] protocol_errors,
    output wire probe_store,
    output wire probe_layer,
    output wire [3:0] probe_index,
    output wire signed [39:0] probe_accumulator,
    output wire [7:0] probe_error,
    output wire [127:0] probe_features, probe_hidden
);
    vibration_core #(.N(1024), .LANES(LANES), .BANDS(1),
        .MODEL_DIR(MODEL_DIR), .HIDDEN_SHIFT(0)) core (
        .clk(clk), .rst(rst), .in_valid(in_valid), .in_ready(in_ready),
        .in_sample(in_sample), .in_frame_id(in_frame_id), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_frame_id(out_frame_id),
        .out_logits(out_logits), .out_class(out_class), .out_error(out_error),
        .cycles_pre(cycles_pre), .cycles_dft(cycles_dft), .cycles_power(cycles_power),
        .cycles_nn(cycles_nn), .cycles_total(cycles_total), .protocol_errors(protocol_errors),
        .dbg_valid(), .dbg_kind(), .dbg_index(), .dbg_value()
    );
    // NN_STORE is state 21 in the source version bound into the test manifest.
    // Ignore lane 3's padded output row in the four-lane implementation.
    assign probe_store = core.state == 5'd21 && (!core.nn_layer || core.nn_output_index < 3);
    assign probe_layer = core.nn_layer;
    assign probe_index = core.nn_output_index;
    assign probe_accumulator = core.selected_accumulator;
    assign probe_error = core.arithmetic_errors;
    genvar i;
    generate for (i=0; i<16; i=i+1) begin: g_probe
        assign probe_features[8*i+:8] = core.features[i];
        assign probe_hidden[8*i+:8] = core.hidden[i];
    end endgenerate
endmodule
