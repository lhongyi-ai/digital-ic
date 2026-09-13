#!/usr/bin/env python3
"""Inspect official archive central directory only; no audio read."""
from pathlib import Path
import json,urllib.request,struct,collections
from vibfpga.mimii import fetch_range,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    out=ROOT/'data/mimii-due-source-review';out.mkdir(exist_ok=False)
    with urllib.request.urlopen('https://zenodo.org/api/records/4740355',timeout=60) as response:meta=json.load(response)
    archive=next(f for f in meta['files'] if f['key']=='dev_data_fan.zip');url=archive['links']['self'];size=archive['size']
    (out/'archive.json').write_text(json.dumps(archive,indent=2)+'\n')
    tail=fetch_range(url,size-65557,65557);pos=tail.rfind(b'PK\x05\x06');assert pos>=0
    eocd=struct.unpack('<4s4H2IH',tail[pos:pos+22]);count=eocd[4];length=eocd[5];offset=eocd[6];assert count!=65535 and offset+length<=size
    central=fetch_range(url,offset,length);entries=[];p=0
    while p<len(central):
        v=struct.unpack('<4s6H3I5H2I',central[p:p+46]);assert v[0]==b'PK\x01\x02'
        name=central[p+46:p+46+v[10]].decode();entries.append({'name':name,'size':v[9],'compressed':v[8],'crc':v[7],'method':v[4],'offset':v[16]});p+=46+v[10]+v[11]+v[12]
    assert len(entries)==count
    groups=collections.Counter();non_audio=[]
    for e in entries:
        name=e['name']
        if name.endswith('.wav'):
            stem=Path(name).stem;tokens=stem.split('_');section='_'.join(tokens[:2]);domain=tokens[2] if len(tokens)>2 else '?';split=Path(name).parent.name;state='abnormal' if 'anomaly' in tokens or 'abnormal' in tokens else ('normal' if 'normal' in tokens else 'unlabeled');groups[(section,domain,split,state)]+=1
        elif not name.endswith('/'):non_audio.append(e)
    (out/'inventory.json').write_text(json.dumps({'entries':entries,'central_sha256':sha(central),'audio_opened':False},indent=2)+'\n')
    report={'archive_bytes':size,'central_bytes_read':len(central),'tail_bytes_read':len(tail),'audio_opened':False,'groups':[{'section':k[0],'domain':k[1],'split':k[2],'state':k[3],'count':v} for k,v in sorted(groups.items())],'non_audio':non_audio,'examples':[e['name'] for e in entries if e['name'].endswith('.wav')][:5]}
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
