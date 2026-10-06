// Complete raw-PCM -> full spectrum -> clip-average power -> INT8 linear score.
// The same LANES signed16 multipliers serve every arithmetic stage.
module known_spectral_core #(
    parameter integer N=1024,LANES=4,WINDOWS=156,
    parameter MODEL_DIR="artifacts/acoustic-known-release-v1/id00",
    parameter signed [31:0] BIAS=0,THRESHOLD=0,
    parameter signed [31:0] LOG_CONSTANT=128145,LOG_FLOOR=-163279
)(input wire clk,rst,input wire in_valid,output wire in_ready,
   input wire signed [15:0] in_sample,input wire [31:0] in_frame_id,input wire in_last,
   output reg out_valid,input wire out_ready,output reg signed [31:0] out_score,
   output reg [31:0] out_frame_id,output reg out_class,output reg [7:0] out_error,
   output reg [31:0] cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total,
   output wire [31:0] protocol_errors,accepted_samples,
   output reg dbg_valid,output reg [3:0] dbg_kind,output reg [31:0] dbg_frame,
   output reg [15:0] dbg_index,output reg signed [63:0] dbg_value);
    localparam P=$clog2(N),F=N/2,LB=LANES==1?1:$clog2(LANES);
    // Counters cover one clip. Conservative FSM-derived bounds keep the public
    // 32-bit fields while avoiding unused physical counter bits on UP5K.
    localparam PRE_W=$clog2(3*N*WINDOWS+1),
        DFT_W=$clog2((N/LANES)*(N+LANES+3)*WINDOWS+1),
        POWER_W=$clog2(100*F*WINDOWS+1),NN_W=$clog2(128*F+1),
        TOTAL_W=$clog2((2*N*N/LANES+150*N)*WINDOWS+1);
    localparam IDLE=0,PRE_READ=1,PRE_MULT=2,PRE_STORE=3,DFT_INIT=4,DFT_RUN=5,
        DFT_SAVE=6,REAL_INIT=7,WM_PREP=8,WM_ACC=9,P_READ=10,P_CAPTURE=11,
        P_SUM=12,P_WRITE=13,LOG_INIT=14,LOG_SHIFT=15,LOG_LOOKUP=16,LOG_COMPUTE=17,
        NORM_INIT=18,NN_MULT=19,NN_ACC=20,NEXT_COMPONENT=21,FRAME_DONE=22,HOLD=23;
    reg [4:0] state;
    wire window_valid,window_bank;
    wire [31:0] window_id;wire signed [31:0] window_sum;
    wire take=state==IDLE&&window_valid&&!rst;
    reg active_bank;
    wire release_bank=state==PRE_STORE&&point==N-1&&!rst;
    wire signed [15:0] raw_q;
    reg [P-1:0] point;
    known_capture #(.N(N)) capture(.clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),
        .in_sample(in_sample),.in_frame_id(in_frame_id),.in_last(in_last),.window_valid(window_valid),
        .take(take),.window_bank(window_bank),.window_id(window_id),.window_sum(window_sum),
        .release_bank(release_bank),.released_bank(active_bank),.read_enable(state==PRE_READ),
        .read_bank(active_bank),.read_address(point),.read_sample(raw_q),
        .protocol_errors(protocol_errors),.accepted_samples(accepted_samples));

    (* ram_style="block" *) reg signed [15:0] windowed[0:N-1];
    reg signed [15:0] sample_q,mean;
    (* ram_style="block" *) reg signed [31:0] means[0:F-1];
    (* ram_style="block" *) reg [31:0] gains[0:F-1];
    (* ram_style="block" *) reg signed [7:0] weights[0:F-1];
    (* ram_style="block" *) reg [11:0] log_table[0:1023];
    reg signed [31:0] mean_q;reg [31:0] gain_q;reg signed [7:0] weight_q;reg [11:0] log_q;
    initial begin
        $readmemh({MODEL_DIR,"/mean_q12.hex"},means);
        $readmemh({MODEL_DIR,"/gain_q24.hex"},gains);
        $readmemh({MODEL_DIR,"/weights.hex"},weights);
        $readmemh({MODEL_DIR,"/log_lut.hex"},log_table);
    end
    reg [31:0] active_id,clip_id,previous_id;reg previous_valid;
    reg [7:0] clip_window;
    reg signed [31:0] score;
    reg [7:0] arithmetic_error;
    reg [P:0] component_base,issued,retired;
    reg [LB-1:0] lane_store;
    wire [P:0] component=component_base+lane_store;
    reg [P-1:0] phases[0:LANES-1];
    wire signed [15:0] coefficient[0:LANES-1];
    reg signed [15:0] operand_a[0:LANES-1],operand_b[0:LANES-1];
    reg signed [31:0] product[0:LANES-1];
    reg signed [47:0] accumulator[0:LANES-1];
    reg multiply;
    reg valid0,valid1;
    wire issue=state==DFT_RUN && issued<N;
    wire signed [31:0] centered=$signed(raw_q)-$signed(mean);
    wire signed [15:0] centered_clipped=centered>32767?16'sd32767:centered< -32768?-16'sd32768:centered[15:0];
    wire [16:0] hann_difference=17'd32767-{coefficient[0][15],coefficient[0]};
    wire signed [15:0] hann_value=16'((hann_difference>>1)+(hann_difference[0]&&hann_difference[1]));

    function automatic signed [63:0] rne(input signed [63:0] value,input integer shift);
        reg signed [63:0] quotient;reg [63:0] rem,half;
        begin
            quotient=value>>>shift;rem=value&((64'd1<<shift)-1);half=64'd1<<(shift-1);
            rne=quotient+64'((rem>half)||((rem==half)&&quotient[0]));
        end
    endfunction
    wire signed [63:0] rounded_component=rne({{16{accumulator[lane_store][47]}},accumulator[lane_store]},8);
    wire signed [63:0] rounded_window=rne({{32{product[0][31]}},product[0]},15);
    reg signed [31:0] real_part,imag_part;
    reg [P-2:0] bin_index;
    reg [31:0] wide_a;reg [1:0] wide_part,purpose;
    wire [31:0] wide_b=purpose==2?gain_q:wide_a;
    reg [63:0] wide_acc,power_buffer;
    wire [15:0] wide_limb_a=wide_part[0]?wide_a[31:16]:wide_a[15:0];
    wire [15:0] wide_limb_b=wide_part[1]?wide_b[31:16]:wide_b[15:0];
    wire [31:0] unsigned_product=product[0]+(wide_limb_a[15]?{wide_limb_b,16'd0}:32'd0)+
                                                      (wide_limb_b[15]?{wide_limb_a,16'd0}:32'd0);
    wire [63:0] wide_term={32'd0,unsigned_product}<<(wide_part==3?32:wide_part==0?0:16);
    wire [63:0] wide_result=wide_acc+wide_term;
    wire [64:0] power_sum={1'b0,power_buffer}+{1'b0,wide_acc};
    // Keep the real square in the same accumulator while adding the imaginary
    // square. Signed32 components guarantee the sum is <= 2^63.
    wire [63:0] rounded_power=(wide_result>>8)+64'((wide_result[7:0]>128)||((wide_result[7:0]==128)&&wide_result[8]));
    reg norm_negative;reg signed [31:0] difference,log_value;reg signed [7:0] feature;
    // Ties-to-even is odd-symmetric: round the magnitude, clip, then restore
    // sign. Avoid a wide negator without changing any quantized output.
    wire [39:0] rounded_magnitude=wide_result[63:24]+40'((wide_result[23:0]>24'h800000)||
        ((wide_result[23:0]==24'h800000)&&wide_result[24]));
    wire [6:0] feature_magnitude=rounded_magnitude>127?7'd127:rounded_magnitude[6:0];
    wire signed [7:0] quantized_feature=norm_negative?-$signed({1'b0,feature_magnitude}):$signed({1'b0,feature_magnitude});
    reg [1:0] ram_part;
    wire [13:0] ram_address=14'(({23'd0,bin_index}<<2)+ram_part);
    wire [15:0] ram_q;
    spram16k power_ram(.clk(clk),.address(ram_address),.write_enable(state==P_WRITE&&!rst),
        .write_data(16'(power_buffer>>(ram_part*16))),.read_data(ram_q));
    reg [63:0] log_work;reg signed [7:0] exponent;
    wire signed [31:0] computed_log=($signed(exponent)<<<12)+$signed({20'd0,log_q})-LOG_CONSTANT;
    wire signed [31:0] bounded_log=computed_log<LOG_FLOOR?LOG_FLOOR:computed_log;
    genvar g;
    generate for(g=0;g<LANES;g=g+1) begin: lanes
        // Real/imaginary lanes for one bin differ only by a quarter-cycle.
        // Share their phase counter instead of duplicating its state/adder.
        wire [P-1:0] dft_phase;
        if(LANES>1&&(g%2)==1)assign dft_phase=phases[g-1]+P'(N/4);
        else assign dft_phase=phases[g];
        wire [P-1:0] rom_phase=state==PRE_READ?point:dft_phase;
        vib_coeff_rom #(.N(N),.MODEL_DIR(MODEL_DIR)) rom(.clk(clk),.en(issue||(state==PRE_READ&&g==0)),
            .phase(rom_phase),.coefficient(coefficient[g]));
        always @(posedge clk) if(multiply) product[g]<=operand_a[g]*operand_b[g];
    end endgenerate
    integer i;
    always @* begin
        multiply=0;
        for(integer j=0;j<LANES;j=j+1) begin operand_a[j]=0;operand_b[j]=0;end
        case(state)
            PRE_MULT:begin multiply=1;operand_a[0]=centered_clipped;operand_b[0]=hann_value;end
            DFT_RUN:begin
                multiply=valid0;
                for(integer j=0;j<LANES;j=j+1) begin operand_a[j]=sample_q;operand_b[j]=coefficient[j];end
            end
            WM_PREP:begin multiply=1;operand_a[0]=wide_limb_a;operand_b[0]=wide_limb_b;end
            NN_MULT:begin multiply=1;operand_a[0]={{8{feature[7]}},feature};operand_b[0]={{8{weight_q[7]}},weight_q};end
            default:begin end
        endcase
    end
    always @(posedge clk) begin
        if(issue) sample_q<=windowed[issued[P-1:0]];
        if(state==PRE_STORE&&!rst) windowed[point]<=rounded_window[15:0];
        if(state==LOG_LOOKUP) begin
            log_q<=log_table[log_work[9:0]];mean_q<=means[bin_index];gain_q<=gains[bin_index];weight_q<=weights[bin_index];
        end
        if(rst) begin
            state<=IDLE;out_valid<=0;out_score<=0;out_frame_id<=0;out_class<=0;out_error<=0;
            active_bank<=0;active_id<=0;clip_id<=0;previous_id<=0;previous_valid<=0;clip_window<=0;score<=BIAS;
            arithmetic_error<=0;mean<=0;point<=0;component_base<=0;issued<=0;retired<=0;lane_store<=0;
            valid0<=0;valid1<=0;bin_index<=0;wide_part<=0;purpose<=0;
            ram_part<=0;norm_negative<=0;exponent<=0;
            cycles_pre<=0;cycles_dft<=0;cycles_power<=0;cycles_nn<=0;cycles_total<=0;
            dbg_valid<=0;dbg_kind<=0;dbg_frame<=0;dbg_index<=0;dbg_value<=0;
            // Datapath registers are initialized by their issuing state before
            // use (DFT_INIT, REAL_INIT, P_READ/P_WRITE, LOG_INIT, NORM_INIT).
            // Reset cancels control/valid state; it need not fan out to these
            // large internal registers, just as it need not clear the RAMs.
        end else begin
            dbg_valid<=0;
            if(state!=IDLE&&state!=HOLD) begin
                cycles_total<=32'(cycles_total[TOTAL_W-1:0]+TOTAL_W'(1));
                if(state==PRE_READ||state==PRE_MULT||state==PRE_STORE) cycles_pre<=32'(cycles_pre[PRE_W-1:0]+PRE_W'(1));
                else if(state==DFT_INIT||state==DFT_RUN||state==DFT_SAVE) cycles_dft<=32'(cycles_dft[DFT_W-1:0]+DFT_W'(1));
                else if((state>=LOG_INIT&&state<=NN_ACC)||((state==WM_PREP||state==WM_ACC)&&purpose==2)) cycles_nn<=32'(cycles_nn[NN_W-1:0]+NN_W'(1));
                else cycles_power<=32'(cycles_power[POWER_W-1:0]+POWER_W'(1));
            end
            case(state)
                IDLE:if(window_valid) begin
                    active_bank<=window_bank;active_id<=window_id;mean<=16'(rne({{32{window_sum[31]}},window_sum},P));point<=0;
                    if(clip_window==0||(previous_valid&&window_id!=previous_id+1)) begin
                        clip_window<=0;clip_id<=window_id;score<=BIAS;arithmetic_error<=0;
                        cycles_pre<=0;cycles_dft<=0;cycles_power<=0;cycles_nn<=0;cycles_total<=0;
                    end
                    dbg_frame<=window_id;state<=PRE_READ;
                end
                PRE_READ:state<=PRE_MULT;
                PRE_MULT:begin
                    if(centered>32767||centered< -32768) arithmetic_error[0]<=1;
                    state<=PRE_STORE;
                end
                PRE_STORE:begin
                    dbg_valid<=1;dbg_kind<=0;dbg_index<=16'(point);dbg_value<=rounded_window;
                    if(point==N-1) begin component_base<=0;state<=DFT_INIT;end
                    else begin point<=point+1'b1;state<=PRE_READ;end
                end
                DFT_INIT:begin
                    issued<=0;retired<=0;valid0<=0;valid1<=0;
                    for(i=0;i<LANES;i=i+1) begin
                        accumulator[i]<=0;
                        if(LANES==1||(i%2)==0)phases[i]<=((component_base+i)&1)?P'(N/4):P'(0);
                    end
                    state<=DFT_RUN;
                end
                DFT_RUN:begin
                    valid0<=issue;valid1<=valid0;
                    if(issue) begin
                        issued<=issued+1'b1;
                        for(i=0;i<LANES;i=i+1)if(LANES==1||(i%2)==0)phases[i]<=phases[i]+P'(((component_base+i)>>1)+1);
                    end
                    if(valid1) begin
                        for(i=0;i<LANES;i=i+1) accumulator[i]<=accumulator[i]+{{16{product[i][31]}},product[i]};
                        retired<=retired+1'b1;
                        if(retired==N-1) begin lane_store<=0;state<=DFT_SAVE;end
                    end
                end
                DFT_SAVE:begin
                    dbg_valid<=1;dbg_kind<=component[0]?2:1;dbg_index<=16'(component>>1);dbg_value<=rounded_component;
                    if(rounded_component>64'sd2147483647||rounded_component< -64'sd2147483648) arithmetic_error[1]<=1;
                    if(component[0]) begin imag_part<=rounded_component[31:0];bin_index<=(component>>1);state<=REAL_INIT;end
                    else begin real_part<=rounded_component[31:0];state<=NEXT_COMPONENT;end
                end
                REAL_INIT:begin
                    wide_a<=real_part[31]?-$signed(real_part):real_part;
                    wide_part<=0;wide_acc<=0;purpose<=0;state<=WM_PREP;
                end
                WM_PREP:state<=WM_ACC;
                WM_ACC:begin
                    if(wide_part!=3) begin wide_acc<=wide_result;wide_part<=wide_part+1'b1;state<=WM_PREP;end
                    else if(purpose==0) begin
                        wide_a<=imag_part[31]?-$signed(imag_part):imag_part;
                        wide_part<=0;wide_acc<=wide_result;purpose<=1;state<=WM_PREP;
                    end else if(purpose==1) begin
                        wide_acc<=rounded_power;ram_part<=0;
                        dbg_valid<=1;dbg_kind<=3;dbg_index<=16'(bin_index);dbg_value<=$signed(rounded_power);
                        if(clip_window==0) begin power_buffer<=rounded_power;state<=P_WRITE;end
                        else state<=P_READ;
                    end else begin
                        feature<=quantized_feature;
                        dbg_valid<=1;dbg_kind<=6;dbg_index<=16'(bin_index);
                        dbg_value<=64'($signed(quantized_feature));
                        state<=NN_MULT;
                    end
                end
                P_READ:state<=P_CAPTURE;
                P_CAPTURE:begin
                    power_buffer[ram_part*16+:16]<=ram_q;
                    if(ram_part==3) state<=P_SUM;
                    else begin ram_part<=ram_part+1'b1;state<=P_READ;end
                end
                P_SUM:begin
                    if(power_sum[64]) arithmetic_error[2]<=1;
                    power_buffer<=power_sum[63:0];ram_part<=0;state<=P_WRITE;
                end
                P_WRITE:begin
                    if(ram_part==3) begin
                        dbg_valid<=1;dbg_kind<=4;dbg_index<=16'(bin_index);dbg_value<=$signed(power_buffer);
                        state<=clip_window==WINDOWS-1?LOG_INIT:NEXT_COMPONENT;
                    end else ram_part<=ram_part+1'b1;
                end
                LOG_INIT:begin log_work<=power_buffer;exponent<=10;state<=LOG_SHIFT;end
                LOG_SHIFT:begin
                    if(log_work==0) begin log_value<=LOG_FLOOR;state<=LOG_LOOKUP;end
                    else if(log_work>=2048) begin log_work<=log_work>>1;exponent<=exponent+1'b1;end
                    else if(log_work<1024) begin log_work<=log_work<<1;exponent<=exponent-1'b1;end
                    else state<=LOG_LOOKUP;
                end
                LOG_LOOKUP:state<=LOG_COMPUTE;
                LOG_COMPUTE:begin
                    log_value<=log_work==0?LOG_FLOOR:bounded_log;
                    difference<=(log_work==0?LOG_FLOOR:bounded_log)-mean_q;
                    dbg_valid<=1;dbg_kind<=5;dbg_index<=16'(bin_index);dbg_value<=64'($signed(log_work==0?LOG_FLOOR:bounded_log));
                    state<=NORM_INIT;
                end
                NORM_INIT:begin
                    wide_a<=difference[31]?-$signed(difference):difference;norm_negative<=difference[31];
                    purpose<=2;wide_part<=0;wide_acc<=0;state<=WM_PREP;
                end
                NN_MULT:state<=NN_ACC;
                NN_ACC:begin score<=score+product[0];state<=NEXT_COMPONENT;end
                NEXT_COMPONENT:begin
                    if(lane_store!=LANES-1) begin lane_store<=lane_store+1'b1;state<=DFT_SAVE;end
                    else if(component_base+LANES<N) begin component_base<=component_base+LANES;state<=DFT_INIT;end
                    else state<=FRAME_DONE;
                end
                FRAME_DONE:begin
                    previous_id<=active_id;previous_valid<=1;
                    if(clip_window==WINDOWS-1) begin
                        out_valid<=1;out_score<=score;out_class<=score>THRESHOLD;out_error<=arithmetic_error;out_frame_id<=clip_id;
                        dbg_valid<=1;dbg_kind<=7;dbg_index<=0;dbg_value<=64'($signed(score));state<=HOLD;
                    end else begin clip_window<=clip_window+1'b1;state<=IDLE;end
                end
                HOLD:if(out_ready) begin out_valid<=0;clip_window<=0;state<=IDLE;end
                default:state<=IDLE;
            endcase
`ifdef VIB_ASSERT
            assert(LANES==1||LANES==4);
            assert(WINDOWS>=1&&WINDOWS<=255);
            if(state==DFT_RUN) begin assert(issued<=N);assert(retired<=N);end
            if(state!=IDLE&&state!=HOLD) assert(component_base<N);
            if(out_valid) assert(state==HOLD);
`endif
        end
    end
endmodule
