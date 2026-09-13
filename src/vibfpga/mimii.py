"""Bounded official MIMII subset, frozen whole-record splits and range extraction."""
import hashlib, io, json, struct, time, urllib.request, wave, zlib
from pathlib import Path
import numpy as np

def sha(b): return hashlib.sha256(b).hexdigest()

def make_plan(index, archive):
    counts={"normal": {"train":120,"validation":40,"test":40}, "abnormal":{"validation":30,"test":50}}
    records=[]
    for label,splits in counts.items():
        candidates=[x for x in index if x['name'].startswith(f'fan/id_00/{label}/')]
        candidates.sort(key=lambda x: sha(('mimii-fan-v1:'+x['name']).encode()))
        pos=0
        for split,count in splits.items():
            if pos+count>len(candidates): raise ValueError('insufficient official records')
            for info in candidates[pos:pos+count]:
                records.append({**info,'label':int(label=='abnormal'),'split':split,
                    'local':f"pcm/{label}_{Path(info['name']).stem}.npy"})
            pos+=count
    return {'schema_version':1,'dataset':'MIMII public 1.0','source':'https://zenodo.org/records/3384388',
        'license':'CC-BY-SA-4.0; cite Purohit et al., 2019','archive':archive,'machine':'fan/id_00',
        'snr_db':0,'channel':0,'sample_rate_hz':16000,'seed':'mimii-fan-v1',
        'split_unit':'whole official WAV, all channels and derived windows stay together',
        'scope':'single machine ID and SNR feasibility; not cross-machine or independent-session evidence',
        'training':'normal only; labeled validation may select features/model; test locked until freeze',
        'window_n':1024,'window_hop':1024,'clip_pooling':'mean window anomaly score',
        'threshold':'95th percentile of normal validation clip scores; strict score > threshold',
        'alarm_windows':3,'feasibility_target':{'validation_auc':0.8,'validation_recall_at_threshold':0.5},
        'records':records}

def validate_plan(p):
    names=[x['name'] for x in p['records']]
    if len(names)!=len(set(names)):raise ValueError('record leakage/duplicate')
    if any(x['label'] for x in p['records'] if x['split']=='train'):raise ValueError('abnormal training input')
    if {x['split'] for x in p['records']} != {'train','validation','test'}:raise ValueError('missing split')
    return True

def fetch_range(url,start,length):
    for attempt in range(5):
        try:
            req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{start+length-1}'})
            with urllib.request.urlopen(req,timeout=90) as response:
                expected=f'bytes {start}-{start+length-1}/'
                if response.status!=206 or not response.headers.get('Content-Range','').startswith(expected):
                    raise ValueError('server did not honor byte range')
                blob=response.read(length+1)
                if len(blob)!=length:raise ValueError('range length mismatch')
                return blob
        except Exception:
            if attempt==4:raise
            time.sleep(2**attempt)

def extract_record(info,url):
    # Bound the request to this member plus its local header; no ZIP paths extracted.
    start=info['offset']; header=fetch_range(url,start,30)
    fields=struct.unpack('<4s5H3I2H',header)
    if fields[0]!=b'PK\x03\x04' or fields[3]!=info['method']:raise ValueError('wrong ZIP local header')
    name_n,extra_n=fields[-2:]
    blob=fetch_range(url,start+30,name_n+extra_n+info['compressed'])
    if blob[:name_n].decode()!=info['name']:raise ValueError('ZIP name mismatch')
    packed=blob[name_n+extra_n:]
    raw=zlib.decompress(packed,-15) if info['method']==8 else packed
    if len(raw)!=info['size'] or zlib.crc32(raw)!=info['crc']:raise ValueError('ZIP member CRC/length mismatch')
    with wave.open(io.BytesIO(raw)) as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(8,2,16000):raise ValueError('unexpected WAV format')
        pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,8)[:,0].copy()
    return pcm,{'original_wav_sha256':sha(raw),'archive_member_crc32':f"{info['crc']:08x}",
        'range_bytes':len(blob)+30,'frames':len(pcm),'channel':0,'original_channels':8,'sample_rate_hz':16000}
