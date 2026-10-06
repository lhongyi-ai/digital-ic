// Fixed-point, frame-oriented vibration classifier. No processor is required.
// A multiplier bank is time-shared by Hann, selected-bin DFT, power and MLP.
module vibration_core #(
    parameter integer N = 1024,
    parameter integer LANES = 4,
    parameter integer BANDS = 1,
    parameter MODEL_DIR = "artifacts/model",
    parameter integer HIDDEN_SHIFT = 7
) (
    input wire clk,
    input wire rst,
    input wire in_valid,
    output wire in_ready,
    input wire signed [15:0] in_sample,
    input wire [31:0] in_frame_id,
    input wire in_last,
    output reg out_valid,
    input wire out_ready,
    output reg [31:0] out_frame_id,
    output reg [95:0] out_logits,
    output reg [1:0] out_class,
    output reg [7:0] out_error,
    output reg [31:0] cycles_pre,
    output reg [31:0] cycles_dft,
    output reg [31:0] cycles_power,
    output reg [31:0] cycles_nn,
    output reg [31:0] cycles_total,
    output reg [31:0] protocol_errors,
    // Passive diagnostics: kind 0 mean, 1 windowed, 2 real, 3 imag,
    // 4 power, 5 feature, 6 hidden activation, 7 logit. Signed 40-bit value.
    output reg dbg_valid,
    output reg [3:0] dbg_kind,
    output reg [15:0] dbg_index,
    output reg signed [39:0] dbg_value
);
    localparam integer P = $clog2(N);
    localparam integer TOTAL_BINS = 16*BANDS;
    localparam integer COMPONENTS = 2*TOTAL_BINS;
    localparam integer CW = $clog2(COMPONENTS);
    localparam integer BI_W = $clog2(TOTAL_BINS);
    localparam integer LB = LANES == 1 ? 1 : $clog2(LANES);
    localparam integer SUM_W = 16+P;
    localparam integer W1_WORDS = (16/LANES)*16;
    localparam integer W2_GROUPS = (3+LANES-1)/LANES;
    localparam integer WEIGHT_WORDS = W1_WORDS+W2_GROUPS*16;
    localparam integer WA = $clog2(WEIGHT_WORDS);
    localparam integer PRE_MAX = 3*N+1;
    localparam integer DFT_MAX = (COMPONENTS/LANES)*(3*N+LANES+1);
    localparam integer NN_MAX = (16/LANES+W2_GROUPS)*(49+LANES);
    localparam integer POWER_MAX = 16*(4*BANDS+2+33);
    localparam integer POWER_W = $clog2(POWER_MAX+1);
    localparam integer TOTAL_MAX = PRE_MAX+DFT_MAX+POWER_MAX+NN_MAX;
    localparam integer PRE_W = $clog2(PRE_MAX+1);
    localparam integer DFT_W = $clog2(DFT_MAX+1);
    localparam integer NN_W = $clog2(NN_MAX+1);
    localparam integer TOTAL_W = $clog2(TOTAL_MAX+1);

    localparam [4:0] IDLE=0, PRE_MEAN=1, PRE_READ=2, PRE_MUL=3,
        PRE_STORE=4, DFT_INIT=5, DFT_READ=6, DFT_MUL=7, DFT_ACC=8,
        DFT_STORE=9, POWER_RE_MUL=10, POWER_RE_ADD=11,
        POWER_IM_MUL=12, POWER_IM_ADD=13, POWER_Q_INIT=14,
        POWER_Q_SHIFT=15, POWER_QUANT=16, NN_INIT=17, NN_READ=18,
        NN_MUL=19, NN_ACC=20, NN_STORE=21, FINISH=22, HOLD=23;
    reg [4:0] state;

    (* ram_style = "block" *) reg signed [15:0] raw0 [0:N-1];
    (* ram_style = "block" *) reg signed [15:0] raw1 [0:N-1];
    (* ram_style = "block" *) reg signed [15:0] windowed [0:N-1];
    reg [15:0] frequency_bins [0:TOTAL_BINS-1];
    reg [7:0] feature_shifts [0:15];
    reg signed [31:0] bias1 [0:15];
    reg signed [31:0] bias2 [0:2];
    initial begin
        $readmemh({MODEL_DIR, "/feature_shifts.hex"}, feature_shifts);
        $readmemh({MODEL_DIR, "/b1.hex"}, bias1);
        $readmemh({MODEL_DIR, "/b2.hex"}, bias2);
    end

    generate if (BANDS == 3) begin: g_neighbor_bins
        initial $readmemh({MODEL_DIR, "/dft_bins.hex"}, frequency_bins);
    end else begin: g_single_bins
        initial $readmemh({MODEL_DIR, "/bins.hex"}, frequency_bins);
    end endgenerate
    reg [1:0] full, busy;
    reg write_bank, read_bank, active_bank;
    reg receiving, draining;
    reg [P-1:0] input_index;
    reg [31:0] receiving_id, frame_ids [0:1];
    reg signed [SUM_W-1:0] input_sum, frame_sums [0:1];
    wire restart_input = !receiving || in_frame_id != receiving_id;
    wire signed [SUM_W-1:0] extended_sample = {{(SUM_W-16){in_sample[15]}}, in_sample};
    assign in_ready = !rst && (receiving || (!full[write_bank] && !busy[write_bank]));

    reg [31:0] active_id;
    reg [P-1:0] point;
    reg signed [15:0] mean, raw_q, sample_q;
    wire signed [15:0] hann_q;
    reg [CW-1:0] dft_group;
    reg [LB-1:0] store_lane;
    reg [P-1:0] phase [0:LANES-1];
    wire signed [15:0] coefficient [0:LANES-1];
    reg signed [39:0] accumulator [0:LANES-1];
    reg signed [15:0] real_part [0:TOTAL_BINS-1], imag_part [0:TOTAL_BINS-1];
    reg [7:0] features [0:15], hidden [0:15];
    reg [3:0] feature_index;
    reg [BI_W-1:0] power_index;
    reg [1:0] band_part;
    reg [32:0] band_sum;
    wire [32:0] one_bin_power = power_sum + {1'b0,product[0]};
    wire [33:0] band_sum_next = {1'b0,band_sum}+{1'b0,one_bin_power};
    reg [32:0] power_sum, quant_work;
    reg [7:0] quant_remaining;
    reg quant_guard, quant_sticky;
    wire [7:0] quant_rounded = {1'b0,quant_work[6:0]} + {7'd0,(quant_guard && (quant_sticky || quant_work[0]))};
    wire [7:0] quant_result = ((|quant_work[32:7]) || quant_rounded[7]) ? 8'd127 : quant_rounded;
    reg nn_layer;
    reg [3:0] nn_group;
    reg [3:0] nn_input;
    reg [7:0] activation_q;
    reg signed [31:0] logits [0:2];
    reg [7:0] arithmetic_errors;
    reg [PRE_W-1:0] count_pre;
    reg [DFT_W-1:0] count_dft;
    reg [POWER_W-1:0] count_power;
    reg [NN_W-1:0] count_nn;
    reg [TOTAL_W-1:0] count_total;

    reg signed [15:0] operand_a [0:LANES-1], operand_b [0:LANES-1];
    reg signed [31:0] product [0:LANES-1];
    reg multiply_enable;
    wire [WA-1:0] weight_address = WA'(nn_layer ? W1_WORDS + int'(nn_group)/LANES*16 + int'(nn_input) : int'(nn_group)/LANES*16 + int'(nn_input));
    wire [CW-1:0] dft_component = dft_group + CW'(store_lane);
    wire [BI_W-1:0] dft_bin_index = dft_component[CW-1:1];
    wire [3:0] nn_output_index = nn_group + 4'(store_lane);
    wire signed [39:0] selected_accumulator = accumulator[LANES == 1 ? 0 : store_lane];
    wire signed [7:0] weight_q [0:LANES-1];

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
    function automatic [7:0] power_quant;
        input [32:0] value;
        input [7:0] shift;
        reg [32:0] quotient, remainder, halfway;
        reg [33:0] rounded;
        begin
            quotient = 0; remainder = 0; halfway = 0; rounded = 0;
            if (shift == 0) rounded = {1'b0,value};
            else if (shift <= 33) begin
                quotient = value >> shift;
                remainder = value & ((33'd1 << shift)-1);
                halfway = 33'd1 << (shift-1);
                rounded = {1'b0,quotient} + (((remainder > halfway) || ((remainder == halfway) && quotient[0])) ? 34'd1 : 34'd0);
            end
            power_quant = rounded > 127 ? 8'd127 : rounded[7:0];
        end
    endfunction

    vib_coeff_rom #(.N(N), .MODEL_DIR(MODEL_DIR), .HANN(1)) hann_rom (
        .clk(clk), .en(state == PRE_READ), .phase(point), .coefficient(hann_q)
    );
    genvar lane;
    generate for (lane=0; lane<LANES; lane=lane+1) begin: g_lane
        vib_coeff_rom #(.N(N), .MODEL_DIR(MODEL_DIR)) coeff_rom (
            .clk(clk), .en(state == DFT_READ), .phase(phase[lane]),
            .coefficient(coefficient[lane])
        );
        (* ram_style = "block" *) reg signed [7:0] weights [0:WEIGHT_WORDS-1];
        localparam BANK_FILE = LANES == 1 ? "/weights_l1_0.hex" :
                                   lane == 0 ? "/weights_l4_0.hex" :
                                   lane == 1 ? "/weights_l4_1.hex" :
                                   lane == 2 ? "/weights_l4_2.hex" : "/weights_l4_3.hex";
        reg signed [7:0] selected_weight;
        initial $readmemh({MODEL_DIR, BANK_FILE}, weights);
        always @(posedge clk) begin
            if (state == NN_READ) selected_weight <= weights[weight_address];
            // The only multiplication expression in each lane.
            if (multiply_enable) product[lane] <= operand_a[lane] * operand_b[lane];
        end
        assign weight_q[lane] = selected_weight;
    end endgenerate

    integer m;
    always @* begin
        multiply_enable = 0;
        for (m=0; m<LANES; m=m+1) begin operand_a[m]=0; operand_b[m]=0; end
        case (state)
            PRE_MUL: begin
                multiply_enable=1;
                operand_a[0]=sat12(rne($signed({{24{raw_q[15]}},raw_q})-$signed({{24{mean[15]}},mean}),5));
                operand_b[0]=hann_q;
            end
            DFT_MUL: begin
                multiply_enable=1;
                for (m=0; m<LANES; m=m+1) begin operand_a[m]=sample_q; operand_b[m]=coefficient[m]; end
            end
            POWER_RE_MUL: begin multiply_enable=1; operand_a[0]=real_part[power_index]; operand_b[0]=real_part[power_index]; end
            POWER_IM_MUL: begin multiply_enable=1; operand_a[0]=imag_part[power_index]; operand_b[0]=imag_part[power_index]; end
            NN_MUL: begin
                multiply_enable=1;
                for (m=0; m<LANES; m=m+1) begin operand_a[m]=$signed({8'd0,activation_q}); operand_b[m]={{8{weight_q[m][7]}},weight_q[m]}; end
            end
            default: begin end
        endcase
    end

    // Dedicated synchronous RAM ports have no reset: reset invalidates ownership.
    always @(posedge clk) begin
        if (!rst && in_valid && in_ready && (restart_input || !draining)) begin
            if (write_bank) raw1[restart_input ? 0 : input_index] <= in_sample;
            else raw0[restart_input ? 0 : input_index] <= in_sample;
        end
        if (state == PRE_READ) begin
            raw_q <= active_bank ? raw1[point] : raw0[point];
        end
        if (state == PRE_STORE) windowed[point] <= sat12(rne({{8{product[0][31]}},product[0]},14));
        if (state == DFT_READ) sample_q <= windowed[point];
    end

    integer k;
    always @(posedge clk) begin
        if (rst) begin
            state<=IDLE; full<=0; busy<=0; write_bank<=0; read_bank<=0;
            active_bank<=0; receiving<=0; draining<=0; input_index<=0;
            receiving_id<=0; input_sum<=0; active_id<=0;
            out_valid<=0; out_frame_id<=0; out_logits<=0; out_class<=0; out_error<=0;
            cycles_pre<=0; cycles_dft<=0; cycles_power<=0; cycles_nn<=0; cycles_total<=0;
            protocol_errors<=0; dbg_valid<=0; dbg_kind<=0; dbg_index<=0; dbg_value<=0;
            point<=0; mean<=0; dft_group<=0; store_lane<=0; feature_index<=0; power_index<=0; band_part<=0; band_sum<=0;
            power_sum<=0; quant_work<=0; quant_remaining<=0; quant_guard<=0; quant_sticky<=0; nn_layer<=0; nn_group<=0; nn_input<=0; activation_q<=0;
            arithmetic_errors<=0; count_pre<=0; count_dft<=0; count_power<=0; count_nn<=0; count_total<=0;
            for (k=0; k<LANES; k=k+1) begin accumulator[k]<=0; phase[k]<=0; end
            for (k=0; k<3; k=k+1) logits[k]<=0;
        end else begin
            dbg_valid<=0;
            if (in_valid && in_ready) begin
                if (restart_input) begin
                    if (receiving) protocol_errors<=protocol_errors+1;
                    receiving_id<=in_frame_id; input_sum<=extended_sample;
                    input_index<=1; draining<=0;
                    if (in_last) begin
                        receiving<=0; protocol_errors<=protocol_errors+1;
                    end else receiving<=1;
                end else if (draining) begin
                    if (in_last) begin receiving<=0; draining<=0; end
                end else begin
                    input_sum<=input_sum+extended_sample;
                    if (in_last) begin
                        receiving<=0;
                        if (input_index == P'(N-1)) begin
                            full[write_bank]<=1; frame_ids[write_bank]<=receiving_id;
                            frame_sums[write_bank]<=input_sum+extended_sample;
                            write_bank<=!write_bank;
                        end else protocol_errors<=protocol_errors+1;
                    end else if (input_index == P'(N-1)) begin
                        draining<=1; protocol_errors<=protocol_errors+1;
                    end else input_index<=input_index+1;
                end
            end

            if (state >= PRE_MEAN && state <= PRE_STORE) count_pre<=count_pre+1;
            if (state >= DFT_INIT && state <= DFT_STORE) count_dft<=count_dft+1;
            if (state >= POWER_RE_MUL && state <= POWER_QUANT) count_power<=count_power+1;
            if (state >= NN_INIT && state <= NN_STORE) count_nn<=count_nn+1;
            if (state != IDLE && state != HOLD && state != FINISH) count_total<=count_total+1;

            case (state)
                IDLE: if (full[read_bank]) begin
                    active_bank<=read_bank; active_id<=frame_ids[read_bank];
                    full[read_bank]<=0; busy[read_bank]<=1; read_bank<=!read_bank;
                    point<=0; arithmetic_errors<=0;
                    count_pre<=0; count_dft<=0; count_power<=0; count_nn<=0; count_total<=0;
                    state<=PRE_MEAN;
                end
                PRE_MEAN: begin
                    mean<=16'(rne({{(40-SUM_W){frame_sums[active_bank][SUM_W-1]}},frame_sums[active_bank]},P));
                    dbg_valid<=1; dbg_kind<=0; dbg_index<=0; dbg_value<=40'(rne({{(40-SUM_W){frame_sums[active_bank][SUM_W-1]}},frame_sums[active_bank]},P));
                    state<=PRE_READ;
                end
                PRE_READ: state<=PRE_MUL;
                PRE_MUL: state<=PRE_STORE;
                PRE_STORE: begin
                    dbg_valid<=1; dbg_kind<=1; dbg_index<=16'(point); dbg_value<=40'(sat12(rne({{8{product[0][31]}},product[0]},14)));
                    if (point == P'(N-1)) begin busy[active_bank]<=0; point<=0; dft_group<=0; state<=DFT_INIT; end
                    else begin point<=point+1; state<=PRE_READ; end
                end
                DFT_INIT: begin
                    point<=0;
                    for (k=0; k<LANES; k=k+1) begin accumulator[k]<=0; phase[k]<=((int'(dft_group)+k)%2 == 1) ? P'(N/4) : P'(0); end
                    state<=DFT_READ;
                end
                DFT_READ: state<=DFT_MUL;
                DFT_MUL: state<=DFT_ACC;
                DFT_ACC: begin
                    for (k=0; k<LANES; k=k+1) begin
                        accumulator[k]<=accumulator[k]+$signed({{8{product[k][31]}},product[k]});
                        phase[k]<=phase[k]+P'(frequency_bins[(int'(dft_group)+k)>>1]);
                    end
                    if (point == P'(N-1)) begin store_lane<=0; state<=DFT_STORE; end
                    else begin point<=point+1; state<=DFT_READ; end
                end
                DFT_STORE: begin
                    if (dft_component[0]) imag_part[dft_bin_index]<=sat16(rne(selected_accumulator,P+10));
                    else real_part[dft_bin_index]<=sat16(rne(selected_accumulator,P+10));
                    dbg_valid<=1; dbg_kind<=dft_component[0] ? 3 : 2;
                    dbg_index<=16'(dft_bin_index); dbg_value<=40'(sat16(rne(selected_accumulator,P+10)));
                    if (store_lane == LB'(LANES-1)) begin
                        if (int'(dft_group)+LANES == COMPONENTS) begin feature_index<=0; power_index<=0; band_part<=0; band_sum<=0; state<=POWER_RE_MUL; end
                        else begin dft_group<=dft_group+CW'(LANES); state<=DFT_INIT; end
                    end else store_lane<=store_lane+1;
                end
                POWER_RE_MUL: state<=POWER_RE_ADD;
                POWER_RE_ADD: begin power_sum<={1'b0,product[0]}; state<=POWER_IM_MUL; end
                POWER_IM_MUL: state<=POWER_IM_ADD;
                POWER_IM_ADD: begin
                    if (BANDS == 1 || band_part == 2'(BANDS-1)) begin
                        power_sum<=band_sum_next[32:0];
                        dbg_valid<=1; dbg_kind<=4; dbg_index<={12'd0,feature_index};
                        dbg_value<=$signed({6'd0,band_sum_next});
                        band_sum<=0; band_part<=0; state<=POWER_Q_INIT;
                    end else begin
                        band_sum<=band_sum_next[32:0]; band_part<=band_part+1;
                        power_index<=power_index+1; state<=POWER_RE_MUL;
                    end
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
                NN_INIT: begin
                    nn_input<=0;
                    for (k=0; k<LANES; k=k+1) begin
                        if (!nn_layer) accumulator[k]<=40'(bias1[int'(nn_group)+k]);
                        else if (int'(nn_group)+k < 3) accumulator[k]<=40'(bias2[int'(nn_group)+k]);
                        else accumulator[k]<=0;
                    end
                    state<=NN_READ;
                end
                NN_READ: begin activation_q<=nn_layer ? hidden[nn_input] : features[nn_input]; state<=NN_MUL; end
                NN_MUL: state<=NN_ACC;
                NN_ACC: begin
                    for (k=0; k<LANES; k=k+1) accumulator[k]<=accumulator[k]+$signed({{8{product[k][31]}},product[k]});
                    if (nn_input == 15) begin store_lane<=0; state<=NN_STORE; end
                    else begin nn_input<=nn_input+1; state<=NN_READ; end
                end
                NN_STORE: begin
                    if (selected_accumulator > 40'sd2147483647 || selected_accumulator < -40'sd2147483648) arithmetic_errors[0]<=1;
                    if (!nn_layer) begin
                        hidden[nn_output_index]<=relu_quant(selected_accumulator);
                        dbg_valid<=1; dbg_kind<=6; dbg_index<={12'd0,nn_output_index};
                        dbg_value<=$signed({32'd0,relu_quant(selected_accumulator)});
                    end else if (nn_output_index < 4'd3) begin
                        logits[nn_output_index[1:0]]<=selected_accumulator[31:0];
                        dbg_valid<=1; dbg_kind<=7; dbg_index<={12'd0,nn_output_index}; dbg_value<=selected_accumulator;
                    end
                    if (store_lane == LB'(LANES-1)) begin
                        if (!nn_layer && int'(nn_group)+LANES == 16) begin nn_layer<=1; nn_group<=0; state<=NN_INIT; end
                        else if (nn_layer && int'(nn_group)+LANES >= 3) state<=FINISH;
                        else begin nn_group<=nn_group+4'(LANES); state<=NN_INIT; end
                    end else store_lane<=store_lane+1;
                end
                FINISH: begin
                    out_valid<=1; out_frame_id<=active_id; out_logits<={logits[2],logits[1],logits[0]}; out_error<=arithmetic_errors;
                    if (logits[0]>=logits[1] && logits[0]>=logits[2]) out_class<=0;
                    else if (logits[1]>=logits[2]) out_class<=1; else out_class<=2;
                    cycles_pre<=32'(count_pre); cycles_dft<=32'(count_dft); cycles_power<=32'(count_power); cycles_nn<=32'(count_nn); cycles_total<=32'(count_total);
                    state<=HOLD;
                end
                HOLD: if (out_valid && out_ready) begin out_valid<=0; state<=IDLE; end
                default: state<=IDLE;
            endcase
        end
    end
`ifdef VIB_ASSERT
    initial begin
        assert (N >= 8 && (N & (N-1)) == 0);
        assert (LANES == 1 || LANES == 4);
        assert (BANDS == 1 || BANDS == 3);
    end
    always @(posedge clk) if (!rst) begin
        assert ((full & busy) == 0);
        if (in_valid && in_ready && (restart_input || !draining))
            assert (!full[write_bank] && !busy[write_bank]);
        if (state == PRE_READ) assert (busy[active_bank]);
        if (state == DFT_STORE) assert (int'(dft_group)+int'(store_lane) < COMPONENTS && int'(store_lane) < LANES);
        if (state == NN_READ) assert (int'(weight_address) < WEIGHT_WORDS);
        if (state == POWER_IM_ADD) assert (!band_sum_next[33]);
    end
    assert property (@(posedge clk) disable iff (rst)
        out_valid && !out_ready |=> out_valid && $stable({out_frame_id,
        out_logits,out_class,out_error,cycles_pre,cycles_dft,cycles_power,
        cycles_nn,cycles_total}));
`endif
endmodule
