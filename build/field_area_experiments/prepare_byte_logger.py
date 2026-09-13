from pathlib import Path
import re, shutil

base=Path(__file__).resolve().parent
source=base/'timestamp_no_collision'
target=base/'byte_logger'
target.mkdir(exist_ok=True)
shutil.copytree(source/'rtl',target/'rtl',dirs_exist_ok=True)
path=target/'rtl/upduino_field.sv'
text=path.read_text()

def replace(old,new,count=1):
    global text
    assert text.count(old)==count,(old,text.count(old))
    text=text.replace(old,new)

records=re.search(r'case\(record_halfword\[4:1\]\)(.*?)endcase',text,re.S)
record_words=re.findall(r'(\d+):selected_record_word=([^;]+);',records[1])
assert len(record_words)==16
headers=re.search(r'        selected_header_word=32\'hffffffff;.*?selected_header_word=MODEL_HASH\[\(write_position\[4:2\]\)\*32\+:32\];',text,re.S)
header_words=re.findall(r'(\d+):selected_header_word=([^;]+);',headers[0])
assert len(header_words)==30
record_cases=['case(record_byte)']
for word,expr in record_words:
    for byte in range(4):
        record_cases.append(f"            6'd{int(word)*4+byte}:selected_record_byte=8'(({expr}) >> {8*byte});")
record_cases.append('        endcase')
replace(records[0],'\n'.join(record_cases))
header_cases=["        selected_header_byte=8'hff;",'        case(write_position[7:0])']
for word,expr in header_words:
    for byte in range(4):
        header_cases.append(f"            8'd{int(word)*4+byte}:selected_header_byte=8'(({expr}) >> {8*byte});")
for byte in range(32):
    header_cases.append(f"            8'd{64+byte}:selected_header_byte=MODEL_HASH[{byte*8}+:8];")
header_cases.extend(['            default:begin end','        endcase'])
replace(headers[0],'\n'.join(header_cases))
replace('reg [4:0] record_halfword;', 'reg [5:0] record_byte;\n    wire [4:0] record_halfword=record_byte[5:1];\n    reg [7:0] record_low_byte;')
replace('reg [31:0] selected_record_word,selected_header_word;', 'reg [7:0] selected_record_byte,selected_header_byte;')
replace('wire [15:0] memory_data=record_halfword[0]?selected_record_word[31:16]:selected_record_word[15:0];',
        'wire [15:0] memory_data={selected_record_byte,record_low_byte};')
replace('.write_enable(storing&&store_address[15:14]==bank&&!gap&&result_valid)',
        '.write_enable(storing&&record_byte[0]&&store_address[15:14]==bank&&!gap&&result_valid)')
replace('record_halfword==31','record_byte==63',count=2)
replace('record_halfword<=0','record_byte<=0',count=2)
replace('storing<=0;record_byte<=0;result_count<=0;', 'storing<=0;record_byte<=0;record_low_byte<=0;result_count<=0;')
replace('selected_header_word[write_position[1:0]*8+:8]', 'selected_header_byte')
replace('record_crc<=crc_byte(crc_byte(record_crc,memory_data[7:0]),memory_data[15:8]);',
        "record_crc<=crc_byte(record_crc,selected_record_byte);\n                    if(!record_byte[0])record_low_byte<=selected_record_byte;")
replace('payload_crc<=crc_byte(crc_byte(record_crc,memory_data[7:0]),memory_data[15:8]);',
        'payload_crc<=crc_byte(record_crc,selected_record_byte);')
replace("record_halfword<=record_halfword+1'b1;", "record_byte<=record_byte+1'b1;")
path.write_text(text)
(target/'synth.ys').write_text((source/'synth.ys').read_text().replace(str(source),str(target)))
shutil.copyfile(source/'reference.pcf',target/'reference.pcf')
print(target)
