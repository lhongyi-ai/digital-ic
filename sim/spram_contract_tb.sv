`timescale 1ns/1ps
module spram_contract_tb;
reg clk=0;always #5 clk=~clk;
reg [13:0] address=0;reg write_enable=0;reg [15:0] write_data=0;wire [15:0] read_data;
spram16k dut(.*);
task put(input [13:0] a,input [15:0] value);
begin @(negedge clk);address=a;write_data=value;write_enable=1;@(posedge clk);#1;end endtask
task get(input [13:0] a,input [15:0] expected);
reg [15:0] previous;
begin @(negedge clk);previous=read_data;address=a;write_enable=0;#1;
if(read_data!==previous)$fatal(1,"asynchronous output change");
@(posedge clk);#1;if(read_data!==expected)$fatal(1,"RAM mismatch address %d: %h expected %h",a,read_data,expected);
end endtask
initial begin
put(0,16'h1234);put(16383,16'hFEDC);put(1,16'hA55A);
get(0,16'h1234);get(16383,16'hFEDC);get(1,16'hA55A);
put(0,16'h5678);get(0,16'h5678);get(16383,16'hFEDC);
// Idle control changes have no asynchronous effect; RAM has no reset port.
get(0,16'h5678);get(1,16'hA55A);
$display("CONTRACT_PASS spram16k");$finish;
end
initial begin #10000;$fatal(1,"timeout");end
endmodule
