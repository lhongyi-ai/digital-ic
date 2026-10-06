// N256 DSP-only selected-frequency monitor. No classification output is exposed.
// At 800 samples/s, bin spacing is 3.125 Hz. The logger records the actual ODR.
// Clamp to [-1024,1023] before x32 so the signed16 core input cannot overflow.
module sensor_spectrum #(
    parameter MODEL_DIR="artifacts/sensor_spectrum/model"
)(input wire clk,rst,
  input wire in_valid,output wire in_ready,input wire signed [15:0] in_sample,
  output wire power_valid,output wire [3:0] power_index,output wire [31:0] power,
  output wire window_done,output wire busy,output reg [31:0] clip_count);
    wire clipped_high=in_sample>16'sd1023;
    wire clipped_low=in_sample< -16'sd1024;
    wire signed [15:0] limited=clipped_high?16'sd1023:clipped_low?-16'sd1024:in_sample;
    wire signed [15:0] core_sample=limited<<<5;
    reg [7:0] point;
    reg [31:0] frame_id;
    reg [2:0] pending_windows;
    wire done;
    wire dbg_valid;
    wire [3:0] dbg_kind;
    wire [15:0] dbg_index;
    wire signed [39:0] dbg_value;
    wire accepted=in_valid&&in_ready;
    wire complete_input=accepted&&point==255;
    assign power_valid=!rst&&dbg_valid&&dbg_kind==4;
    assign power_index=power_valid?dbg_index[3:0]:4'd0;
    assign power=power_valid?dbg_value[31:0]:32'd0;
    assign window_done=!rst&&done;
    // A trailing partial window is intentionally not pending computation.
    assign busy=pending_windows!=0;
    vibration_core #(.N(256),.LANES(1),.BANDS(1),.MODEL_DIR(MODEL_DIR),.HIDDEN_SHIFT(0)) dsp(
        .clk(clk),.rst(rst),.in_valid(in_valid),.in_ready(in_ready),.in_sample(core_sample),
        .in_frame_id(frame_id),.in_last(point==255),.out_valid(done),.out_ready(1'b1),
        .out_frame_id(),.out_logits(),.out_class(),.out_error(),.cycles_pre(),.cycles_dft(),
        .cycles_power(),.cycles_nn(),.cycles_total(),.protocol_errors(),
        .dbg_valid(dbg_valid),.dbg_kind(dbg_kind),.dbg_index(dbg_index),.dbg_value(dbg_value));
    always @(posedge clk) begin
        if(rst) begin point<=0;frame_id<=0;pending_windows<=0;clip_count<=0;end
        else begin
            if(accepted) begin
                point<=point+1'b1;
                if(point==255) frame_id<=frame_id+1'b1;
                if(clipped_high||clipped_low) clip_count<=clip_count+1'b1;
            end
            case({complete_input,done})
                2'b10:pending_windows<=pending_windows+1'b1;
                2'b01:pending_windows<=pending_windows-1'b1;
                default:begin end
            endcase
        end
    end
endmodule
