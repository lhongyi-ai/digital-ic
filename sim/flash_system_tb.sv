// Simulation-only harness; the autonomous clock avoids Python per-cycle polling.
`timescale 1ns/1ps
module flash_system_tb #(
    parameter MODEL_DIR="artifacts/model",
    parameter integer LANES=4,
    parameter integer BANDS=1,
    parameter integer HIDDEN_SHIFT=8,
    parameter integer LOG_SCAN_CHUNK_SHIFT=15,
    parameter [255:0] MODEL_HASH=0
)(input wire rst,direct_mode,flash_miso,
  output wire flash_cs_n,flash_sclk,flash_mosi,
  output wire status_done,status_error,status_running,
  input wire cmd_valid,cmd_write,wr_valid,rd_ready,
  input wire [23:0] cmd_address,input wire [15:0] cmd_length,input wire [7:0] wr_data,
  output wire cmd_ready,wr_ready,rd_valid,done,error,output wire [7:0] rd_data);
    reg clk=0;
    always #5 clk=~clk;
    wire sys_cs,sys_sclk,sys_mosi,direct_cs,direct_sclk,direct_mosi;
    assign flash_cs_n=direct_mode?direct_cs:sys_cs;
    assign flash_sclk=direct_mode?direct_sclk:sys_sclk;
    assign flash_mosi=direct_mode?direct_mosi:sys_mosi;
    replay_system #(.LANES(LANES),.BANDS(BANDS),.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(HIDDEN_SHIFT),
        .MODEL_HASH(MODEL_HASH),.TAIL_TIMEOUT(1200000),.LOG_SCAN_CHUNK_SHIFT(LOG_SCAN_CHUNK_SHIFT)) system(
        .clk(clk),.rst(rst||direct_mode),.flash_miso(flash_miso),
        .flash_cs_n(sys_cs),.flash_sclk(sys_sclk),.flash_mosi(sys_mosi),
        .status_done(status_done),.status_error(status_error),.status_running(status_running));
    flash_stream #(.POLL_LIMIT(4)) direct_transport(
        .clk(clk),.rst(rst||!direct_mode),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
        .cmd_write(cmd_write),.cmd_address(cmd_address),.cmd_length(cmd_length),
        .wr_valid(wr_valid),.wr_ready(wr_ready),.wr_data(wr_data),
        .rd_valid(rd_valid),.rd_ready(rd_ready),.rd_data(rd_data),.done(done),.error(error),
        .flash_cs_n(direct_cs),.flash_sclk(direct_sclk),.flash_mosi(direct_mosi),.flash_miso(flash_miso));
endmodule
