// One complete recording per boot. The host batches recordings across boots.
// Streaming PCM has a fixed cadence independent of core_ready. A missed sample
// aborts with an explicit error; it is never hidden by slowing the source.
module known_replay_controller #(
    parameter integer N=1024, WINDOWS=156, LANES=4,
    parameter [255:0] MODEL_HASH=0,
    parameter signed [31:0] THRESHOLD=0,
    parameter integer TAIL_TIMEOUT=2400000
)(input wire clk,rst,
   output reg cmd_valid,cmd_write,output reg [23:0] cmd_address,
   output reg [15:0] cmd_length,input wire cmd_ready,
   input wire rd_valid,input wire [7:0] rd_data,output reg rd_ready,
   output reg wr_valid,output reg [7:0] wr_data,input wire wr_ready,
   input wire flash_done,flash_error,
   output wire in_valid,input wire in_ready,output wire signed [15:0] in_sample,
   output wire [31:0] in_frame_id,output wire in_last,
   input wire out_valid,input wire signed [31:0] out_score,
   input wire [31:0] out_frame_id,input wire out_class,input wire [7:0] out_error,
   input wire [31:0] cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total,
   input wire [31:0] protocol_errors,accepted_samples,
   output wire status_done,status_error,status_running);
    localparam integer SAMPLES=N*WINDOWS, BYTES=2*SAMPLES, P=$clog2(N),SW=$clog2(SAMPLES+1);
    localparam SCAN=0,SCAN_WAIT=1,HEADER=2,HEADER_WAIT=3,CHECK=4,
        LOAD=5,LOAD_WAIT=6,DRAIN=7,LOG_CMD=8,LOG_DATA=9,LOG_WAIT=10,
        COMMIT_CMD=11,COMMIT_DATA=12,COMMIT_WAIT=13,HALT=14;
    reg [3:0] state;
    reg [7:0] errors;
    reg blank,committed,active;
    reg [13:0] period,phase;
    // Header assembly storage becomes the completed payload CRC after loading.
    // The same CRC datapath then protects the result log.
    reg [31:0] header_word,expected_crc,crc;
    reg [18:0] loaded;
    reg [SW-1:0] generated;
    reg [7:0] byte_index,low_byte;
    // Supported periods 4..12000 and <=159744 samples finish within 2^31
    // clocks, including transport startup and the bounded processing tail.
    reg [30:0] tick,first_tick,last_tick,result_tick;
    localparam TW=$clog2(TAIL_TIMEOUT+1);
    reg [TW-1:0] tail;
    reg result_seen;
    (* ram_style="block" *) reg [15:0] queue[0:255];
    reg [7:0] wp,rp;
    reg [8:0] level,max_level;
    reg [15:0] sample_q;
    wire due=active&&phase==0;
    wire receiving=state==LOAD_WAIT&&!errors;
    wire push=receiving&&rd_valid&&rd_ready&&loaded[0];
    wire pop=due&&level!=0;
    assign in_valid=pop&&!errors&&!rst;
    assign in_sample=sample_q;
    assign in_frame_id=32'(generated>>P);
    assign in_last=generated[P-1:0]==N-1;
    assign status_done=state==HALT&&committed;
    assign status_error=|errors;
    assign status_running=active||state==DRAIN;
    always @(posedge clk) begin
        if(push) queue[wp]<={rd_data,low_byte};
        sample_q<=queue[rp];
    end
    function automatic [31:0] crc_byte(input [31:0] prior,input [7:0] data);
        reg [31:0] c;integer i;
        begin c=prior^{24'd0,data};for(i=0;i<8;i=i+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;crc_byte=c;end
    endfunction
    wire [31:0] received_word={rd_data,header_word[31:8]};
    reg [31:0] log_word;
    always @* begin
        log_word=0;
        case(byte_index[7:2])
            0:log_word=32'h314c534b; // KSL1
            1:log_word=1;2:log_word=N;3:log_word=WINDOWS;4:log_word=LANES;
            5:log_word=32'(period);6:log_word=32'(generated);
            7:log_word=accepted_samples;8:log_word={24'd0,errors};9:log_word=protocol_errors;
            10:log_word=errors?0:out_score;11:log_word=THRESHOLD;
            12:log_word=errors?0:{31'd0,out_class};13:log_word=errors?0:{24'd0,out_error};
            14:log_word=errors?0:out_frame_id;
            15:log_word=errors?0:cycles_pre;16:log_word=errors?0:cycles_dft;
            17:log_word=errors?0:cycles_power;18:log_word=errors?0:cycles_nn;
            19:log_word=errors?0:cycles_total;
            20:log_word=first_tick;21:log_word=last_tick;22:log_word=result_tick;
            23:log_word=expected_crc;24:log_word=(|errors[1:0])?0:header_word;25:log_word={23'd0,max_level};
            32,33,34,35,36,37,38,39:log_word=MODEL_HASH[(byte_index[7:2]-32)*32+:32];
            62:log_word=~crc;
            default:log_word=0;
        endcase
        cmd_valid=0;cmd_write=0;cmd_address=0;cmd_length=0;
        rd_ready=1;wr_valid=0;wr_data=0;
        case(state)
            SCAN:begin cmd_valid=1;cmd_address=24'h300000;cmd_length=4096;end
            HEADER:begin cmd_valid=1;cmd_address=24'h100000;cmd_length=64;end
            LOAD:begin cmd_valid=1;cmd_address=24'h100040+24'(loaded);
                cmd_length=(BYTES-loaded>1024)?16'd1024:16'(BYTES-loaded);end
            LOAD_WAIT:rd_ready=errors||!loaded[0]||level<256;
            LOG_CMD:begin cmd_valid=1;cmd_write=1;cmd_address=24'h300000;cmd_length=252;end
            LOG_DATA:begin wr_valid=1;wr_data=log_word[byte_index[1:0]*8+:8];end
            COMMIT_CMD:begin cmd_valid=1;cmd_write=1;cmd_address=24'h3000fc;cmd_length=4;end
            COMMIT_DATA:begin wr_valid=1;wr_data=8'(32'hc04d17ed>>(byte_index[1:0]*8));end
            default:begin end
        endcase
    end
    always @(posedge clk) begin
        if(rst)begin
            state<=SCAN;errors<=0;blank<=1;committed<=0;active<=0;
            period<=0;phase<=0;header_word<=0;expected_crc<=0;crc<=32'hffffffff;
            loaded<=0;generated<=0;byte_index<=0;low_byte<=0;
            tick<=0;first_tick<=0;last_tick<=0;result_tick<=0;tail<=0;result_seen<=0;
            wp<=0;rp<=0;level<=0;max_level<=0;
        end else begin
            tick<=tick+1'b1;
            case({push,pop})
                2'b10:level<=level+1'b1;
                2'b01:level<=level-1'b1;
                default:begin end
            endcase
            if(push)wp<=wp+1'b1;
            if(pop)rp<=rp+1'b1;
            if(level>max_level)max_level<=level;
            // A two-cycle gap after prefill permits the synchronous RAM read.
            if(!active&&generated==0&&!errors&&(state==LOAD||state==LOAD_WAIT)&&level>=32)begin
                active<=1;phase<=2;
            end
            if(active)begin
                if(phase==0)begin
                    generated<=generated+1'b1;phase<=period-1'b1;
                    if(generated==0)first_tick<=tick;
                    if(generated==SAMPLES-1)begin active<=0;last_tick<=tick;end
                    if(!level)begin errors[3]<=1;active<=0;end
                    else if(!in_ready)begin errors[4]<=1;active<=0;end
                end else phase<=phase-1'b1;
                if(errors)active<=0;
            end
            if(out_valid&&!result_seen&&!errors)begin result_seen<=1;result_tick<=tick;end
            case(state)
                SCAN:if(cmd_valid&&cmd_ready)state<=SCAN_WAIT;
                SCAN_WAIT:begin
                    if(rd_valid&&rd_ready&&rd_data!=8'hff)blank<=0;
                    if(flash_done)begin
                        if(flash_error||!blank)begin errors[5]<=1;state<=HALT;end
                        else begin state<=HEADER;byte_index<=0;end
                    end
                end
                HEADER:if(cmd_valid&&cmd_ready)state<=HEADER_WAIT;
                HEADER_WAIT:begin
                    if(rd_valid&&rd_ready)begin
                        header_word<=received_word;byte_index<=byte_index+1'b1;
                        if(byte_index<32&&byte_index[1:0]==3)case(byte_index[4:2])
                            0:if(received_word!=32'h3152534b)errors[0]<=1; // KSR1
                            1:if(received_word!=1)errors[0]<=1;
                            2:if(received_word!=N)errors[0]<=1;
                            3:if(received_word!=WINDOWS)errors[0]<=1;
                            4:begin period<=received_word[13:0];
                                if(received_word<4||received_word>12000)errors[0]<=1;end
                            5:if(received_word!=BYTES)errors[0]<=1;
                            6:expected_crc<=received_word;
                            7:if(received_word!=0)errors[0]<=1;
                        endcase
                        if(byte_index>=32&&rd_data!=MODEL_HASH[(byte_index-32)*8+:8])errors[1]<=1;
                    end
                    if(flash_done)begin if(flash_error)errors[5]<=1;state<=CHECK;end
                end
                CHECK:state<=errors?LOG_CMD:LOAD;
                LOAD:begin
                    if(errors)state<=DRAIN;
                    else if(cmd_valid&&cmd_ready)state<=LOAD_WAIT;
                end
                LOAD_WAIT:begin
                    if(rd_valid&&rd_ready&&!errors)begin
                        if(!loaded[0])low_byte<=rd_data;
                        loaded<=loaded+1'b1;
                    end
                    if(flash_done)begin
                        if(flash_error)errors[5]<=1;
                        state<=(errors||flash_error||loaded==BYTES)?DRAIN:LOAD;
                    end
                end
                DRAIN:begin
                    header_word<=~crc;
                    if(errors)begin active<=0;state<=LOG_CMD;end
                    else if(loaded==BYTES&&~crc!=expected_crc)begin errors[2]<=1;active<=0;end
                    else if(result_seen)begin
                        if(out_error||protocol_errors||accepted_samples!=SAMPLES||generated!=SAMPLES)errors[7]<=1;
                        state<=LOG_CMD;
                    end else if(generated==SAMPLES)begin
                        if(tail==TAIL_TIMEOUT-1)errors[6]<=1;else tail<=tail+1'b1;
                    end
                end
                LOG_CMD:if(cmd_valid&&cmd_ready)begin byte_index<=0;crc<=32'hffffffff;state<=LOG_DATA;end
                LOG_DATA:if(wr_valid&&wr_ready)begin
                    byte_index<=byte_index+1'b1;if(byte_index==251)state<=LOG_WAIT;
                end
                LOG_WAIT:if(flash_done)begin
                    if(flash_error)begin errors[5]<=1;state<=HALT;end else state<=COMMIT_CMD;
                end
                COMMIT_CMD:if(cmd_valid&&cmd_ready)begin byte_index<=0;state<=COMMIT_DATA;end
                COMMIT_DATA:if(wr_valid&&wr_ready)begin byte_index<=byte_index+1'b1;if(byte_index==3)state<=COMMIT_WAIT;end
                COMMIT_WAIT:if(flash_done)begin committed<=!flash_error;if(flash_error)errors[5]<=1;state<=HALT;end
                default:begin end
            endcase
            if((receiving&&rd_valid&&rd_ready)||(state==LOG_DATA&&wr_valid&&wr_ready&&byte_index<248))
                crc<=crc_byte(crc,state==LOG_DATA?wr_data:rd_data);
        end
    end
`ifdef VIB_ASSERT
    initial assert(SAMPLES<=159744);
    always @(posedge clk)if(!rst)begin
        assert(level<=256);assert(!push||level<256);assert(generated<=SAMPLES);
        if(cmd_valid&&cmd_write)assert(cmd_address==24'h300000||cmd_address==24'h3000fc);
    end
`endif
endmodule
