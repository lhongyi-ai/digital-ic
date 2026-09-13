"""Transport semantics and corruption rejection, independent synthetic model/log."""
import json,struct
import numpy as np
import pytest
from vibfpga.board import build_replay_image, COMMIT
from vibfpga.acoustic_board import verify_acoustic_log

def test_reconstruction_score_alarm_and_corruption(tmp_path):
    # Zero input/features; reconstruction sixteen 1s -> SSE=16, alarm after 3 frames.
    model={'n':1024,'bins':list(range(1,17)),'feature_shifts':[0]*16,'input_shift':0,
           'profile':'mimii_fan_autoencoder','w1':[[0]*16]*16,'w2':[[0]*16]*16,
           'b1':[0]*16,'b2':[1]*16,'hidden_shift':0,'output_shift':0,'threshold':15,'alarm_windows':3}
    p=tmp_path/'model.json';p.write_text(json.dumps(model))
    image,_=build_replay_image(np.zeros((1,1024),dtype=np.int16),p,run_frames=4)
    log=bytearray(4096+4*64)
    struct.pack_into('<4sIII',log,0,b'VLG1',1,4,COMMIT)
    struct.pack_into('<8I',log,16,0,4096,4096,0,0,1,1000,4)
    for i in range(4):struct.pack_into('<16I',log,4096+i*64,i,16,15,min(i+1,3),int(i>=2),1,1,1,1,4,1,4096,4096,0,0,0)
    assert verify_acoustic_log(image,bytes(log),p)['checked_frames']==4
    for offset in [4096,4100,4104,4108,4112]:
        bad=bytearray(log);bad[offset]^=1
        with pytest.raises(ValueError):verify_acoustic_log(image,bytes(bad),p)
    model['threshold']=16;p.write_text(json.dumps(model))
    with pytest.raises(ValueError,match='model mismatch'):verify_acoustic_log(image,bytes(log),p)
