// Single-clock, registered-storage FIFO. No combinational empty bypass.
// Legal parameters: WIDTH >= 1 and DEPTH >= 1 (DEPTH need not be a power of 2).
module sync_fifo #(
    parameter integer WIDTH = 16,
    parameter integer DEPTH = 4,
    parameter integer COUNT_W = $clog2(DEPTH + 1)
) (
    input  wire                 clk,
    input  wire                 rst,
    input  wire                 in_valid,
    output wire                 in_ready,
    input  wire [WIDTH-1:0]     in_data,
    output wire                 out_valid,
    input  wire                 out_ready,
    output wire [WIDTH-1:0]     out_data,
    output reg  [COUNT_W-1:0]   occupancy
);
    localparam integer PTR_W = DEPTH > 1 ? $clog2(DEPTH) : 1;
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [PTR_W-1:0] rd_ptr, wr_ptr;

    assign out_valid = !rst && (occupancy != 0);
    // A pop releases its slot on this edge, including at full capacity.
    assign in_ready = !rst && ((occupancy < COUNT_W'(DEPTH)) || out_ready);
    assign out_data = mem[rd_ptr];
    wire push = in_valid && in_ready;
    wire pop = out_valid && out_ready;

    always @(posedge clk) begin
        if (rst) begin
            occupancy <= 0;
            rd_ptr <= 0;
            wr_ptr <= 0;
        end else begin
            if (push) begin
                mem[wr_ptr] <= in_data;
                wr_ptr <= wr_ptr == PTR_W'(DEPTH-1) ? '0 : wr_ptr + 1'b1;
            end
            if (pop)
                rd_ptr <= rd_ptr == PTR_W'(DEPTH-1) ? '0 : rd_ptr + 1'b1;
            case ({push, pop})
                2'b10: occupancy <= occupancy + 1'b1;
                2'b01: occupancy <= occupancy - 1'b1;
                default: occupancy <= occupancy;
            endcase
        end
    end
endmodule
