module upduino_known #(
    parameter integer LANES=4,STARTUP_CYCLES=120000,
    parameter MODEL_DIR="artifacts/acoustic-known-release-v1/id00",
    parameter [255:0] MODEL_HASH=0,
    parameter signed [31:0] BIAS=0,THRESHOLD=0,LOG_CONSTANT=128145,LOG_FLOOR=-163279
)(input wire flash_miso,output wire flash_cs_n,flash_sclk,flash_mosi,
   output wire status_done,status_error,status_running);
    wire clk;reg [16:0] startup=0;
    SB_HFOSC #(.CLKHF_DIV("0b10")) oscillator(.CLKHFPU(1'b1),.CLKHFEN(1'b1),.CLKHF(clk));
    wire rst=startup<STARTUP_CYCLES;
    always @(posedge clk)if(rst)startup<=startup+1'b1;
    known_replay_system #(.LANES(LANES),.MODEL_DIR(MODEL_DIR),.MODEL_HASH(MODEL_HASH),
        .BIAS(BIAS),.THRESHOLD(THRESHOLD),.LOG_CONSTANT(LOG_CONSTANT),.LOG_FLOOR(LOG_FLOOR)) system(.*);
endmodule

module known_replay_system #(
    parameter integer N=1024,WINDOWS=156,LANES=4,
    parameter MODEL_DIR="artifacts/acoustic-known-release-v1/id00",
    parameter [255:0] MODEL_HASH=0,
    parameter signed [31:0] BIAS=0,THRESHOLD=0,LOG_CONSTANT=128145,LOG_FLOOR=-163279
)(input wire clk,rst,flash_miso,output wire flash_cs_n,flash_sclk,flash_mosi,
   output wire status_done,status_error,status_running);
    wire cmd_valid,cmd_write,cmd_ready,rd_valid,rd_ready,wr_valid,wr_ready,flash_done,flash_error;
    wire [23:0] cmd_address;wire [15:0] cmd_length;wire [7:0] rd_data,wr_data;
    wire in_valid,in_ready,in_last,out_valid,out_class;wire signed [15:0] in_sample;
    wire signed [31:0] out_score;wire [7:0] out_error;
    wire [31:0] in_frame_id,out_frame_id,cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total,protocol_errors,accepted_samples;
    // Thousands of complete two-byte status transactions remain a generous
    // bounded wait; a device still busy at the limit reports an explicit error.
    flash_stream #(.POLL_LIMIT(4095)) transport(.done(flash_done),.error(flash_error),.*);
    known_replay_controller #(.N(N),.WINDOWS(WINDOWS),.LANES(LANES),.MODEL_HASH(MODEL_HASH),.THRESHOLD(THRESHOLD)) controller(.*);
    // Hold the only result until external reset so the log serializer sees
    // immutable scores and stage counters without another register copy.
    known_spectral_core #(.N(N),.WINDOWS(WINDOWS),.LANES(LANES),.MODEL_DIR(MODEL_DIR),
        .BIAS(BIAS),.THRESHOLD(THRESHOLD),.LOG_CONSTANT(LOG_CONSTANT),.LOG_FLOOR(LOG_FLOOR)) core(
        .out_ready(1'b0),.dbg_valid(),.dbg_kind(),.dbg_frame(),.dbg_index(),.dbg_value(),.*);
endmodule
