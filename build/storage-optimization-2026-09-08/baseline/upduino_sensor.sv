// Standalone sensor acquisition image. Does not instantiate the classifier.
module upduino_sensor #(
    parameter integer TOTAL_SAMPLES=480000,
    parameter integer STORE_SAMPLES=24000,
    parameter [7:0] RATE_CODE=8'h0d,
    parameter integer AXIS=0,
    parameter integer ENABLE_SPECTRUM=1,
    parameter SPECTRUM_MODEL_DIR="artifacts/sensor_spectrum/model",
    parameter signed [31:0] CAL_OFFSET_Q8=0,
    parameter [31:0] CAL_GAIN_Q20=32'd4096000,
    parameter integer STARTUP_CYCLES=120000
)(input wire clk12, flash_miso, sensor_miso, sensor_drdy,
  output wire flash_cs_n, flash_sclk, flash_mosi,
  output wire sensor_cs_n, sensor_sclk, sensor_mosi,
  output wire status_done, status_error, status_running);
    reg [23:0] startup=0;
    wire rst=startup<STARTUP_CYCLES;
    always @(posedge clk12) if(rst) startup<=startup+1'b1;
    sensor_system #(.TOTAL_SAMPLES(TOTAL_SAMPLES),.STORE_SAMPLES(STORE_SAMPLES),
        .RATE_CODE(RATE_CODE),.AXIS(AXIS),.ENABLE_SPECTRUM(ENABLE_SPECTRUM),
        .SPECTRUM_MODEL_DIR(SPECTRUM_MODEL_DIR),.CAL_OFFSET_Q8(CAL_OFFSET_Q8),.CAL_GAIN_Q20(CAL_GAIN_Q20)) system(
        .clk(clk12),.rst(rst),.flash_miso(flash_miso),.sensor_miso(sensor_miso),
        .sensor_drdy(sensor_drdy),.flash_cs_n(flash_cs_n),.flash_sclk(flash_sclk),
        .flash_mosi(flash_mosi),.sensor_cs_n(sensor_cs_n),.sensor_sclk(sensor_sclk),
        .sensor_mosi(sensor_mosi),.status_done(status_done),.status_error(status_error),
        .status_running(status_running));
endmodule

