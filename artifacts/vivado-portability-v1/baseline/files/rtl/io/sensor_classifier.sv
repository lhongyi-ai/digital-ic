// Independent N=256 field profile. No changes to the archived CWRU pipeline.
// A gap is an explicit transaction cancellation, including any stalled output.
module sensor_classifier #(
    parameter integer LANES = 1,
    parameter MODEL_DIR = "build/field_fixture/trained/model",
    parameter integer HIDDEN_SHIFT = 8
) (
    input wire clk, rst,
    input wire in_valid,
    output wire in_ready,
    input wire signed [15:0] in_sample,
    input wire [31:0] in_service_cycle,
    input wire gap,
    output wire out_valid,
    input wire out_ready,
    output wire [31:0] out_frame_id,
    output wire [95:0] out_logits,
    output wire [1:0] out_class,
    output wire [7:0] out_error,
    output wire [31:0] cycles_pre, cycles_dft, cycles_power, cycles_nn, cycles_total,
    output wire [31:0] out_first_service_cycle, out_last_service_cycle,
    output wire busy,
    output reg [7:0] partial_samples,
    output reg [31:0] accepted_samples, dropped_samples, canceled_frames, clip_count,
    output reg [31:0] protocol_errors
);
    wire core_ready, core_valid;
    wire [31:0] core_protocol_errors;
    wire metadata_ready, metadata_valid;
    wire [63:0] metadata;
    wire [1:0] pending;
    reg [31:0] next_frame_id, current_frame_id, first_service_cycle;

    // Credit for a same-edge completed output uses the core's registered valid,
    // not the externally gated out_valid. ready therefore does not depend on
    // core_ready, which is reset-gated and would form an abort/reset loop.
    wire release_credit = core_valid && out_ready && (pending != 0);
    assign in_ready = !rst && !gap &&
        ((partial_samples != 0) || (pending < 2) || release_credit);
    wire abort_transaction = gap || (in_valid && !in_ready);
    wire pipeline_reset = rst || abort_transaction;
    wire take_sample = in_valid && in_ready && !abort_transaction;
    wire complete_window = take_sample && partial_samples == 8'd255;
    wire deliver_output = core_valid && out_ready && metadata_valid && !pipeline_reset;

    wire signed [15:0] clamped_sample = in_sample < -16'sd1024 ? -16'sd1024 :
                                       in_sample > 16'sd1023 ? 16'sd1023 : in_sample;
    // Exact mapping: [-1024,1023] * 32 fits signed16; no calibration is applied.
    wire signed [15:0] core_sample = clamped_sample <<< 5;
    wire [31:0] input_frame_id = partial_samples == 0 ? next_frame_id : current_frame_id;

    vibration_core #(.N(256), .LANES(LANES), .BANDS(1),
        .MODEL_DIR(MODEL_DIR), .HIDDEN_SHIFT(HIDDEN_SHIFT)) core (
        .clk(clk), .rst(pipeline_reset), .in_valid(take_sample), .in_ready(core_ready),
        .in_sample(core_sample), .in_frame_id(input_frame_id), .in_last(complete_window),
        .out_valid(core_valid), .out_ready(deliver_output),
        .out_frame_id(out_frame_id), .out_logits(out_logits), .out_class(out_class),
        .out_error(out_error), .cycles_pre(cycles_pre), .cycles_dft(cycles_dft),
        .cycles_power(cycles_power), .cycles_nn(cycles_nn), .cycles_total(cycles_total),
        .protocol_errors(core_protocol_errors), .dbg_valid(), .dbg_kind(), .dbg_index(), .dbg_value()
    );

    // At most two complete windows are outstanding. This leaves the original
    // core's two raw banks sufficient for every advertised accepted sample.
    sync_fifo #(.WIDTH(64), .DEPTH(2)) timestamp_fifo (
        .clk(clk), .rst(pipeline_reset), .in_valid(complete_window), .in_ready(metadata_ready),
        .in_data({in_service_cycle, first_service_cycle}), .out_valid(metadata_valid),
        .out_ready(deliver_output), .out_data(metadata), .occupancy(pending)
    );
    assign out_valid = core_valid && metadata_valid && !pipeline_reset;
    assign out_first_service_cycle = metadata[31:0];
    assign out_last_service_cycle = metadata[63:32];
    assign busy = !rst && (pending != 0);

    always @(posedge clk) begin
        if (rst) begin
            partial_samples<=0; next_frame_id<=0; current_frame_id<=0; first_service_cycle<=0;
            accepted_samples<=0; dropped_samples<=0; canceled_frames<=0; clip_count<=0;
            protocol_errors<=0;
        end else if (abort_transaction) begin
            // A gap's same-cycle sample is discarded. Previously accepted
            // samples are not counted again as dropped; canceled_frames records
            // the complete and partial transactions invalidated by this event.
            partial_samples<=0; current_frame_id<=0; first_service_cycle<=0;
            dropped_samples<=dropped_samples+{31'd0,in_valid};
            canceled_frames<=canceled_frames+{30'd0,pending}+{31'd0,(partial_samples != 0)};
            protocol_errors<=protocol_errors+1;
        end else if (take_sample) begin
            accepted_samples<=accepted_samples+1;
            if (in_sample < -16'sd1024 || in_sample > 16'sd1023) clip_count<=clip_count+1;
            if (partial_samples == 0) begin
                current_frame_id<=next_frame_id;
                next_frame_id<=next_frame_id+1;
                first_service_cycle<=in_service_cycle;
            end
            partial_samples<=partial_samples+1'b1;
        end
    end

`ifdef VIB_ASSERT
    initial assert (LANES == 1 || LANES == 4);
    always @(posedge clk) if (!pipeline_reset) begin
        assert (pending <= 2);
        if (take_sample) assert (core_ready);
        if (complete_window) assert (metadata_ready);
        if (core_valid) assert (metadata_valid);
        assert (core_protocol_errors == 0);
    end
    // Cancellation explicitly permits withdrawing an unaccepted output.
    assert property (@(posedge clk) disable iff (pipeline_reset)
        out_valid && !out_ready |=> out_valid && $stable({out_frame_id,out_logits,
        out_class,out_error,cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total,
        out_first_service_cycle,out_last_service_cycle}));
`endif
endmodule
