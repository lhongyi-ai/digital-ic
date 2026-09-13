// Low-pin standalone place/route probe, not physical sensor pin assignments.
module sensor_spectrum_probe #(parameter MODEL_DIR="artifacts/sensor_spectrum/model")(
    input wire clk,rst,serial_sample,shift_sample,in_valid,
    output wire in_ready,busy,output reg observation);
    reg signed [15:0] sample;
    wire valid,done;
    wire [3:0] index;
    wire [31:0] power,clips;
    always @(posedge clk) begin
        if(rst) sample<=0;
        else if(shift_sample) sample<={sample[14:0],serial_sample};
        observation<=^{power,clips,index,valid,done,busy};
    end
    sensor_spectrum #(.MODEL_DIR(MODEL_DIR)) spectrum(.clk(clk),.rst(rst),
        .in_valid(in_valid),.in_ready(in_ready),.in_sample(sample),.power_valid(valid),
        .power_index(index),.power(power),.window_done(done),.busy(busy),.clip_count(clips));
endmodule
