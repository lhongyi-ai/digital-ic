// One synchronous quarter-wave cosine ROM per multiplier lane.
// Coefficients are Q2.14; exact quadrant endpoints are handled explicitly.
module vib_coeff_rom #(
    parameter integer N = 1024,
    parameter bit HANN = 0,
    parameter MODEL_DIR = "artifacts/model"
) (
    input wire clk,
    input wire en,
    input wire [$clog2(N)-1:0] phase,
    output wire signed [15:0] coefficient
);
    localparam integer P = $clog2(N);
    localparam integer Q = P-2;
    (* ram_style = "block" *) reg signed [15:0] quarter [0:N/4-1];
    reg signed [15:0] magnitude;
    reg negative, is_zero;
    wire [Q-1:0] offset = phase[Q-1:0];
    wire [1:0] quadrant = phase[P-1:P-2];
    wire [Q-1:0] address = quadrant[0] ? -offset : offset;
    generate if (HANN) begin: g_hann_init
        initial $readmemh({MODEL_DIR, "/hann_quarter.hex"}, quarter);
    end else begin: g_cos_init
        initial $readmemh({MODEL_DIR, "/cos_quarter.hex"}, quarter);
    end endgenerate
    always @(posedge clk) begin
        if (en) begin
            magnitude <= quarter[address];
            negative <= (quadrant == 1 || quadrant == 2);
            is_zero <= quadrant[0] && offset == 0;
        end
    end
    assign coefficient = is_zero ? (HANN ? 16'sd8192 : 16'sd0) :
                         negative ? (HANN ? 16'sd16384-magnitude : -magnitude) : magnitude;
endmodule