module sensor_system #(
    parameter integer TOTAL_SAMPLES=480000,
    parameter integer STORE_SAMPLES=24000,
    parameter [7:0] RATE_CODE=8'h0d,
    parameter integer AXIS=0,
    parameter integer ENABLE_SPECTRUM=1,
    parameter SPECTRUM_MODEL_DIR="artifacts/sensor_spectrum/model",
    parameter signed [31:0] CAL_OFFSET_Q8=0,
    parameter [31:0] CAL_GAIN_Q20=32'd4096000,
    parameter integer SENSOR_POWERUP_CYCLES=24000,
    parameter integer WATCHDOG_CYCLES=12000000,
    // Smaller values are for simulation only; the board build leaves defaults.
    parameter integer LOG_SCAN_BYTES=131072,
    parameter integer SCAN_CHUNK_BYTES=65535,
    parameter [31:0] SERVICE_COUNTER_START=0,
    parameter integer BANK_ADDR_BITS=14
)(input wire clk, rst, flash_miso, sensor_miso, sensor_drdy,
  output wire flash_cs_n, flash_sclk, flash_mosi,
  output wire sensor_cs_n, sensor_sclk, sensor_mosi,
  output wire status_done, status_error, status_running);
    localparam [3:0] SCAN_CMD=0, SCAN_READ=1, RUN=2, FINALIZE=3,
        WRITE_CMD=4, PREFETCH=5, PREFETCH2=6, WRITE_DATA=7,
        WRITE_WAIT=8, HALT=9;
    localparam [23:0] LOG_BASE=24'h300000, PAYLOAD_BASE=24'h301000;
    localparam integer HEADER_BYTES=ENABLE_SPECTRUM!=0 ? 208 : 128;
    reg [3:0] state;
    reg [7:0] error_flags;
    reg committed, log_blank;
    reg [17:0] scan_position;
    reg [15:0] scan_length;
    reg [31:0] observed_count, first_cycle, last_cycle, min_delta, max_delta;
    reg [31:0] interval_overflows, watchdog, crc;
    reg signed [31:0] last_calibrated;
    reg signed [63:0] calibrated_sum;
    reg [31:0] calibrated_count;
    reg [31:0] service_wrap_count;
    reg [31:0] spectrum_windows;
    wire spectrum_ready, spectrum_valid, spectrum_done, spectrum_busy;
    wire [3:0] spectrum_index;
    wire [31:0] spectrum_power, spectrum_clips;
    wire [15:0] spectrum_q;
    reg spectrum_storing;
    reg [3:0] spectrum_saved_index;
    reg [15:0] spectrum_high;
    reg [15:0] stored_count;
    reg storing;
    reg [15:0] interval_hold;
    reg [16:0] write_position, write_end;
    reg [8:0] page_remaining;
    reg [1:0] write_kind; // 0 payload, 1 header with erased commit, 2 commit token

    wire init_done, init_error, sample_valid;
    wire cal_ready, cal_valid;
    wire signed [31:0] cal_mg;
    wire sample_ready=(state==RUN) && !storing && cal_ready && spectrum_ready;
    wire [7:0] device_id;
    wire signed [15:0] x,y,z;
    wire [31:0] service_cycle, samples_captured, missed_service, sensor_overruns;
    wire [15:0] selected_axis=AXIS==0 ? x : AXIS==1 ? y : z;
    wire [31:0] delta=service_cycle-last_cycle;
    wire [29:0] delta_q4=service_cycle[31:2]-last_cycle[31:2];
    wire interval_bad=observed_count!=0 && (delta>262140 || delta_q4>65535);
    wire [15:0] interval_value=observed_count==0 ? 16'd0 :
        interval_bad ? 16'hffff : delta_q4[15:0];
    wire accept_sample=sample_valid && sample_ready;
    static_calibration #(.OFFSET_Q8(CAL_OFFSET_Q8),.GAIN_Q20(CAL_GAIN_Q20)) calibration(
        .clk(clk),.rst(rst),.in_valid(sample_valid && state==RUN && !storing && spectrum_ready),
        .in_ready(cal_ready),.in_raw(selected_axis),.out_valid(cal_valid),
        .out_ready(1'b1),.out_mg(cal_mg));
    generate if(ENABLE_SPECTRUM!=0) begin: with_spectrum
        sensor_spectrum #(.MODEL_DIR(SPECTRUM_MODEL_DIR)) spectrum(
            .clk(clk),.rst(rst),.in_valid(sample_valid && state==RUN && !storing && cal_ready),
            .in_ready(spectrum_ready),.in_sample(selected_axis),.power_valid(spectrum_valid),
            .power_index(spectrum_index),.power(spectrum_power),.window_done(spectrum_done),
            .busy(spectrum_busy),.clip_count(spectrum_clips));
        wire [13:0] spectrum_address=spectrum_storing ? {9'd0,spectrum_saved_index,1'b1} :
            spectrum_valid ? {9'd0,spectrum_index,1'b0} : 14'((write_position-17'd144)>>1);
        spram16k spectrum_ram(.clk(clk),.address(spectrum_address),
            .write_enable(spectrum_storing || spectrum_valid),
            .write_data(spectrum_storing ? spectrum_high : spectrum_power[15:0]),.read_data(spectrum_q));
    end else begin: without_spectrum
        assign spectrum_ready=1;
        assign spectrum_valid=0;assign spectrum_done=0;assign spectrum_busy=0;
        assign spectrum_index=0;assign spectrum_power=0;assign spectrum_clips=0;assign spectrum_q=0;
    end endgenerate

    adxl345_capture #(.RATE_CODE(RATE_CODE),.POWERUP_CYCLES(SENSOR_POWERUP_CYCLES),
        .SERVICE_COUNTER_START(SERVICE_COUNTER_START)) capture(
        .clk(clk),.rst(rst),.enable(state==RUN),.drdy(sensor_drdy),
        .sclk(sensor_sclk),.mosi(sensor_mosi),.miso(sensor_miso),.cs_n(sensor_cs_n),
        .init_done(init_done),.init_error(init_error),.device_id(device_id),
        .sample_valid(sample_valid),.sample_ready(sample_ready),.x(x),.y(y),.z(z),
        .service_cycle(service_cycle),.samples_captured(samples_captured),
        .missed_service(missed_service),.sensor_overruns(sensor_overruns));

    wire ram_write=storing || (accept_sample && stored_count<16'(STORE_SAMPLES));
    wire [15:0] store_address={stored_count[14:0],1'b0}+{15'd0,storing};
    wire [15:0] ram_address=ram_write ? store_address : write_position[16:1];
    wire [1:0] ram_bank=2'(ram_address >> BANK_ADDR_BITS);
    wire [13:0] local_address=14'(ram_address & ((1<<BANK_ADDR_BITS)-1));
    wire [15:0] ram_data=storing ? interval_hold : selected_axis;
    wire [15:0] q0,q1,q2;
    wire [15:0] ram_q=ram_bank==0 ? q0 : ram_bank==1 ? q1 : q2;
    spram16k ram0(.clk(clk),.address(local_address),.write_enable(ram_write && ram_bank==0),
        .write_data(ram_data),.read_data(q0));
    spram16k ram1(.clk(clk),.address(local_address),.write_enable(ram_write && ram_bank==1),
        .write_data(ram_data),.read_data(q1));
    spram16k ram2(.clk(clk),.address(local_address),.write_enable(ram_write && ram_bank==2),
        .write_data(ram_data),.read_data(q2));

    reg cmd_valid, cmd_write, wr_valid;
    reg [23:0] cmd_address;
    reg [15:0] cmd_length;
    reg [7:0] wr_data;
    wire cmd_ready, wr_ready, rd_valid, flash_done, flash_error;
    wire [7:0] rd_data;
    flash_stream transport(.clk(clk),.rst(rst),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),
        .cmd_write(cmd_write),.cmd_address(cmd_address),.cmd_length(cmd_length),
        .wr_valid(wr_valid),.wr_ready(wr_ready),.wr_data(wr_data),
        .rd_valid(rd_valid),.rd_ready(1'b1),.rd_data(rd_data),.done(flash_done),.error(flash_error),
        .flash_cs_n(flash_cs_n),.flash_sclk(flash_sclk),.flash_mosi(flash_mosi),.flash_miso(flash_miso));

    assign status_done=state==HALT && committed;
    assign status_error=|error_flags;
    assign status_running=state==RUN;

    function automatic [31:0] crc_byte(input [31:0] prior,input [7:0] value);
        reg [31:0] c; integer i;
        begin
            c=prior^{24'd0,value};
            for(i=0;i<8;i=i+1) c=c[0] ? (c>>1)^32'hedb88320 : c>>1;
            crc_byte=c;
        end
    endfunction
    function automatic [31:0] header_word(input [5:0] index);
        case(index)
            0:header_word=32'h314e4553;
            1:header_word=1;
            2:header_word={16'd0,stored_count};
            3:header_word=32'hffffffff;
            4:header_word={24'd0,error_flags};
            5:header_word=observed_count;
            6:header_word=TOTAL_SAMPLES;
            7:header_word=STORE_SAMPLES;
            8:header_word=12000000;
            9:header_word={24'd0,RATE_CODE};
            10:header_word=AXIS;
            11:header_word={24'd0,device_id};
            12:header_word=first_cycle;
            13:header_word=last_cycle;
            14:header_word=observed_count>1 ? min_delta : 0;
            15:header_word=max_delta;
            16:header_word=samples_captured;
            17:header_word=missed_service;
            18:header_word=sensor_overruns;
            19:header_word=interval_overflows;
            20:header_word=crc^32'hffffffff;
            21:header_word=4;
            22:header_word={8'd0,PAYLOAD_BASE};
            23:header_word=4;
            24:header_word=last_calibrated;
            25:header_word=calibrated_sum[31:0];
            26:header_word=calibrated_sum[63:32];
            27:header_word=calibrated_count;
            28:header_word=CAL_OFFSET_Q8;
            29:header_word=CAL_GAIN_Q20;
            30:header_word=service_wrap_count;
            31:header_word=HEADER_BYTES;
            32:header_word=spectrum_windows;
            33:header_word=256;
            34:header_word=1;
            35:header_word=spectrum_clips;
            default:header_word=32'hffffffff;
        endcase
    endfunction
    reg [31:0] chosen_header;
    always @* begin
        cmd_valid=0; cmd_write=0; cmd_address=0; cmd_length=0;
        wr_valid=0; wr_data=0;
        chosen_header=header_word(write_position[7:2]);
        case(state)
            SCAN_CMD: begin
                cmd_valid=1; cmd_address=LOG_BASE+{6'd0,scan_position}; cmd_length=scan_length;
            end
            WRITE_CMD: begin
                cmd_valid=1; cmd_write=1;
                cmd_address=write_kind==0 ? PAYLOAD_BASE+{7'd0,write_position} :
                    write_kind==1 ? LOG_BASE : LOG_BASE+24'd12;
                cmd_length={7'd0,page_remaining};
            end
            WRITE_DATA: begin
                wr_valid=1;
                if(write_kind==0) wr_data=write_position[0] ? ram_q[15:8] : ram_q[7:0];
                else if(write_kind==1) begin
                    if(ENABLE_SPECTRUM!=0 && write_position>=144)
                        wr_data=spectrum_windows==0 ? 8'd0 : write_position[0] ? spectrum_q[15:8] : spectrum_q[7:0];
                    else wr_data=chosen_header[write_position[1:0]*8+:8];
                end
                else case(write_position[1:0])
                    0:wr_data=8'h54;1:wr_data=8'h4d;2:wr_data=8'h4f;3:wr_data=8'h43;
                endcase
            end
            default:begin end
        endcase
    end

    always @(posedge clk) begin
        if(rst) begin
            state<=SCAN_CMD; error_flags<=0; committed<=0; log_blank<=1;
            scan_position<=0; scan_length<=LOG_SCAN_BYTES>=SCAN_CHUNK_BYTES ? 16'(SCAN_CHUNK_BYTES) : 16'(LOG_SCAN_BYTES);
            observed_count<=0; first_cycle<=0; last_cycle<=0; min_delta<=32'hffffffff; max_delta<=0;
            interval_overflows<=0; watchdog<=0; crc<=32'hffffffff;
            last_calibrated<=0;calibrated_sum<=0;calibrated_count<=0;service_wrap_count<=0;
            spectrum_windows<=0;spectrum_storing<=0;spectrum_saved_index<=0;spectrum_high<=0;
            stored_count<=0; storing<=0; interval_hold<=0;
            write_position<=0; write_end<=0; page_remaining<=0; write_kind<=0;
        end else begin
            spectrum_storing<=0;
            if(spectrum_valid) begin
                spectrum_storing<=1;spectrum_saved_index<=spectrum_index;spectrum_high<=spectrum_power[31:16];
            end
            if(spectrum_done) spectrum_windows<=spectrum_windows+1'b1;
            if(cal_valid) begin
                last_calibrated<=cal_mg;
                calibrated_sum<=calibrated_sum+{{32{cal_mg[31]}},cal_mg};
                calibrated_count<=calibrated_count+1'b1;
            end
            if(storing) begin storing<=0; stored_count<=stored_count+1'b1; end
            if(accept_sample) begin
                observed_count<=observed_count+1'b1;
                last_cycle<=service_cycle;
                watchdog<=0;
                if(observed_count==0) first_cycle<=service_cycle;
                else begin
                    if(service_cycle<last_cycle) service_wrap_count<=service_wrap_count+1'b1;
                    if(delta<min_delta) min_delta<=delta;
                    if(delta>max_delta) max_delta<=delta;
                    if(interval_bad) begin interval_overflows<=interval_overflows+1'b1;error_flags[2]<=1;end
                end
                if(stored_count<16'(STORE_SAMPLES)) begin storing<=1;interval_hold<=interval_value;end
            end
            if(state==RUN) begin
                if(missed_service!=0) error_flags[3]<=1;
                if(sensor_overruns!=0) error_flags[4]<=1;
            end
            case(state)
                SCAN_CMD: if(TOTAL_SAMPLES<1 || STORE_SAMPLES<1 || STORE_SAMPLES>TOTAL_SAMPLES ||
                    STORE_SAMPLES>3*(1<<BANK_ADDR_BITS)/2 || STORE_SAMPLES>24000 ||
                    AXIS<0 || AXIS>2 || !(RATE_CODE==8'h0a || RATE_CODE==8'h0c || RATE_CODE==8'h0d)) begin
                    error_flags[7]<=1;state<=HALT;
                end else if(cmd_valid && cmd_ready) state<=SCAN_READ;
                SCAN_READ: begin
                    if(rd_valid && rd_data!=8'hff) log_blank<=0;
                    if(flash_done) begin
                        if(flash_error) begin error_flags[6]<=1;state<=HALT;end
                        else if(!log_blank) begin error_flags[0]<=1;state<=HALT;end
                        else if({14'd0,scan_position}+{16'd0,scan_length}>=LOG_SCAN_BYTES) state<=RUN;
                        else begin
                            scan_position<=scan_position+{2'd0,scan_length};
                            scan_length<=LOG_SCAN_BYTES-({14'd0,scan_position}+{16'd0,scan_length})>=SCAN_CHUNK_BYTES ?
                                16'(SCAN_CHUNK_BYTES) : 16'(LOG_SCAN_BYTES-({14'd0,scan_position}+{16'd0,scan_length}));
                            state<=SCAN_CMD;
                        end
                    end
                end
                RUN: begin
                    if(init_error) begin error_flags[1]<=1;state<=FINALIZE;end
                    else if(accept_sample && observed_count==TOTAL_SAMPLES-1) state<=FINALIZE;
                    else if(init_done && !accept_sample) begin
                        if(watchdog>=WATCHDOG_CYCLES-1) begin error_flags[5]<=1;state<=FINALIZE;end
                        else watchdog<=watchdog+1'b1;
                    end
                end
                FINALIZE: if(!storing && calibrated_count==observed_count && !spectrum_busy && !spectrum_storing) begin
                    write_position<=0;
                    if(stored_count!=0) begin
                        write_kind<=0;write_end<={stored_count[14:0],2'b0};
                        page_remaining<=stored_count>=64 ? 9'd256 : {stored_count[6:0],2'b0};
                    end else begin write_kind<=1;write_end<=17'(HEADER_BYTES);page_remaining<=9'(HEADER_BYTES);end
                    state<=WRITE_CMD;
                end
                WRITE_CMD: if(cmd_valid && cmd_ready) state<=PREFETCH;
                PREFETCH: state<=PREFETCH2;
                PREFETCH2: state<=WRITE_DATA;
                WRITE_DATA: if(wr_valid && wr_ready) begin
                    if(write_kind==0) crc<=crc_byte(crc,wr_data);
                    write_position<=write_position+1'b1;
                    page_remaining<=page_remaining-1'b1;
                    state<=page_remaining==1 ? WRITE_WAIT : PREFETCH;
                end
                WRITE_WAIT: if(flash_done) begin
                    if(flash_error) begin error_flags[6]<=1;state<=HALT;end
                    else if(write_kind==2) begin committed<=1;state<=HALT;end
                    else if(write_kind==0 && write_position<write_end) begin
                        page_remaining<=write_end-write_position>=256 ? 9'd256 : write_end[8:0]-write_position[8:0];
                        state<=WRITE_CMD;
                    end else begin
                        write_position<=0;
                        if(write_kind==0) begin write_kind<=1;write_end<=17'(HEADER_BYTES);page_remaining<=9'(HEADER_BYTES);end
                        else begin write_kind<=2;write_end<=4;page_remaining<=4;end
                        state<=WRITE_CMD;
                    end
                end
                HALT:begin end
                default:begin error_flags[7]<=1;state<=HALT;end
            endcase
        end
    end
endmodule
