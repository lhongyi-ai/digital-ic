// Separate field-classification firmware; raw SEN1 measurement firmware is retained.
// Finite continuous acquisition -> per-window results in SPRAM -> committed NOR log.
module upduino_field #(
    parameter integer LANES=1,
    parameter MODEL_DIR="build/field_fixture/trained/model",
    parameter integer HIDDEN_SHIFT=8,
    parameter [255:0] MODEL_HASH=0,
    parameter integer SYNTHETIC_MODEL=1,
    parameter integer AXIS=2,
    parameter integer TOTAL_SAMPLES=480000,
    parameter integer STARTUP_CYCLES=120000
)(input wire clk12,flash_miso,sensor_miso,sensor_drdy,
   output wire flash_cs_n,flash_sclk,flash_mosi,
   output wire sensor_cs_n,sensor_sclk,sensor_mosi,
   output wire status_done,status_error,status_running);
    reg [23:0] startup=0;
    wire rst=startup<STARTUP_CYCLES;
    always @(posedge clk12) if(rst) startup<=startup+1'b1;
    field_system #(.LANES(LANES),.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(HIDDEN_SHIFT),
        .MODEL_HASH(MODEL_HASH),.SYNTHETIC_MODEL(SYNTHETIC_MODEL),.AXIS(AXIS),.TOTAL_SAMPLES(TOTAL_SAMPLES)) system(
        .clk(clk12),.rst(rst),.flash_miso(flash_miso),.sensor_miso(sensor_miso),.sensor_drdy(sensor_drdy),
        .flash_cs_n(flash_cs_n),.flash_sclk(flash_sclk),.flash_mosi(flash_mosi),
        .sensor_cs_n(sensor_cs_n),.sensor_sclk(sensor_sclk),.sensor_mosi(sensor_mosi),
        .status_done(status_done),.status_error(status_error),.status_running(status_running));
endmodule

