// Fixed-rate source deliberately has NO ready input. Consumers must count loss.
module replay_source(
    input wire clk,rst,
    input wire load_we,input wire [13:0] load_address,input wire [15:0] load_data,
    input wire start,input wire [4:0] source_frames,input wire [9:0] run_frames,
    input wire [15:0] period_cycles,
    output reg sample_valid,output reg signed [15:0] sample,
    output reg [31:0] frame_id,output reg sample_last,
    output reg finished,output wire [31:0] generated_samples
);
    reg active;
    reg [15:0] phase;
    reg [9:0] current_frame;
    reg [19:0] generated_count;
    assign generated_samples={12'd0,generated_count};
    reg [9:0] point;
    reg [13:0] read_address;
    wire [15:0] q;
    spram16k ram(.clk(clk),.address(load_we?load_address:read_address),
        .write_enable(load_we),.write_data(load_data),.read_data(q));
    always @(posedge clk) begin
        if(rst) begin
            active<=0;phase<=0;current_frame<=0;point<=0;read_address<=0;
            sample_valid<=0;sample<=0;frame_id<=0;sample_last<=0;
            finished<=0;generated_count<=0;
        end else begin
            sample_valid<=0;
            if(start && !active) begin
                active<=1;phase<=0;current_frame<=0;point<=0;read_address<=0;
                finished<=0;generated_count<=0;
            end else if(active) begin
                // Address has been stable for two clocks when the pulse is sent.
                if(phase==2) begin
                    sample_valid<=1;sample<=q;sample_last<=point==1023;frame_id<={22'd0,current_frame};
                    generated_count<=generated_count+1'b1;
                    if(point==1023 && current_frame+1==run_frames) begin
                        active<=0;finished<=1;
                    end
                end
                if(phase+1==period_cycles) begin
                    phase<=0;point<=point+1'b1;
                    if(point==1023) current_frame<=current_frame+1'b1;
                    if({1'b0,read_address}+1 == {source_frames,10'b0}) read_address<=0;
                    else read_address<=read_address+1'b1;
                end else phase<=phase+1'b1;
            end
        end
    end
endmodule
