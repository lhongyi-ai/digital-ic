// Two complete-window banks. A bank is released after preprocessing copies it.
module known_capture #(parameter integer N=1024)(
    input wire clk,rst,
    input wire in_valid,output wire in_ready,input wire signed [15:0] in_sample,
    input wire [31:0] in_frame_id,input wire in_last,
    output wire window_valid,input wire take,
    output wire window_bank,output wire [31:0] window_id,
    output wire signed [31:0] window_sum,
    input wire release_bank,input wire released_bank,
    input wire read_enable,input wire read_bank,input wire [$clog2(N)-1:0] read_address,
    output wire signed [15:0] read_sample,
    output reg [31:0] protocol_errors,accepted_samples
);
    localparam P=$clog2(N);
    (* ram_style="block" *) reg signed [15:0] raw0[0:N-1],raw1[0:N-1];
    reg signed [15:0] q0,q1;
    reg [1:0] full,busy;
    reg wr_bank,head_bank,draining;
    reg [P-1:0] position;
    reg [31:0] current_id,ids[0:1];
    reg signed [31:0] sum,sums[0:1];
    wire signed [15:0] half_sample=$signed(in_sample)>>>1;
    wire signed [15:0] shifted=half_sample+$signed({15'd0,in_sample[0]&&in_sample[1]});
    wire bad=(in_last!=(position==N-1)) || (position!=0 && in_frame_id!=current_id);
    assign in_ready=!rst&&(draining||(!full[wr_bank]&&!busy[wr_bank]));
    assign window_valid=!rst&&full[head_bank];
    assign window_bank=head_bank;
    assign window_id=ids[head_bank];
    assign window_sum=sums[head_bank];
    assign read_sample=read_bank?q1:q0;
    always @(posedge clk) begin
        if(read_enable) begin q0<=raw0[read_address];q1<=raw1[read_address];end
        if(!rst && in_valid && in_ready && !draining && !bad) begin
            if(wr_bank) raw1[position]<=shifted; else raw0[position]<=shifted;
        end
        if(rst) begin
            full<=0;busy<=0;wr_bank<=0;head_bank<=0;draining<=0;
            position<=0;sum<=0;current_id<=0;protocol_errors<=0;accepted_samples<=0;
            ids[0]<=0;ids[1]<=0;sums[0]<=0;sums[1]<=0;
        end else begin
            if(take&&window_valid) begin full[head_bank]<=0;busy[head_bank]<=1;head_bank<=~head_bank;end
            if(release_bank) busy[released_bank]<=0;
            if(in_valid&&in_ready) begin
                accepted_samples<=accepted_samples+1;
                if(draining) begin if(in_last) draining<=0;end
                else if(bad) begin
                    protocol_errors<=protocol_errors+1;position<=0;sum<=0;draining<=!in_last;
                end else begin
                    if(position==0) current_id<=in_frame_id;
                    if(position==N-1) begin
                        sums[wr_bank]<=sum+$signed(shifted);ids[wr_bank]<=in_frame_id;
                        full[wr_bank]<=1;wr_bank<=~wr_bank;position<=0;sum<=0;
                    end else begin position<=position+1'b1;sum<=sum+$signed(shifted);end
                end
            end
`ifdef VIB_ASSERT
            if(take) assert(window_valid);
            if(release_bank) assert(busy[released_bank]);
            if(in_valid&&in_ready&&!draining) assert(!full[wr_bank]&&!busy[wr_bank]);
`endif
        end
    end
endmodule
