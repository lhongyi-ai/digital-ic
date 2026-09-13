// SPI NOR read / bounded page-program transport. The host erases log sectors.
// Writes are hardware-limited to the log partition; configuration is protected.
// command lengths 1..65535 for read, 1..256 within one page for program.
module flash_stream #(
    parameter [23:0] LOG_BASE = 24'h300000,
    parameter [23:0] LOG_END = 24'h320000,
    parameter integer HALF_PERIOD = 1,
    parameter integer POLL_LIMIT = 65535,
    // iCE40 configuration can leave NOR in deep power-down (B9). Release (AB)
    // and wait >=3 us tRES1 before exposing the command interface. 256 clocks
    // exceed 19 us even at the HFOSC +10% corner of 13.2 MHz.
    parameter integer WAKE_CYCLES = 256
) (
    input wire clk, rst,
    input wire cmd_valid, output wire cmd_ready,
    input wire cmd_write, input wire [23:0] cmd_address, input wire [15:0] cmd_length,
    input wire wr_valid, output wire wr_ready, input wire [7:0] wr_data,
    output reg rd_valid, input wire rd_ready, output reg [7:0] rd_data,
    output reg done, output reg error,
    output wire flash_cs_n, flash_sclk, flash_mosi, input wire flash_miso
);
    localparam IDLE=0, WREN=1, WREN_WAIT=2, HEADER=3, HEADER_WAIT=4,
        DATA=5, DATA_WAIT=6, READ_HOLD=7, STATUS=8, STATUS_WAIT=9,
        STATUS_DATA=10, STATUS_RESULT=11, WAKE=12, WAKE_WAIT=13, WAKE_SETTLE=14;
    reg [3:0] state;
    localparam integer WAKE_W = WAKE_CYCLES > 1 ? $clog2(WAKE_CYCLES) : 1;
    reg [WAKE_W-1:0] wake_count;
`ifdef VIB_ASSERT
    initial assert (WAKE_CYCLES >= 40);
`endif
    reg writing;
    reg [23:0] address;
    reg [15:0] remaining;
    reg [1:0] header_index;
    localparam integer POLL_W=$clog2(POLL_LIMIT+1);
    reg [POLL_W-1:0] polls;
    wire tx_ready, rx_valid;
    wire [7:0] rx_data;
    reg tx_valid, tx_last;
    reg [7:0] tx_data;
    wire spi_busy;
    spi_master #(.CPOL(0), .CPHA(0), .HALF_PERIOD(HALF_PERIOD)) spi(
        .clk(clk),.rst(rst),.tx_valid(tx_valid),.tx_ready(tx_ready),.tx_data(tx_data),
        .tx_last(tx_last),.rx_valid(rx_valid),.rx_data(rx_data),.busy(spi_busy),
        .sclk(flash_sclk),.mosi(flash_mosi),.miso(flash_miso),.cs_n(flash_cs_n));
    assign cmd_ready = state == IDLE && !rd_valid && !rst;
    assign wr_ready = state == DATA && writing && tx_ready && !rst;
    always @* begin
        tx_valid=0; tx_last=0; tx_data=0;
        case(state)
            WAKE: begin tx_valid=1; tx_last=1; tx_data=8'hab; end
            WREN: begin tx_valid=1; tx_last=1; tx_data=8'h06; end
            HEADER: begin
                tx_valid=1;
                case(header_index)
                    0: tx_data=writing ? 8'h02 : 8'h03;
                    1: tx_data=address[23:16];
                    2: tx_data=address[15:8];
                    3: tx_data=address[7:0];
                endcase
            end
            DATA: begin tx_valid=writing ? wr_valid : 1'b1;
                tx_data=writing ? wr_data : 8'h00; tx_last=remaining==1; end
            STATUS: begin tx_valid=1; tx_data=8'h05; end
            STATUS_DATA: begin tx_valid=1; tx_last=1; end
            default: begin end
        endcase
    end
    always @(posedge clk) begin
        if(rst) begin
            state<=WAKE; wake_count<=0; rd_valid<=0; rd_data<=0; done<=0; error<=0;
            writing<=0;address<=0;remaining<=0;header_index<=0;polls<=0;
        end else begin
            done<=0;
            if(rd_valid && rd_ready) rd_valid<=0;
            case(state)
                WAKE: if(tx_valid && tx_ready) state<=WAKE_WAIT;
                WAKE_WAIT: if(rx_valid) begin wake_count<=0; state<=WAKE_SETTLE; end
                WAKE_SETTLE: begin
                    if(wake_count == WAKE_W'(WAKE_CYCLES-1)) state<=IDLE;
                    else wake_count<=wake_count+1'b1;
                end
                IDLE: if(cmd_valid && cmd_ready) begin
                    error<=0;
                    if(cmd_length==0 || (cmd_write && (cmd_length>256 ||
                        {17'd0,cmd_address[7:0]}+{9'd0,cmd_length}>256 ||
                        cmd_address<LOG_BASE || {1'b0,cmd_address}+{9'd0,cmd_length}>{1'b0,LOG_END}))) begin
                        error<=1;done<=1;
                    end else begin
                        address<=cmd_address;remaining<=cmd_length;writing<=cmd_write;
                        header_index<=0;polls<=0;state<=cmd_write?WREN:HEADER;
                    end
                end
                WREN: if(tx_valid && tx_ready) state<=WREN_WAIT;
                WREN_WAIT: if(rx_valid) state<=HEADER;
                HEADER: if(tx_valid && tx_ready) state<=HEADER_WAIT;
                HEADER_WAIT: if(rx_valid) begin
                    if(header_index==3) state<=DATA;
                    else begin header_index<=header_index+1'b1; state<=HEADER; end
                end
                DATA: if(tx_valid && tx_ready) state<=DATA_WAIT;
                DATA_WAIT: if(rx_valid) begin
                    remaining<=remaining-1'b1;
                    if(writing) begin
                        if(remaining==1) state<=STATUS; else state<=DATA;
                    end else begin rd_data<=rx_data;rd_valid<=1;state<=READ_HOLD;end
                end
                READ_HOLD: if(rd_valid && rd_ready) begin
                    if(remaining==0) begin state<=IDLE;done<=1;end else state<=DATA;
                end
                STATUS: if(tx_valid && tx_ready) state<=STATUS_WAIT;
                STATUS_WAIT: if(rx_valid) state<=STATUS_DATA;
                STATUS_DATA: if(tx_valid && tx_ready) state<=STATUS_RESULT;
                STATUS_RESULT: if(rx_valid) begin
                    if(!rx_data[0]) begin done<=1;state<=IDLE;end
                    else if(polls==POLL_W'(POLL_LIMIT-1)) begin error<=1;done<=1;state<=IDLE;end
                    else begin polls<=polls+1'b1;state<=STATUS;end
                end
                default: begin state<=IDLE;error<=1;end
            endcase
        end
    end
endmodule
