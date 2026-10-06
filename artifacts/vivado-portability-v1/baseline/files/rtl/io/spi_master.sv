// Byte-oriented MSB-first SPI master. Legal HALF_PERIOD >= 1.
// A transaction starts on the first accepted byte and ends after tx_last.
// Between bytes CS stays asserted and SCLK stays at CPOL. No RX backpressure.
module spi_master #(
    parameter bit CPOL = 1'b0,
    parameter bit CPHA = 1'b0,
    parameter integer HALF_PERIOD = 6
) (
    input wire clk, rst,
    input wire tx_valid,
    output wire tx_ready,
    input wire [7:0] tx_data,
    input wire tx_last,
    output reg rx_valid,
    output reg [7:0] rx_data,
    output wire busy,
    output reg sclk, mosi,
    input wire miso,
    output reg cs_n
);
    localparam integer DIV_W = HALF_PERIOD > 1 ? $clog2(HALF_PERIOD) : 1;
    reg [DIV_W-1:0] divider;
    reg [7:0] tx_shift, rx_shift;
    reg [3:0] edge_count;
    reg byte_active, finishing, last_byte;
    assign tx_ready = !rst && !byte_active;
    assign busy = !cs_n;

    always @(posedge clk) begin
        if (rst) begin
            divider <= 0;
            tx_shift <= 0;
            rx_shift <= 0;
            edge_count <= 0;
            byte_active <= 0;
            finishing <= 0;
            last_byte <= 0;
            rx_valid <= 0;
            rx_data <= 0;
            sclk <= CPOL;
            mosi <= 0;
            cs_n <= 1;
        end else begin
            rx_valid <= 0;
            if (tx_valid && tx_ready) begin
                cs_n <= 0;
                byte_active <= 1;
                finishing <= 0;
                last_byte <= tx_last;
                tx_shift <= tx_data;
                rx_shift <= 0;
                edge_count <= 0;
                divider <= DIV_W'(HALF_PERIOD-1);
                sclk <= CPOL;
                if (!CPHA) mosi <= tx_data[7];
            end else if (byte_active) begin
                if (finishing) begin
                    // Keep CS low for one system clock after the final SCLK edge.
                    rx_valid <= 1;
                    rx_data <= rx_shift;
                    byte_active <= 0;
                    finishing <= 0;
                    if (last_byte) cs_n <= 1;
                end else if (divider == 0) begin
                    divider <= DIV_W'(HALF_PERIOD-1);
                    sclk <= !sclk;
                    if (edge_count[0] == CPHA)
                        rx_shift <= {rx_shift[6:0], miso};
                    else if (CPHA) begin
                        mosi <= tx_shift[7];
                        tx_shift <= {tx_shift[6:0], 1'b0};
                    end else if (edge_count != 15) begin
                        mosi <= tx_shift[6];
                        tx_shift <= {tx_shift[6:0], 1'b0};
                    end
                    if (edge_count == 15) finishing <= 1;
                    else edge_count <= edge_count + 1'b1;
                end else divider <= divider - 1'b1;
            end
        end
    end
endmodule
