from pathlib import Path
import shutil, json, hashlib

root = Path(__file__).resolve().parents[2]
experiment = Path(__file__).resolve().parent
destination = experiment / 'timestamp_ebr'
destination.mkdir(parents=True, exist_ok=True)
files = ['rtl/platform/spram16k.sv', 'rtl/core/sync_fifo.sv', 'rtl/io/spi_master.sv',
         'rtl/io/flash_stream.sv', 'rtl/io/adxl345_capture.sv', 'rtl/core/vib_coeff_rom.sv',
         'rtl/core/vibration_core.sv', 'rtl/io/sensor_classifier.sv', 'rtl/upduino_field.sv']
for name in files:
    copy = destination / name
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root/name, copy)
(experiment/'production_source_sha256.json').write_text(json.dumps(
    {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}, indent=2)+'\n')
path = destination/'rtl/io/sensor_classifier.sv'
text = path.read_text()

def replace(old, new):
    global text
    assert text.count(old) == 1, (old, text.count(old))
    text = text.replace(old, new)

replace('reg [31:0] next_frame_id, current_frame_id, first_service_cycle;',
        'reg [31:0] next_frame_id, first_service_cycle;')
replace('wire [31:0] input_frame_id = partial_samples == 0 ? next_frame_id : current_frame_id;',
        'wire [31:0] input_frame_id = next_frame_id;')
replace('sync_fifo #(.WIDTH(64), .DEPTH(2)) timestamp_fifo', 'field_timestamp_ebr timestamp_fifo')
replace('partial_samples<=0; next_frame_id<=0; current_frame_id<=0; first_service_cycle<=0;',
        'partial_samples<=0; next_frame_id<=0; first_service_cycle<=0;')
replace('partial_samples<=0; current_frame_id<=0; first_service_cycle<=0;',
        'partial_samples<=0; first_service_cycle<=0;\n            if (partial_samples != 0) next_frame_id<=next_frame_id+1;')
replace('                current_frame_id<=next_frame_id;\n                next_frame_id<=next_frame_id+1;\n', '')
replace("            partial_samples<=partial_samples+1'b1;",
        "            if (complete_window) next_frame_id<=next_frame_id+1;\n            partial_samples<=partial_samples+1'b1;")
text += '''
// Experiment only: synchronous 2x64 storage mapped into four EBRs.
// Metadata is written on window completion and ready before NN output.
module field_timestamp_ebr(input wire clk,rst,in_valid,output wire in_ready,
 input wire [63:0] in_data,output wire out_valid,input wire out_ready,
 output reg [63:0] out_data,output reg [1:0] occupancy);
 (* ram_style = "block" *) reg [63:0] mem[0:1];
 reg rd_ptr,wr_ptr;
 assign out_valid=!rst&&(occupancy!=0);
 assign in_ready=!rst&&((occupancy<2)||out_ready);
 wire push=in_valid&&in_ready,pop=out_valid&&out_ready;
 always @(posedge clk) begin
   if(push) mem[wr_ptr]<=in_data;
   out_data<=mem[rd_ptr];
   if(rst)begin occupancy<=0;rd_ptr<=0;wr_ptr<=0;end
   else begin
    if(push)wr_ptr<=!wr_ptr;
    if(pop)rd_ptr<=!rd_ptr;
    case({push,pop})2'b10:occupancy<=occupancy+1'b1;2'b01:occupancy<=occupancy-1'b1;default:begin end endcase
   end
 end
endmodule
'''
path.write_text(text)
script = (root/'build/field_board_l4/synth.ys').read_text()
for name in files:
    script = script.replace(name, str(destination/name))
script = script.replace(str(root/'build/field_board_l4/netlist.json'), str(destination/'netlist.json'))
(destination/'synth.ys').write_text(script)
shutil.copyfile(root/'build/field_board_l4/reference.pcf', destination/'reference.pcf')
print(destination)
