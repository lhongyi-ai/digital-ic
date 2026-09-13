// Test-only access to the actual functions used inside vibration_core.
module arithmetic_tb #(
    parameter MODEL_DIR="artifacts/model",
    parameter integer HIDDEN_SHIFT=8
)(
    input wire signed [63:0] value,
    input wire [7:0] shift,
    input wire [32:0] power_value,
    output wire signed [63:0] rounded,
    output wire signed [15:0] clipped12, clipped16,
    output wire [7:0] power_quantized, hidden_quantized
);
    vibration_core #(.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(HIDDEN_SHIFT)) core(
        .clk(1'b0),.rst(1'b1),.in_valid(1'b0),.in_ready(),.in_sample(16'd0),
        .in_frame_id(32'd0),.in_last(1'b0),.out_valid(),.out_ready(1'b0),
        .out_frame_id(),.out_logits(),.out_class(),.out_error(),.cycles_pre(),
        .cycles_dft(),.cycles_power(),.cycles_nn(),.cycles_total(),.protocol_errors(),
        .dbg_valid(),.dbg_kind(),.dbg_index(),.dbg_value()
    );
    assign rounded = core.rne($signed(value[39:0]),int'(shift));
    assign clipped12 = core.sat12($signed(value[39:0]));
    assign clipped16 = core.sat16($signed(value[39:0]));
    assign power_quantized = core.power_quant(power_value,shift);
    assign hidden_quantized = core.relu_quant(value[39:0]);
endmodule
