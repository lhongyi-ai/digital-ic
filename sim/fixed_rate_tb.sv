// Synthesizable simulation source: ticks are never postponed by backpressure.
// The ROM is test data; deployed replay_source uses the board SPRAM path.
module fixed_rate_tb #(
    parameter integer N=1024,
    parameter integer LANES=4,
    parameter integer BANDS=1,
    parameter integer HIDDEN_SHIFT=8,
    parameter MODEL_DIR="artifacts/model",
    parameter RAW_FILE="artifacts/vectors/replay_000.hex"
)(
    input wire clk, rst,
    input wire [31:0] run_frames, period_cycles, overload_frames,
    output reg source_done,
    output reg [31:0] generated_samples, accepted_samples, dropped_samples, output_frames,
    output wire [31:0] protocol_errors,
    output reg result_pulse,
    output reg [31:0] result_frame_id,
    output reg [95:0] result_logits,
    output reg [1:0] result_class,
    output reg [7:0] result_error,
    output reg [31:0] result_latency,
    output reg [31:0] maximum_fifo_occupancy
);
    localparam integer P=$clog2(N);
    reg [15:0] samples [0:N-1];
    initial $readmemh(RAW_FILE,samples);
    reg [P-1:0] point;
    reg [31:0] source_frame, tick_count;
    wire [31:0] period_now = source_frame < overload_frames ? 32'd1 : period_cycles;
    wire tick = !rst && !source_done && tick_count == period_now-1;
    wire fifo_ready, fifo_valid, core_ready;
    wire [48:0] fifo_data;
    wire [2:0] occupancy;
    sync_fifo #(.WIDTH(49),.DEPTH(4)) fifo(
        .clk(clk),.rst(rst),.in_valid(tick),.in_ready(fifo_ready),
        .in_data({source_frame,point == P'(N-1),samples[point]}),
        .out_valid(fifo_valid),.out_ready(core_ready),.out_data(fifo_data),.occupancy(occupancy)
    );
    wire out_valid;
    wire [31:0] out_id, pre, dft, power_cycles, nn_cycles, total;
    wire [95:0] logits;
    wire [1:0] class_id;
    wire [7:0] errors;
    vibration_core #(.N(N),.LANES(LANES),.BANDS(BANDS),.HIDDEN_SHIFT(HIDDEN_SHIFT),.MODEL_DIR(MODEL_DIR)) core(
        .clk(clk),.rst(rst),.in_valid(fifo_valid),.in_ready(core_ready),
        .in_sample(fifo_data[15:0]),.in_last(fifo_data[16]),.in_frame_id(fifo_data[48:17]),
        .out_valid(out_valid),.out_ready(1'b1),.out_frame_id(out_id),.out_logits(logits),
        .out_class(class_id),.out_error(errors),.cycles_pre(pre),.cycles_dft(dft),
        .cycles_power(power_cycles),.cycles_nn(nn_cycles),.cycles_total(total),
        .protocol_errors(protocol_errors),.dbg_valid(),.dbg_kind(),.dbg_index(),.dbg_value()
    );
    always @(posedge clk) begin
        if (rst) begin
            point<=0; source_frame<=0; tick_count<=0; source_done<=0;
            generated_samples<=0; accepted_samples<=0; dropped_samples<=0; output_frames<=0;
            result_pulse<=0; result_frame_id<=0; result_logits<=0; result_class<=0;
            result_error<=0; result_latency<=0; maximum_fifo_occupancy<=0;
        end else begin
            result_pulse<=0;
            if (!source_done) begin
                if (tick) begin
                    tick_count<=0; generated_samples<=generated_samples+1;
                    if (!fifo_ready) dropped_samples<=dropped_samples+1;
                    if (point == P'(N-1)) begin
                        point<=0; source_frame<=source_frame+1;
                        if (source_frame+1 == run_frames) source_done<=1;
                    end else point<=point+1;
                end else tick_count<=tick_count+1;
            end
            if (fifo_valid && core_ready) accepted_samples<=accepted_samples+1;
            if ({29'd0,occupancy} > maximum_fifo_occupancy) maximum_fifo_occupancy<={29'd0,occupancy};
            if (out_valid) begin
                output_frames<=output_frames+1; result_pulse<=1;
                result_frame_id<=out_id; result_logits<=logits; result_class<=class_id;
                result_error<=errors; result_latency<=total;
            end
        end
    end
endmodule
