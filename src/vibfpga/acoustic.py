"""Bit-exact normal-only acoustic autoencoder and deterministic temporal alarm."""
import numpy as np
from .fixed import frontend,round_shift_even

def log_features(powers):
    """Unsigned exponent + two mantissa bits: 4*floor(log2(p)) + fraction, zero->0."""
    a=np.asarray(powers,dtype=np.int64)
    if np.any(a<0) or np.any(a>=1<<33):raise ValueError('power out of 33-bit range')
    flat=[]
    for value in a.flat:
        p=int(value)
        if p==0:flat.append(0);continue
        e=p.bit_length()-1
        fraction=((p-(1<<e))*4)>>e
        flat.append(min(127,4*e+fraction))
    return np.array(flat,dtype=np.int64).reshape(a.shape)

def features_from_powers(powers,model):
    if model.get('acoustic_encoding')=='log4':return log_features(powers)
    return np.stack([np.clip(round_shift_even(np.asarray(powers)[...,i],int(s)),0,127) for i,s in enumerate(model['feature_shifts'])],axis=-1)

def infer(features,model):
    x=np.asarray(features,dtype=np.int64)
    if x.shape!=(16,) or np.any(x<0) or np.any(x>127):raise ValueError('expected sixteen unsigned INT8 features')
    a=np.asarray(model['w1'],dtype=np.int64)@x+model['b1']
    if np.any(a < -(1<<31)) or np.any(a >= 1<<31):raise OverflowError('hidden INT32')
    h=np.clip(round_shift_even(np.maximum(a,0),model['hidden_shift']),0,127)
    b=np.asarray(model['w2'],dtype=np.int64)@h+model['b2']
    if np.any(b < -(1<<31)) or np.any(b >= 1<<31):raise OverflowError('output INT32')
    reconstruction=np.clip(round_shift_even(b,model['output_shift']),0,127)
    squared=(x-reconstruction)**2
    return {'features':x,'hidden_acc':a,'hidden':h,'output_acc':b,'reconstruction':reconstruction,
            'squared_errors':squared,'score':int(squared.sum())}

def classify(samples,model):
    result=frontend(samples,model)
    result['features']=features_from_powers(result['powers'],model)
    result.update(infer(result['features'],model));return result

class Alarm:
    def __init__(self,threshold,windows=3):
        if threshold<0 or windows<1:raise ValueError('invalid alarm settings')
        self.threshold=threshold;self.windows=windows;self.reset()
    def reset(self):self.count=0;self.last=None
    def accept(self,frame_id,score,error=False):
        if error or self.last is None or frame_id!=self.last+1:self.count=0
        self.count=min(self.windows,self.count+1) if not error and score>self.threshold else 0
        self.last=frame_id
        return self.count>=self.windows
