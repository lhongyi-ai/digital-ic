// ADXL345: mode 3, 4-wire, full-resolution +/-2 g, FIFO bypass.
// This module needs a real 3.3 V ADXL345 and its INT1 data-ready pin.
module adxl345_capture #(
    parameter integer HALF_PERIOD = 6,
    parameter integer POWERUP_CYCLES = 24000,
    parameter [7:0] RATE_CODE = 8'h0d, // 0A=100 Hz, 0C=400 Hz, 0D=800 Hz
    parameter [31:0] SERVICE_COUNTER_START = 0 // Nonzero is for rollover simulation.
) (
    input wire clk, rst, enable,
    input wire drdy,
    output wire sclk, mosi,
    input wire miso,
    output wire cs_n,
    output reg init_done, init_error,
    output reg [7:0] device_id,
    output reg sample_valid,
    input wire sample_ready,
    output reg signed [15:0] x, y, z,
    output reg [31:0] service_cycle,
    output reg [31:0] samples_captured,
    output reg [31:0] missed_service,
    output reg [31:0] sensor_overruns
);
    localparam [4:0] WAIT_ENABLE=0, POWERUP=1, ID_CMD=2, ID_CMD_RX=3,
        ID_DATA=4, ID_DATA_RX=5, CFG_ADDR=6, CFG_ADDR_RX=7,
        CFG_DATA=8, CFG_DATA_RX=9, READY=10, STAT_CMD=11,
        STAT_CMD_RX=12, STAT_DATA=13, STAT_DATA_RX=14,
        XYZ_SEND=15, XYZ_RX=16, COMMIT=17, SETTLE=18, ERROR=19;
    reg [4:0] state;
    reg [31:0] power_count, cycle_count;
    reg [2:0] cfg_index, byte_index;
    reg [2:0] settle_count;
    reg [47:0] payload;
    (* ASYNC_REG = "TRUE" *) reg drdy_meta, drdy_sync;
    reg tx_valid, tx_last;
    reg [7:0] tx_data;
    wire tx_ready, rx_valid, unused_busy;
    wire [7:0] rx_data;

    spi_master #(.CPOL(1), .CPHA(1), .HALF_PERIOD(HALF_PERIOD)) master (
        .clk(clk), .rst(rst), .tx_valid(tx_valid), .tx_ready(tx_ready),
        .tx_data(tx_data), .tx_last(tx_last), .rx_valid(rx_valid),
        .rx_data(rx_data), .busy(unused_busy), .sclk(sclk), .mosi(mosi), .miso(miso), .cs_n(cs_n)
    );

    function automatic [7:0] config_address(input [2:0] index);
        case (index)
            0: config_address=8'h2d; // standby before reconfiguration
            1: config_address=8'h2e; // disable old interrupt configuration
            2: config_address=8'h31; // full resolution, right justified, +/-2 g
            3: config_address=8'h2c; // normal-power 800 Hz
            4: config_address=8'h38; // FIFO bypass
            5: config_address=8'h2f; // map DATA_READY to INT1
            6: config_address=8'h2e; // enable DATA_READY interrupt
            7: config_address=8'h2d; // measurement mode
        endcase
    endfunction
    function automatic [7:0] config_value(input [2:0] index);
        case (index)
            2: config_value=8'h08;
            3: config_value=RATE_CODE;
            6: config_value=8'h80;
            7: config_value=8'h08;
            default: config_value=8'h00;
        endcase
    endfunction

    always @* begin
        tx_valid = 0;
        tx_data = 0;
        tx_last = 0;
        case (state)
            ID_CMD: begin tx_valid=1; tx_data=8'h80; end
            ID_DATA: begin tx_valid=1; tx_last=1; end
            CFG_ADDR: begin tx_valid=1; tx_data=config_address(cfg_index); end
            CFG_DATA: begin tx_valid=1; tx_data=config_value(cfg_index); tx_last=1; end
            STAT_CMD: begin tx_valid=1; tx_data=8'hb0; end
            STAT_DATA: begin tx_valid=1; tx_last=1; end
            XYZ_SEND: begin
                tx_valid=1;
                tx_data=(byte_index == 0) ? 8'hf2 : 8'h00;
                tx_last=(byte_index == 6);
            end
            default: begin end
        endcase
    end

    always @(posedge clk) begin
        if (rst) begin
            state <= WAIT_ENABLE;
            power_count <= 0;
            cycle_count <= SERVICE_COUNTER_START;
            cfg_index <= 0;
            byte_index <= 0;
            settle_count <= 0;
            payload <= 0;
            drdy_meta <= 0;
            drdy_sync <= 0;
            init_done <= 0;
            init_error <= 0;
            device_id <= 0;
            sample_valid <= 0;
            x <= 0; y <= 0; z <= 0;
            service_cycle <= 0;
            samples_captured <= 0;
            missed_service <= 0;
            sensor_overruns <= 0;
        end else begin
            cycle_count <= cycle_count + 1'b1;
            drdy_meta <= drdy;
            drdy_sync <= drdy_meta;
            if (sample_valid && sample_ready) sample_valid <= 0;
            case (state)
                WAIT_ENABLE: if (enable) begin power_count <= 0; state <= POWERUP; end
                POWERUP: if (POWERUP_CYCLES <= 1 || power_count == POWERUP_CYCLES-1)
                    state <= ID_CMD;
                    else power_count <= power_count + 1'b1;
                ID_CMD: if (tx_ready) state <= ID_CMD_RX;
                ID_CMD_RX: if (rx_valid) state <= ID_DATA;
                ID_DATA: if (tx_ready) state <= ID_DATA_RX;
                ID_DATA_RX: if (rx_valid) begin
                    device_id <= rx_data;
                    if (rx_data == 8'he5) begin cfg_index <= 0; state <= CFG_ADDR; end
                    else begin init_error <= 1; state <= ERROR; end
                end
                CFG_ADDR: if (tx_ready) state <= CFG_ADDR_RX;
                CFG_ADDR_RX: if (rx_valid) state <= CFG_DATA;
                CFG_DATA: if (tx_ready) state <= CFG_DATA_RX;
                CFG_DATA_RX: if (rx_valid) begin
                    if (cfg_index == 7) begin init_done <= 1; state <= READY; end
                    else begin cfg_index <= cfg_index + 1'b1; state <= CFG_ADDR; end
                end
                READY: if (enable && drdy_sync) state <= STAT_CMD;
                STAT_CMD: if (tx_ready) state <= STAT_CMD_RX;
                STAT_CMD_RX: if (rx_valid) state <= STAT_DATA;
                STAT_DATA: if (tx_ready) state <= STAT_DATA_RX;
                STAT_DATA_RX: if (rx_valid) begin
                    if (rx_data[0] && sensor_overruns != 32'hffffffff)
                        sensor_overruns <= sensor_overruns + 1'b1;
                    if (rx_data[7]) begin byte_index <= 0; state <= XYZ_SEND; end
                    else begin settle_count <= 0; state <= SETTLE; end
                end
                XYZ_SEND: if (tx_ready) state <= XYZ_RX;
                XYZ_RX: if (rx_valid) begin
                    if (byte_index != 0) payload[(byte_index-1)*8 +: 8] <= rx_data;
                    if (byte_index == 6) state <= COMMIT;
                    else begin byte_index <= byte_index + 1'b1; state <= XYZ_SEND; end
                end
                COMMIT: begin
                    if (samples_captured != 32'hffffffff)
                        samples_captured <= samples_captured + 1'b1;
                    if (!sample_valid || sample_ready) begin
                        x <= payload[15:0]; y <= payload[31:16]; z <= payload[47:32];
                        service_cycle <= cycle_count;
                        sample_valid <= 1;
                    end else if (missed_service != 32'hffffffff)
                        missed_service <= missed_service + 1'b1;
                    settle_count <= 0;
                    state <= SETTLE;
                end
                SETTLE: if (settle_count == 3) state <= READY;
                    else settle_count <= settle_count + 1'b1;
                ERROR: begin end // A reset is required to retry an invalid device ID.
                default: state <= WAIT_ENABLE;
            endcase
        end
    end
endmodule
