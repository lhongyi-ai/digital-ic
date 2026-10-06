`timescale 1ns/1ps
module quant_tb;reg clk=0;always #5 clk=~clk;
known_spectral_core #(.N(16),.WINDOWS(2),.QUANT_PIPELINE(1)) dut(.clk(clk),.rst(1'b1),.in_valid(1'b0),.in_sample(16'd0),.in_frame_id(32'd0),.in_last(1'b0),.out_ready(1'b0));
initial begin force dut.wide_term=0;
force dut.wide_acc=64'd0;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 0/0");
force dut.wide_acc=64'd0;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 0/1");
force dut.wide_acc=64'd1;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 1/0");
force dut.wide_acc=64'd1;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 1/1");
force dut.wide_acc=64'd8388607;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 8388607/0");
force dut.wide_acc=64'd8388607;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 8388607/1");
force dut.wide_acc=64'd8388608;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 8388608/0");
force dut.wide_acc=64'd8388608;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=0)$fatal(1,"quant case 8388608/1");
force dut.wide_acc=64'd8388609;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=1)$fatal(1,"quant case 8388609/0");
force dut.wide_acc=64'd8388609;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-1)$fatal(1,"quant case 8388609/1");
force dut.wide_acc=64'd25165824;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=2)$fatal(1,"quant case 25165824/0");
force dut.wide_acc=64'd25165824;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-2)$fatal(1,"quant case 25165824/1");
force dut.wide_acc=64'd41943040;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=2)$fatal(1,"quant case 41943040/0");
force dut.wide_acc=64'd41943040;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-2)$fatal(1,"quant case 41943040/1");
force dut.wide_acc=64'd58720256;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=4)$fatal(1,"quant case 58720256/0");
force dut.wide_acc=64'd58720256;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-4)$fatal(1,"quant case 58720256/1");
force dut.wide_acc=64'd2113929216;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=126)$fatal(1,"quant case 2113929216/0");
force dut.wide_acc=64'd2113929216;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-126)$fatal(1,"quant case 2113929216/1");
force dut.wide_acc=64'd2122317824;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=126)$fatal(1,"quant case 2122317824/0");
force dut.wide_acc=64'd2122317824;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-126)$fatal(1,"quant case 2122317824/1");
force dut.wide_acc=64'd2122317825;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=127)$fatal(1,"quant case 2122317825/0");
force dut.wide_acc=64'd2122317825;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-127)$fatal(1,"quant case 2122317825/1");
force dut.wide_acc=64'd2130706432;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=127)$fatal(1,"quant case 2130706432/0");
force dut.wide_acc=64'd2130706432;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-127)$fatal(1,"quant case 2130706432/1");
force dut.wide_acc=64'd2139095040;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=127)$fatal(1,"quant case 2139095040/0");
force dut.wide_acc=64'd2139095040;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-127)$fatal(1,"quant case 2139095040/1");
force dut.wide_acc=64'd2147483648;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=127)$fatal(1,"quant case 2147483648/0");
force dut.wide_acc=64'd2147483648;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-127)$fatal(1,"quant case 2147483648/1");
force dut.wide_acc=64'd9223372036854775807;force dut.norm_negative=1'b0;#1;if($signed(dut.quantized_feature)!=127)$fatal(1,"quant case 9223372036854775807/0");
force dut.wide_acc=64'd9223372036854775807;force dut.norm_negative=1'b1;#1;if($signed(dut.quantized_feature)!=-127)$fatal(1,"quant case 9223372036854775807/1");
$display("ARITHMETIC_UNIT_PASS");$finish;end
endmodule
