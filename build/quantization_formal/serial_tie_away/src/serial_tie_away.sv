// Automatically extracted. See extraction.json for source spans and SHA256.
module quant_functions_kernel #(parameter integer HIDDEN_SHIFT=8) (
    input wire signed [39:0] value,
    input wire [5:0] shift,
    output wire signed [39:0] rounded,
    output wire signed [15:0] clipped12, clipped16,
    output wire [7:0] hidden_quantized
);
    function automatic signed [39:0] rne;
        input signed [39:0] value;
        input integer shift;
        reg signed [39:0] quotient;
        reg [39:0] remainder, halfway;
        begin
            if (shift == 0) rne = value;
            else begin
                quotient = value >>> shift;
                remainder = value & ((40'd1 << shift)-1);
                halfway = 40'd1 << (shift-1);
                rne = quotient + (((remainder > halfway) || ((remainder == halfway) && quotient[0])) ? 40'sd1 : 40'sd0);
            end
        end
    endfunction
    function automatic signed [15:0] sat12;
        input signed [39:0] value;
        begin
            if (value > 2047) sat12 = 16'sd2047;
            else if (value < -2048) sat12 = -16'sd2048;
            else sat12 = value[15:0];
        end
    endfunction
    function automatic signed [15:0] sat16;
        input signed [39:0] value;
        begin
            if (value > 32767) sat16 = 16'sd32767;
            else if (value < -32768) sat16 = -16'sd32768;
            else sat16 = value[15:0];
        end
    endfunction
    function automatic [7:0] relu_quant;
        input signed [39:0] value;
        reg signed [39:0] rounded;
        begin
            rounded = rne(value, HIDDEN_SHIFT);
            if (rounded <= 0) relu_quant = 0;
            else if (rounded > 127) relu_quant = 127;
            else relu_quant = rounded[7:0];
        end
    endfunction
    assign rounded = rne(value, {26'd0,shift});
    assign clipped12 = sat12(value);
    assign clipped16 = sat16(value);
    assign hidden_quantized = relu_quant(value);
endmodule

module quant_serial_kernel (
    input wire clk, rst, start,
    input wire [32:0] in_power,
    input wire [7:0] in_shift,
    input wire [3:0] in_index,
    output wire ready, out_valid,
    output wire [7:0] out_value, stored_value,
    output wire [3:0] out_index, out_kind,
    output wire shifting
);
    // BANDS=3 gives the widest production power_index. Its post-quantization
    // increment is retained, although DFT/power production is outside this cut.
    localparam integer BI_W=$clog2(16*3);
    localparam [4:0] IDLE=0, PRE_MEAN=1, PRE_READ=2, PRE_MUL=3,
        PRE_STORE=4, DFT_INIT=5, DFT_READ=6, DFT_MUL=7, DFT_ACC=8,
        DFT_STORE=9, POWER_RE_MUL=10, POWER_RE_ADD=11,
        POWER_IM_MUL=12, POWER_IM_ADD=13, POWER_Q_INIT=14,
        POWER_Q_SHIFT=15, POWER_QUANT=16, NN_INIT=17, NN_READ=18,
        NN_MUL=19, NN_ACC=20, NN_STORE=21, FINISH=22, HOLD=23;
    reg [4:0] state;
    reg [7:0] feature_shifts [0:15];
    reg [7:0] features [0:15], hidden [0:15];
    reg [3:0] feature_index;
    reg [BI_W-1:0] power_index;
    reg [32:0] power_sum, quant_work;
    reg [7:0] quant_remaining;
    reg quant_guard, quant_sticky;
    reg nn_layer;
    reg [3:0] nn_group;
    wire [7:0] quant_rounded = {1'b0,quant_work[6:0]} + {7'd0,quant_guard};
    wire [7:0] quant_result = ((|quant_work[32:7]) || quant_rounded[7]) ? 8'd127 : quant_rounded;
    reg dbg_valid;
    reg [3:0] dbg_kind;
    reg [15:0] dbg_index;
    reg signed [39:0] dbg_value;
    assign ready = !rst && state == IDLE;
    assign out_valid = dbg_valid;
    assign out_value = dbg_value[7:0];
    assign stored_value = features[dbg_index[3:0]];
    assign out_index = dbg_index[3:0];
    assign out_kind = dbg_kind;
    assign shifting = state == POWER_Q_SHIFT;
    always @(posedge clk) begin
        if (rst) begin
            state<=IDLE; feature_index<=0; power_index<=0; power_sum<=0;
            nn_layer<=0; nn_group<=0;
            dbg_valid<=0; dbg_kind<=0; dbg_index<=0; dbg_value<=0;
            quant_work<=0; quant_remaining<=0; quant_guard<=0; quant_sticky<=0;
        end else begin
            dbg_valid<=0;
            case (state)
                IDLE: if (start) begin
                    power_sum<=in_power;
                    feature_shifts[in_index]<=in_shift;
                    feature_index<=in_index;
                    state<=POWER_Q_INIT;
                end
                POWER_Q_INIT: begin
                    quant_work<=power_sum; quant_remaining<=feature_shifts[feature_index];
                    quant_guard<=0; quant_sticky<=0;
                    if (feature_shifts[feature_index] == 0) state<=POWER_QUANT;
                    else if (feature_shifts[feature_index] > 33) begin quant_work<=0; state<=POWER_QUANT; end
                    else state<=POWER_Q_SHIFT;
                end
                POWER_Q_SHIFT: begin
                    quant_sticky<=quant_sticky | quant_guard;
                    quant_guard<=quant_work[0];
                    quant_work<={1'b0,quant_work[32:1]};
                    quant_remaining<=quant_remaining-1;
                    if (quant_remaining == 1) state<=POWER_QUANT;
                end
                POWER_QUANT: begin
                    features[feature_index]<=quant_result;
                    dbg_valid<=1; dbg_kind<=5; dbg_index<={12'd0,feature_index}; dbg_value<=$signed({32'd0,quant_result});
                    if (feature_index == 15) begin nn_layer<=0; nn_group<=0; state<=NN_INIT; end
                    else begin feature_index<=feature_index+1; power_index<=power_index+1; state<=POWER_RE_MUL; end
                end

                // The real successor is NN_INIT or POWER_RE_MUL. This cut
                // returns to IDLE after observing the completed feature write.
                default: state<=IDLE;
            endcase
        end
    end
endmodule