module field_system #(
    parameter integer LANES=1,
    parameter MODEL_DIR="build/field_fixture/trained/model",
    parameter integer HIDDEN_SHIFT=8,
    parameter [255:0] MODEL_HASH=0,
    parameter integer SYNTHETIC_MODEL=1,
    parameter integer AXIS=2,
    parameter integer TOTAL_SAMPLES=480000,
    // Production always scans all 128 KiB; shorter scans are testbench-only.
    parameter integer LOG_SCAN_CHUNK_SHIFT=15,
    parameter integer SENSOR_POWERUP_CYCLES=24000,
    parameter integer WATCHDOG_CYCLES=24000000
)(input wire clk,rst,flash_miso,sensor_miso,sensor_drdy,
   output wire flash_cs_n,flash_sclk,flash_mosi,
   output wire sensor_cs_n,sensor_sclk,sensor_mosi,
   output wire status_done,status_error,status_running);
    localparam BOOT=0,SCAN=1,RUN=2,DRAIN=3,HEADER=4,WRITE_CMD=5,
        PREFETCH=6,PREFETCH2=7,WRITE_DATA=8,WRITE_WAIT=9,HALT=10;
    localparam MAX_RESULTS=1875; // 10 min / 0.32 s; 120000 bytes, four SPRAMs.
    reg [3:0] state;
    reg [7:0] error_flags;
    reg committed,log_blank;
    reg [1:0] scan_chunk;
    reg [31:0] observed_count,cycle_counter,watchdog;
    reg [31:0] previous_missed,previous_overruns,first_service,last_service,service_wraps;
    reg service_seen;
    wire sample_valid,capture_init,capture_error;
    wire signed [15:0] x,y,z;
    wire [7:0] device_id;
    wire [31:0] service_cycle,samples_captured,missed_service,sensor_overruns;
    wire signed [15:0] raw_sample=AXIS==0?x:AXIS==1?y:z;
    adxl345_capture #(.POWERUP_CYCLES(SENSOR_POWERUP_CYCLES),.RATE_CODE(8'h0d)) capture(
        .clk(clk),.rst(rst),.enable(state==RUN),.drdy(sensor_drdy),
        .sclk(sensor_sclk),.mosi(sensor_mosi),.cs_n(sensor_cs_n),.miso(sensor_miso),
        .init_done(capture_init),.init_error(capture_error),.device_id(device_id),
        .sample_valid(sample_valid),.sample_ready(1'b1),.x(x),.y(y),.z(z),
        .service_cycle(service_cycle),.samples_captured(samples_captured),
        .missed_service(missed_service),.sensor_overruns(sensor_overruns));
    wire sampled=sample_valid&&state==RUN;
    wire [31:0] service_delta=service_cycle-last_service;
    // Readout timing is a detectable service check, not ADC aperture jitter.
    wire gap=state==RUN&&((missed_service!=previous_missed)||(sensor_overruns!=previous_overruns)||
        (sampled&&service_seen&&service_delta>22500));
    wire result_valid,result_ready,classifier_ready,classifier_busy;
    wire [31:0] result_id,pre_cycles,dft_cycles,power_cycles,nn_cycles,total_cycles;
    wire [31:0] result_first,result_last,accepted,dropped,canceled,clips,protocol_errors;
    wire [95:0] logits;
    wire [1:0] class_id;
    wire [7:0] core_error,partial_samples;
    sensor_classifier #(.LANES(LANES),.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(HIDDEN_SHIFT)) classifier(
        .clk(clk),.rst(rst),.in_valid(sampled),.in_ready(classifier_ready),.in_sample(raw_sample),
        .in_service_cycle(service_cycle),.gap(gap),.out_valid(result_valid),.out_ready(result_ready),
        .out_frame_id(result_id),.out_logits(logits),.out_class(class_id),.out_error(core_error),
        .cycles_pre(pre_cycles),.cycles_dft(dft_cycles),.cycles_power(power_cycles),
        .cycles_nn(nn_cycles),.cycles_total(total_cycles),.out_first_service_cycle(result_first),
        .out_last_service_cycle(result_last),.busy(classifier_busy),.partial_samples(partial_samples),
        .accepted_samples(accepted),.dropped_samples(dropped),.canceled_frames(canceled),
        .clip_count(clips),.protocol_errors(protocol_errors));

    reg cmd_valid,cmd_write,wr_valid;
    reg [23:0] cmd_address;
    reg [15:0] cmd_length;
    reg [7:0] wr_data;
    wire cmd_ready,wr_ready,rd_valid,flash_done,flash_error;
    wire [7:0] rd_data;
    flash_stream transport(.clk(clk),.rst(rst),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
        .cmd_write(cmd_write),.cmd_address(cmd_address),.cmd_length(cmd_length),
        .wr_valid(wr_valid),.wr_ready(wr_ready),.wr_data(wr_data),.rd_valid(rd_valid),.rd_ready(1'b1),
        .rd_data(rd_data),.done(flash_done),.error(flash_error),.flash_cs_n(flash_cs_n),
        .flash_sclk(flash_sclk),.flash_mosi(flash_mosi),.flash_miso(flash_miso));

    reg storing;
    reg [4:0] record_halfword;
    reg [10:0] result_count;
    reg [31:0] record_cycle,record_accepted,record_dropped,record_clips,payload_crc;
    reg [16:0] write_position,write_end;
    reg [8:0] page_remaining;
    reg [1:0] write_kind;
    reg [31:0] selected_record_word,selected_header_word;
    wire [15:0] store_address={result_count,5'b0}+{11'b0,record_halfword};
    wire [15:0] read_address=write_position[16:1];
    wire [15:0] memory_address=storing?store_address:read_address;
    wire [15:0] memory_data=record_halfword[0]?selected_record_word[31:16]:selected_record_word[15:0];
    wire [15:0] memory_q[0:3];
    wire [15:0] read_data=memory_q[memory_address[15:14]];
    genvar bank;
    generate for(bank=0;bank<4;bank=bank+1) begin:g_log
        spram16k ram(.clk(clk),.address(memory_address[13:0]),
            .write_enable(storing&&store_address[15:14]==bank&&!gap&&result_valid),
            .write_data(memory_data),.read_data(memory_q[bank]));
    end endgenerate
    assign result_ready=(state==RUN||state==DRAIN)&&storing&&record_halfword==31&&!gap;
    assign status_done=state==HALT&&committed;
    assign status_error=|error_flags;
    assign status_running=state==RUN;
    function automatic [31:0] crc_byte(input [31:0] prior,input [7:0] data);
        reg [31:0] c;integer j;
        begin c=prior^{24'd0,data};for(j=0;j<8;j=j+1)c=c[0]?(c>>1)^32'hedb88320:c>>1;
            crc_byte=c;end
    endfunction
    // A canceled partly stored record must not enter either count or CRC.
    reg [31:0] record_crc;
    always @* begin
        case(record_halfword[4:1])
            0:selected_record_word=result_id;
            1:selected_record_word=logits[31:0];
            2:selected_record_word=logits[63:32];
            3:selected_record_word=logits[95:64];
            4:selected_record_word={16'd0,core_error,6'd0,class_id};
            5:selected_record_word=pre_cycles;
            6:selected_record_word=dft_cycles;
            7:selected_record_word=power_cycles;
            8:selected_record_word=nn_cycles;
            9:selected_record_word=total_cycles;
            10:selected_record_word=result_first;
            11:selected_record_word=result_last;
            12:selected_record_word=record_cycle;
            13:selected_record_word=record_accepted;
            14:selected_record_word=record_dropped;
            15:selected_record_word=record_clips;
        endcase
        selected_header_word=32'hffffffff;
        case(write_position[7:2])
            0:selected_header_word=32'h314c4346; // FCL1
            1:selected_header_word=1;
            2:selected_header_word={21'd0,result_count};
            3:selected_header_word=32'hffffffff;
            4:selected_header_word={24'd0,error_flags};
            5:selected_header_word=observed_count;
            6:selected_header_word=TOTAL_SAMPLES;
            7:selected_header_word=800;
            8:selected_header_word=12000000;
            9:selected_header_word=256;
            10:selected_header_word=AXIS;
            11:selected_header_word=LANES;
            12:selected_header_word=accepted;
            13:selected_header_word=dropped;
            14:selected_header_word=canceled;
            15:selected_header_word=clips;
            24:selected_header_word=missed_service;
            25:selected_header_word=sensor_overruns;
            26:selected_header_word=first_service;
            27:selected_header_word=last_service;
            28:selected_header_word=service_wraps;
            29:selected_header_word={24'd0,partial_samples};
            30:selected_header_word=payload_crc^32'hffffffff;
            31:selected_header_word=256;
            32:selected_header_word=64;
            33:selected_header_word=32'h00301000;
            34:selected_header_word=protocol_errors;
            35:selected_header_word={24'd0,device_id};
            36:selected_header_word=MAX_RESULTS;
            37:selected_header_word=SYNTHETIC_MODEL;
            default:begin end
        endcase
        if(write_position[7:2]>=16&&write_position[7:2]<=23)
            selected_header_word=MODEL_HASH[(write_position[4:2])*32+:32];
        cmd_valid=0;cmd_write=0;cmd_address=0;cmd_length=0;wr_valid=0;wr_data=0;
        case(state)
            BOOT:begin cmd_valid=1;cmd_address=24'h300000|(24'(scan_chunk)<<LOG_SCAN_CHUNK_SHIFT);
                cmd_length=16'(1<<LOG_SCAN_CHUNK_SHIFT);end
            WRITE_CMD:begin cmd_valid=1;cmd_write=1;
                cmd_address=write_kind==1?24'h301000+{7'd0,write_position}:write_kind==2?24'h30000c:24'h300000;
                cmd_length={7'd0,page_remaining};end
            WRITE_DATA:begin
                wr_valid=1;
                if(write_kind==0)wr_data=selected_header_word[write_position[1:0]*8+:8];
                else if(write_kind==2)case(write_position[1:0])
                    0:wr_data=8'h54;1:wr_data=8'h4d;2:wr_data=8'h4f;3:wr_data=8'h43;
                endcase
                else wr_data=write_position[0]?read_data[15:8]:read_data[7:0];
            end
            default:begin end
        endcase
    end
    always @(posedge clk) begin
        if(rst)begin
            state<=BOOT;error_flags<=0;committed<=0;log_blank<=1;scan_chunk<=0;
            observed_count<=0;cycle_counter<=0;watchdog<=0;previous_missed<=0;previous_overruns<=0;
            first_service<=0;last_service<=0;service_wraps<=0;service_seen<=0;
            storing<=0;record_halfword<=0;result_count<=0;record_cycle<=0;record_accepted<=0;
            record_dropped<=0;record_clips<=0;payload_crc<=32'hffffffff;record_crc<=32'hffffffff;
            write_position<=0;write_end<=0;page_remaining<=0;write_kind<=0;
        end else begin
            cycle_counter<=cycle_counter+1'b1;
            previous_missed<=missed_service;previous_overruns<=sensor_overruns;
            if(sampled)begin
                observed_count<=observed_count+1'b1;
                if(!service_seen)begin first_service<=service_cycle;service_seen<=1;end
                else if(service_cycle<last_service)service_wraps<=service_wraps+1'b1;
                last_service<=service_cycle;
            end
            if(gap||(sampled&&!classifier_ready))error_flags[3]<=1;
            if(result_valid&&(state==RUN||state==DRAIN)&&!storing&&!gap)begin
                if(result_count==MAX_RESULTS)begin error_flags[5]<=1;state<=HALT;end
                else begin storing<=1;record_halfword<=0;record_cycle<=cycle_counter;
                    record_accepted<=accepted;record_dropped<=dropped;record_clips<=clips;record_crc<=payload_crc;
                    if(core_error!=0)error_flags[4]<=1;
                end
            end
            if(storing)begin
                if(gap||!result_valid)storing<=0;
                else begin
                    record_crc<=crc_byte(crc_byte(record_crc,memory_data[7:0]),memory_data[15:8]);
                    if(record_halfword==31)begin storing<=0;result_count<=result_count+1'b1;
                        payload_crc<=crc_byte(crc_byte(record_crc,memory_data[7:0]),memory_data[15:8]);end
                    else record_halfword<=record_halfword+1'b1;
                end
            end
            case(state)
                BOOT:begin
                    if(TOTAL_SAMPLES<1||TOTAL_SAMPLES>480000||AXIS<0||AXIS>2||
                       LOG_SCAN_CHUNK_SHIFT<1||LOG_SCAN_CHUNK_SHIFT>15
`ifdef ICE40
                       ||LOG_SCAN_CHUNK_SHIFT!=15
`endif
                       )begin error_flags[7]<=1;state<=HALT;end
                    else if(cmd_ready)state<=SCAN;
                end
                SCAN:begin
                    if(rd_valid&&rd_data!=8'hff)log_blank<=0;
                    if(flash_done)begin
                        if(flash_error)begin error_flags[6]<=1;state<=HALT;end
                        else if(!log_blank)begin error_flags[0]<=1;state<=HALT;end
                        else if(scan_chunk==3)state<=RUN;
                        else begin scan_chunk<=scan_chunk+1'b1;state<=BOOT;end
                    end
                end
                RUN:begin
                    if(sampled)watchdog<=0;else watchdog<=watchdog+1'b1;
                    if(capture_error)begin error_flags[1]<=1;state<=DRAIN;end
                    else if(watchdog==WATCHDOG_CYCLES)begin error_flags[2]<=1;state<=DRAIN;end
                    else if(sampled&&observed_count==TOTAL_SAMPLES-1)state<=DRAIN;
                end
                DRAIN:if(!classifier_busy&&!storing)state<=HEADER;
                HEADER:begin write_position<=0;write_end<=256;write_kind<=0;page_remaining<=256;state<=WRITE_CMD;end
                WRITE_CMD:if(cmd_valid&&cmd_ready)state<=PREFETCH;
                PREFETCH:state<=PREFETCH2;
                PREFETCH2:state<=WRITE_DATA;
                WRITE_DATA:if(wr_valid&&wr_ready)begin
                    write_position<=write_position+1'b1;page_remaining<=page_remaining-1'b1;
                    state<=page_remaining==1?WRITE_WAIT:PREFETCH;end
                WRITE_WAIT:if(flash_done)begin
                    if(flash_error)begin error_flags[6]<=1;state<=HALT;end
                    else if(write_kind==2)begin committed<=1;state<=HALT;end
                    else if(write_kind==0&&result_count!=0)begin
                        write_kind<=1;write_position<=0;write_end<={result_count,6'b0};
                        page_remaining<=result_count>=4?9'd256:{result_count[2:0],6'b0};state<=WRITE_CMD;
                    end else if(write_kind==1&&write_position<write_end)begin
                        page_remaining<=write_end-write_position>=256?9'd256:write_end[8:0]-write_position[8:0];state<=WRITE_CMD;
                    end else begin write_kind<=2;write_position<=0;write_end<=4;page_remaining<=4;state<=WRITE_CMD;end
                end
                HALT:begin end
                default:begin error_flags[7]<=1;state<=HALT;end
            endcase
        end
    end
`ifdef VIB_ASSERT
    always @(posedge clk)if(!rst)begin
        assert(result_count<=MAX_RESULTS);
        if(storing)assert(store_address<MAX_RESULTS*32);
        if(committed)assert(state==HALT);
    end
`endif
endmodule
