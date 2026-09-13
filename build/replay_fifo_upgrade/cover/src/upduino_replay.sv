// Physical interface wrapper. Uses the externally routed 12 MHz oscillator.
// Reset is a power-up counter; FPGA reconfiguration also restarts the design.
module upduino_replay #(
    parameter integer LANES=4,
    parameter integer BANDS=1,
    parameter MODEL_DIR="artifacts/model",
    parameter integer HIDDEN_SHIFT=8,
    parameter [255:0] MODEL_HASH=0,
    parameter integer STARTUP_CYCLES=120000,
    parameter integer TAIL_TIMEOUT=1200000
)(input wire clk12,input wire flash_miso,
   output wire flash_cs_n,flash_sclk,flash_mosi,
   output wire status_done,status_error,status_running);
    reg [23:0] startup=0;
    wire rst=startup<STARTUP_CYCLES;
    always @(posedge clk12) if(rst) startup<=startup+1'b1;
    replay_system #(.LANES(LANES),.BANDS(BANDS),.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(HIDDEN_SHIFT),
        .MODEL_HASH(MODEL_HASH),.TAIL_TIMEOUT(TAIL_TIMEOUT)) system(
        .clk(clk12),.rst(rst),.flash_miso(flash_miso),.flash_cs_n(flash_cs_n),
        .flash_sclk(flash_sclk),.flash_mosi(flash_mosi),.status_done(status_done),
        .status_error(status_error),.status_running(status_running));
endmodule

module replay_system #(
    parameter integer LANES=4,
    parameter integer BANDS=1,
    parameter MODEL_DIR="artifacts/model",
    parameter integer HIDDEN_SHIFT=8,
    parameter [255:0] MODEL_HASH=0,
    parameter integer TAIL_TIMEOUT=1200000,
    // Four sequential reads cover the full 128 KiB production log partition.
    // Smaller shifts are exclusively for accelerated functional simulation.
    parameter integer LOG_SCAN_CHUNK_SHIFT=15
)(input wire clk,rst,input wire flash_miso,
   output wire flash_cs_n,flash_sclk,flash_mosi,
   output wire status_done,status_error,status_running);
