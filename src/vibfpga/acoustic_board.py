"""Interpret fixed VLG1 transport records as acoustic score/threshold/streak."""
import json,hashlib
from pathlib import Path
from .board import parse_replay_image,parse_result_log
from .acoustic import classify,Alarm

def verify_acoustic_log(image,log,model_path):
    raw=Path(model_path).read_bytes();m=json.loads(raw);meta,samples=parse_replay_image(image);p=parse_result_log(log)
    if hashlib.sha256(raw).hexdigest()!=meta['model_sha256']:raise ValueError('acoustic model mismatch')
    if m.get('profile')!='mimii_fan_autoencoder':raise ValueError('not an acoustic model')
    if not p['complete_without_reported_errors'] or p['record_count']!=meta['run_frames']:raise ValueError('incomplete acoustic replay')
    expected=[classify(x,m)['score'] for x in samples];alarm=Alarm(m['threshold'],m['alarm_windows'])
    for i,record in enumerate(p['records']):
        score=expected[i%len(expected)];flag=alarm.accept(i,score)
        if record['frame_id']!=i or record['error'] or record['logits']!=[score,m['threshold'],alarm.count] or record['class_id']!=int(flag):raise ValueError(f'acoustic frame {i} differs from integer reference')
    return {'passed':True,'checked_frames':len(p['records']),'model_sha256':hashlib.sha256(raw).hexdigest(),
        'input_image_sha256':hashlib.sha256(image).hexdigest(),'result_log_sha256':hashlib.sha256(log).hexdigest(),
        'record_semantics':['squared_reconstruction_error','window_threshold','consecutive_window_count'],
        'scope':'Acoustic numeric/alarm verification of supplied files; physical provenance recorded separately.'}
