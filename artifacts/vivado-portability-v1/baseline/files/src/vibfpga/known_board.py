"""Single-recording transport contract; all DSP and inference execute in RTL."""
import hashlib,struct,zlib
import numpy as np
INPUT_BASE=0x100000
LOG_BASE=0x300000
LOG_BYTES=4096
COMMIT=0xc04d17ed

def build_image(samples,model_bytes,period=750,*,n=1024,windows=156):
    raw=np.asarray(samples)
    if raw.ndim!=1 or len(raw)!=n*windows or not np.issubdtype(raw.dtype,np.integer):
        raise ValueError('Exactly one complete integer PCM recording is required')
    if np.any(raw< -32768) or np.any(raw>32767) or not 4<=period<=12000 or n*windows>159744:
        raise ValueError('PCM/period out of range')
    payload=raw.astype('<i2').tobytes()
    if len(payload)+64>0x200000:raise ValueError('Input would overlap log partition')
    header=struct.pack('<8I',0x3152534b,1,n,windows,period,len(payload),zlib.crc32(payload),0)
    return header+hashlib.sha256(model_bytes).digest()+payload

def parse_log(data,model_bytes,*,n=1024,windows=156,lanes=4,period=750,allow_error=False):
    if len(data)!=LOG_BYTES:raise ValueError('Read the entire 4 KiB log sector')
    w=struct.unpack('<64I',data[:256])
    if w[:6]!=(0x314c534b,1,n,windows,lanes,period) or w[63]!=COMMIT:
        raise ValueError('Uncommitted log or mismatched configuration')
    if zlib.crc32(data[:248])!=w[62]:raise ValueError('Log CRC mismatch')
    if data[128:160]!=hashlib.sha256(model_bytes).digest():raise ValueError('Model binding mismatch')
    if any(w[26:32]) or any(w[40:62]) or data[256:]!=b'\xff'*(LOG_BYTES-256):
        raise ValueError('Reserved bytes or trailing log sector modified')
    signed=lambda i:struct.unpack('<i',struct.pack('<I',w[i]))[0]
    result=dict(errors=w[8],generated=w[6],accepted=w[7],protocol_errors=w[9],score=signed(10),threshold=signed(11),
                classification=w[12],core_error=w[13],frame_id=w[14],cycles_pre=w[15],cycles_dft=w[16],
                cycles_power=w[17],cycles_nn=w[18],cycles_total=w[19],first_sample_tick=w[20],
                last_sample_tick=w[21],output_tick=w[22],expected_crc=w[23],actual_crc=w[24],max_queue=w[25])
    if w[8]:
        if not allow_error:raise ValueError(f'Explicit replay error flags {w[8]:#x}')
        return result
    if w[6]!=n*windows or w[7]!=n*windows or w[9] or w[13] or w[14] or w[23]!=w[24]:
        raise ValueError('Sample/protocol/CRC counter mismatch')
    if w[12]!=int(signed(10)>signed(11)) or sum(w[15:19])!=w[19]:raise ValueError('Result/cycle inconsistency')
    if w[21]-w[20]!=(n*windows-1)*period or w[22]<w[21] or not 32<=w[25]<=256:
        raise ValueError('Input cadence or output timing mismatch')
    return result