`ifdef VIB_ASSERT
    initial assert(LOG_SCAN_CHUNK_SHIFT>=1 && LOG_SCAN_CHUNK_SHIFT<=15);
`endif
    localparam BOOT_LOG=0,BOOT_LOG_WAIT=1,BOOT_IMAGE=2,BOOT_IMAGE_WAIT=3,
        VALIDATE=4,LOAD=5,LOAD_WAIT=6,START=7,RUN=8,
        WRITE_HEADER=9,WRITE_CMD=10,WRITE_DATA=11,WRITE_WAIT=12,
        WRITE_PREFETCH=13,WRITE_PREFETCH2=14,HALT=15;
    reg [3:0] state;
    reg [7:0] error_flags;
    reg committed, existing_log;
    reg [31:0] header_word;
    reg header_bad,hash_bad;
    reg [15:0] byte_index;
    reg log_blank;
    reg [1:0] log_scan_chunk;
    reg [4:0] source_frames;
    reg [9:0] run_frames;
    reg [15:0] period_cycles;
    reg [31:0] expected_crc,crc;
    reg [15:0] payload_size;
    reg [7:0] low_byte;
    reg load_we;
    reg [13:0] load_address;
    reg [15:0] load_data;

    reg cmd_valid,cmd_write,wr_valid,rd_ready;
    wire cmd_ready,wr_ready,rd_valid,flash_done,flash_error;
    reg [23:0] cmd_address;
    reg [15:0] cmd_length;
    reg [7:0] wr_data;
    wire [7:0] rd_data;
    flash_stream transport(.clk(clk),.rst(rst),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
        .cmd_write(cmd_write),.cmd_address(cmd_address),.cmd_length(cmd_length),
        .wr_valid(wr_valid),.wr_ready(wr_ready),.wr_data(wr_data),
        .rd_valid(rd_valid),.rd_ready(rd_ready),.rd_data(rd_data),
        .done(flash_done),.error(flash_error),.flash_cs_n(flash_cs_n),
        .flash_sclk(flash_sclk),.flash_mosi(flash_mosi),.flash_miso(flash_miso));

    wire source_valid,source_last,source_done;
    wire signed [15:0] source_sample;
    wire [31:0] source_id,generated_samples;
    replay_source source(.clk(clk),.rst(rst),.load_we(load_we),.load_address(load_address),
        .load_data(load_data),.start(state==START),.source_frames(source_frames),
        .run_frames(run_frames),.period_cycles(period_cycles),.sample_valid(source_valid),
        .sample(source_sample),.frame_id(source_id),.sample_last(source_last),
        .finished(source_done),.generated_samples(generated_samples));
    wire fifo_ready,fifo_valid,core_ready;
    wire [48:0] fifo_data;
    wire [1:0] fifo_level;
    replay_fifo input_queue(
        .clk(clk),.rst(rst),.in_valid(source_valid),.in_ready(fifo_ready),
        .in_data({source_id,source_last,source_sample}),.out_valid(fifo_valid),
        .out_ready(core_ready),.out_data(fifo_data),.occupancy(fifo_level));
    reg [19:0] overflow_count,accepted_samples;
    reg [1:0] max_fifo;
    localparam integer TAIL_W=$clog2(TAIL_TIMEOUT+1);
    reg [TAIL_W-1:0] tail_cycles;
    wire result_valid;
    wire result_ready;
    wire [31:0] result_id,cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total,protocol_errors;
    wire [95:0] logits;
    wire [1:0] class_id;
    wire [7:0] core_error;
    vibration_core #(.LANES(LANES),.BANDS(BANDS),.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(HIDDEN_SHIFT)) core(
        .clk(clk),.rst(rst),.in_valid(fifo_valid),.in_ready(core_ready),
        .in_sample(fifo_data[15:0]),.in_frame_id(fifo_data[48:17]),.in_last(fifo_data[16]),
        .out_valid(result_valid),.out_ready(result_ready),.out_frame_id(result_id),
        .out_logits(logits),.out_class(class_id),.out_error(core_error),
        .cycles_pre(cycles_pre),.cycles_dft(cycles_dft),.cycles_power(cycles_power),
        .cycles_nn(cycles_nn),.cycles_total(cycles_total),.protocol_errors(protocol_errors),
        .dbg_valid(),.dbg_kind(),.dbg_index(),.dbg_value());

    reg storing;
    reg [4:0] record_word;
    reg [19:0] record_generated,record_accepted;
    reg [31:0] record_protocol;
    reg [1:0] record_maxfifo;
    reg [9:0] result_count;
    wire [14:0] store_address={result_count,5'b0}+{10'b0,record_word};
    reg [16:0] write_position,write_end;
    reg [1:0] write_kind; // 0 header with erased commit, 1 records, 2 final commit
    reg [8:0] page_remaining;
    wire [14:0] log_read_address=write_position[15:1];
    wire [14:0] log_address=storing?store_address:log_read_address;
    wire [15:0] log_q0,log_q1;
    wire [15:0] log_q=log_address[14]?log_q1:log_q0;
    spram16k log0(.clk(clk),.address(log_address[13:0]),
        .write_enable(storing && !store_address[14]),.write_data(record_word[0]?selected_record_word[31:16]:selected_record_word[15:0]),.read_data(log_q0));
    spram16k log1(.clk(clk),.address(log_address[13:0]),
        .write_enable(storing && store_address[14]),.write_data(record_word[0]?selected_record_word[31:16]:selected_record_word[15:0]),.read_data(log_q1));
    assign result_ready=state==RUN && storing && record_word==31;
    assign status_done=state==HALT && committed;
    assign status_error=|error_flags;
    assign status_running=state==RUN;

    function automatic [31:0] crc_byte(input [31:0] prior,input [7:0] data);
        reg [31:0] c;integer i;
        begin c=prior^{24'd0,data};for(i=0;i<8;i=i+1) c=c[0]?(c>>1)^32'hedb88320:c>>1;
            crc_byte=c;end
    endfunction
    function automatic [31:0] log_header_word(input [3:0] index);
        case(index)
            0: log_header_word=32'h31474c56; // VLG1
            1: log_header_word=1;
            2: log_header_word={22'd0,result_count};
            3: log_header_word=32'hffffffff;
            4: log_header_word={24'd0,error_flags};
            5: log_header_word=generated_samples;
            6: log_header_word={12'd0,accepted_samples};
            7: log_header_word={12'd0,overflow_count};
            8: log_header_word=protocol_errors;
            9: log_header_word={30'd0,max_fifo};
            10:log_header_word={16'd0,period_cycles};
            11:log_header_word={22'd0,run_frames};
            default:log_header_word=32'hffffffff;
        endcase
    endfunction
    reg [31:0] selected_header_word;
    reg [31:0] selected_record_word;
    always @* begin
        cmd_valid=0;cmd_write=0;cmd_address=0;cmd_length=0;
        rd_ready=1;wr_valid=0;wr_data=0;
        selected_header_word=log_header_word(write_position[5:2]);
        case(record_word[4:1])
            0:selected_record_word=result_id;
            1:selected_record_word=logits[31:0];
            2:selected_record_word=logits[63:32];
            3:selected_record_word=logits[95:64];
            4:selected_record_word={16'd0,core_error,6'd0,class_id};
            5:selected_record_word=cycles_pre;
            6:selected_record_word=cycles_dft;
            7:selected_record_word=cycles_power;
            8:selected_record_word=cycles_nn;
            9:selected_record_word=cycles_total;
            10:selected_record_word={30'd0,record_maxfifo};
            11:selected_record_word={12'd0,record_generated};
            12:selected_record_word={12'd0,record_accepted};
            13:selected_record_word=record_protocol;
            default:selected_record_word=0;
        endcase
        case(state)
            BOOT_LOG: begin
                cmd_valid=1;
                cmd_address=24'h300000 | (24'(log_scan_chunk)<<LOG_SCAN_CHUNK_SHIFT);
                cmd_length=16'(1<<LOG_SCAN_CHUNK_SHIFT);
            end
            BOOT_IMAGE: begin cmd_valid=1;cmd_address=24'h040000;cmd_length=64;end
            LOAD: begin cmd_valid=1;cmd_address=24'h041000;cmd_length=payload_size[15:0];end
            WRITE_CMD: begin
                cmd_valid=1;cmd_write=1;
                cmd_address=write_kind==1?24'h301000+{7'd0,write_position}:
                            write_kind==2?24'h30000c:24'h300000;
                cmd_length={7'd0,page_remaining};
            end
            WRITE_DATA: begin
                wr_valid=1;
                if(write_kind==0) wr_data=selected_header_word[write_position[1:0]*8+:8];
                else if(write_kind==2) begin
                    case(write_position[1:0])
                        0:wr_data=8'h54;1:wr_data=8'h4d;2:wr_data=8'h4f;3:wr_data=8'h43;
                    endcase
                end else wr_data=write_position[0]?log_q[15:8]:log_q[7:0];
            end
            default:begin end
        endcase
    end
    always @(posedge clk) begin
        if(rst) begin
            state<=BOOT_LOG;error_flags<=0;committed<=0;existing_log<=0;
            header_word<=0;header_bad<=0;hash_bad<=0;
            byte_index<=0;log_blank<=1;log_scan_chunk<=0;source_frames<=0;run_frames<=0;period_cycles<=0;
            payload_size<=0;expected_crc<=0;crc<=32'hffffffff;low_byte<=0;load_we<=0;
            load_address<=0;load_data<=0;overflow_count<=0;accepted_samples<=0;max_fifo<=0;
            tail_cycles<=0;storing<=0;record_word<=0;result_count<=0;
            record_generated<=0;record_accepted<=0;record_protocol<=0;record_maxfifo<=0;
            write_position<=0;write_end<=0;write_kind<=0;page_remaining<=0;
        end else begin
            load_we<=0;
            if(source_valid) begin
                if(fifo_ready) accepted_samples<=accepted_samples+1'b1;
                else begin overflow_count<=overflow_count+1'b1;error_flags[3]<=1;end
            end
            if(fifo_level>max_fifo) max_fifo<=fifo_level;
            if(result_valid && state==RUN && !storing && result_count<1000) begin
                storing<=1;record_word<=0;
                record_generated<=generated_samples[19:0];record_accepted<=accepted_samples;
                record_protocol<=protocol_errors;record_maxfifo<=max_fifo;
                if(core_error!=0) error_flags[4]<=1;
            end
            if(storing) begin
                if(record_word==31) begin storing<=0;result_count<=result_count+1'b1;end
                else record_word<=record_word+1'b1;
            end
            case(state)
                BOOT_LOG: if(cmd_valid && cmd_ready) begin state<=BOOT_LOG_WAIT;byte_index<=0;end
                BOOT_LOG_WAIT: begin
                    if(rd_valid) begin
                        if(rd_data!=8'hff) log_blank<=0;
                    end
                    if(flash_done) begin
                        if(!log_blank) begin existing_log<=1;error_flags[0]<=1;state<=HALT;end
                        else if(log_scan_chunk==3) state<=BOOT_IMAGE;
                        else begin log_scan_chunk<=log_scan_chunk+1'b1;state<=BOOT_LOG;end
                    end
                end
                BOOT_IMAGE: if(cmd_valid && cmd_ready) begin state<=BOOT_IMAGE_WAIT;byte_index<=0;end
                BOOT_IMAGE_WAIT: begin
                    if(rd_valid) begin
                        header_word<={rd_data,header_word[31:8]};byte_index<=byte_index+1'b1;
                        if(byte_index<32 && byte_index[1:0]==3) begin
                            case(byte_index[4:2])
                                0:if({rd_data,header_word[31:8]}!=32'h31424956) header_bad<=1;
                                1:if({rd_data,header_word[31:8]}!=1) header_bad<=1;
                                2:if({rd_data,header_word[31:8]}!=1024) header_bad<=1;
                                3:begin
                                    source_frames<=header_word[12:8];
                                    if({rd_data,header_word[31:8]}<1 || {rd_data,header_word[31:8]}>16) header_bad<=1;
                                end
                                4:begin
                                    run_frames<=header_word[17:8];
                                    if({rd_data,header_word[31:8]}<1 || {rd_data,header_word[31:8]}>1000) header_bad<=1;
                                end
                                5:begin
                                    period_cycles<=header_word[23:8];
                                    if({rd_data,header_word[31:8]}<4 || {rd_data,header_word[31:8]}>65535) header_bad<=1;
                                end
                                6:begin
                                    payload_size<=header_word[23:8];
                                    if({rd_data,header_word[31:8]}!={16'd0,source_frames,11'd0}) header_bad<=1;
                                end
                                7:expected_crc<={rd_data,header_word[31:8]};
                            endcase
                        end else if(byte_index>=32 && rd_data!=MODEL_HASH[byte_index[4:0]*8+:8]) hash_bad<=1;
                    end
                    if(flash_done) state<=VALIDATE;
                end
                VALIDATE: begin
                    if(header_bad || hash_bad) begin error_flags[1]<=1;state<=HALT;end
                    else state<=LOAD;
                end
                LOAD: if(cmd_valid && cmd_ready) begin state<=LOAD_WAIT;byte_index<=0;end
                LOAD_WAIT: begin
                    if(rd_valid) begin
                        crc<=crc_byte(crc,rd_data);byte_index<=byte_index+1'b1;
                        if(byte_index[0]) begin
                            load_we<=1;load_address<=byte_index[14:1];load_data<={rd_data,low_byte};
                        end else low_byte<=rd_data;
                    end
                    if(flash_done) begin
                        if((crc^32'hffffffff)!=expected_crc) begin error_flags[2]<=1;state<=HALT;end
                        else state<=START;
                    end
                end
                START: state<=RUN;
                RUN: if(source_done) begin
                    if(!storing && {22'd0,result_count}==run_frames) state<=WRITE_HEADER;
                    else if(tail_cycles==TAIL_W'(TAIL_TIMEOUT)) begin error_flags[5]<=1;state<=WRITE_HEADER;end
                    else tail_cycles<=tail_cycles+1'b1;
                end
                WRITE_HEADER: begin
                    write_position<=0;write_end<=64;write_kind<=0;page_remaining<=64;state<=WRITE_CMD;
                end
                WRITE_CMD: if(cmd_valid && cmd_ready) state<=WRITE_PREFETCH;
                WRITE_PREFETCH: state<=WRITE_PREFETCH2;
                WRITE_PREFETCH2: state<=WRITE_DATA;
                WRITE_DATA: if(wr_valid && wr_ready) begin
                    write_position<=write_position+1'b1;page_remaining<=page_remaining-1'b1;
                    state<=page_remaining==1?WRITE_WAIT:WRITE_PREFETCH;
                end
                WRITE_WAIT: if(flash_done) begin
                    if(flash_error) begin error_flags[6]<=1;state<=HALT;end
                    else if(write_kind==2) begin committed<=1;state<=HALT;end
                    else if(write_kind==0 && result_count!=0) begin
                        write_kind<=1;write_position<=0;write_end<={1'b0,result_count,6'b0};
                        page_remaining<=result_count>=4?9'd256:{result_count[2:0],6'b0};state<=WRITE_CMD;
                    end else if(write_kind==1 && write_position<write_end) begin
                        page_remaining<=write_end-write_position>=256?9'd256:write_end[8:0]-write_position[8:0];
                        state<=WRITE_CMD;
                    end else begin
                        write_kind<=2;write_position<=0;write_end<=4;page_remaining<=4;state<=WRITE_CMD;
                    end
                end
                HALT: begin end
                default:begin error_flags[7]<=1;state<=HALT;end
            endcase
        end
    end
endmodule

// Two explicit register slots avoid spending four EBRs on a 49-bit-wide FIFO.
module replay_fifo(input wire clk,rst,input wire in_valid,output wire in_ready,
    input wire [48:0] in_data,output wire out_valid,input wire out_ready,
    output wire [48:0] out_data,output reg [1:0] occupancy);
    reg [48:0] slot0,slot1;
    reg rp,wp;
    assign out_valid=!rst && occupancy!=0;
    assign in_ready=!rst && (occupancy!=2 || out_ready);
    assign out_data=rp?slot1:slot0;
    wire push=in_valid&&in_ready,pop=out_valid&&out_ready;
    always @(posedge clk) begin
        if(rst) begin occupancy<=0;rp<=0;wp<=0;end
        else begin
            if(push) begin if(wp)slot1<=in_data;else slot0<=in_data;wp<=!wp;end
            if(pop)rp<=!rp;
            case({push,pop})
                2'b10:occupancy<=occupancy+1'b1;
                2'b01:occupancy<=occupancy-1'b1;
                default:begin end
            endcase
        end
    end
endmodule
