#!/usr/bin/env python3
"""Report saved feasibility results without retraining or reading test waveforms."""
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=ROOT/'artifacts/acoustic-v2-analysis';out.mkdir(exist_ok=False)
    studies=[]
    for tag in ['acoustic-v2-study','acoustic-v2-logpower']:
        p=ROOT/'artifacts'/tag;r=read(p/'receipt.json');protocol=read(p/'protocol.json')
        for rel,h in r['sha256'].items():
            if digest(ROOT/rel)!=h:raise ValueError('study artifact changed: '+rel)
        for rel,h in protocol['source_sha256'].items():
            if digest(ROOT/rel)!=h:raise ValueError('study source changed: '+rel)
        studies.append(read(p/'validation.json'))
    rows=[]
    for compression,study in zip(['log1p','logpower'],studies):
        for r in study['candidates']:
            # Comparative operation counts, not timing/area promises. Mean includes division/shift.
            d=r['dimension'];kind=r['model'];h=min(16,max(8,d//4))
            row={k:r[k] for k in ['name','features','context','dimension','model','auc','fpr','recall','alarm_fpr','alarm_recall','context_ms','earliest_3window_alarm_ms','weights_or_parameters']}
            row.update(compression=compression,score_multiplications=(2*d*h+d if kind=='ae' else d*(2 if kind=='diagonal_mahalanobis' else 1)),
                       context_storage_bytes_if_int8=d,parameter_bytes_if_float32=4*r['weights_or_parameters'])
            rows.append(row)
    with (out/'comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    # Resolve floating-point AUC equality at 1e-12; do not pay for longer context for numerical noise.
    selected=max(rows,key=lambda r:(round(r['recall'],12) if r['fpr']<=.05 else -1,round(r['auc'],12),-r['dimension'],-r['score_multiplications']))
    audit=read(ROOT/'artifacts/acoustic-v2-study/input-audit.json')
    fig,ax=plt.subplots(2,1,figsize=(10,7),layout='constrained')
    hz=np.arange(513)*15.625
    for group in audit['groups']:
        ax[0].plot(hz,10*np.log10(np.maximum(group['mean_spectrum'],1e-14)),label=group['group'])
    for b in audit['sparse_bins']:ax[0].axvspan((b-.5)*15.625,(b+.5)*15.625,color='grey',alpha=.10)
    ax[0].set(xlabel='Frequency (Hz)',ylabel='Mean power (dB, relative)',title='Full spectrum; grey strips are the old 48 selected bins');ax[0].legend()
    names=['sparse16','uniform16','uniform32','mel16','mel32']
    xpos=np.arange(5)
    for offset,model in enumerate(['centroid','diagonal_mahalanobis','ae']):
        vals=[next(r['recall'] for r in rows if r['compression']=='log1p' and r['name']==n+'-log-c1-'+model) for n in names]
        ax[1].bar(xpos+(offset-1)*.25,vals,width=.25,label=model)
    ax[1].axhline(.5,color='red',linestyle='--',label='recall gate (AUC gate also required)')
    ax[1].set(xticks=xpos,xticklabels=names,ylabel='Abnormal clips detected / 30',ylim=(0,.65),title='Single-window log1p features, validation clip FPR = 5%');ax[1].legend(fontsize=8,ncol=2)
    fig.savefig(out/'feature-comparison.png',dpi=160);plt.close(fig)
    hardware={'scope':'operation estimates only; no new RTL/synthesis/board result','old_selected_dft_bins':48,'full_non_dc_bins':512,
      'existing_l1_dft_cycles_48_bins':295104,'naive_full_l1_dft_cycles_estimate':295104*512/48,
      'naive_full_l1_dft_ms_at_nominal_12MHz':295104*512/48/12000,
      'ideal_quarter_of_that_ms_not_implemented':295104*512/48/12000/4,
      'window_ms':64,'radix2_complex_1024_fft_butterflies':5120,'generic_four_real_mults_per_butterfly_upper_count':20480,
      'caveats':'FFT count omits memory/control overhead and scaling; real-input/pruned FFT can differ. Neither cycle count nor fit established. Existing sparse DFT expanded directly is unattractive.'}
    summary={'engineering_candidate':selected,'tie_rule':'AUC/recall rounded to 1e-12 for ties, then lower feature dimension and multiplication count',
      'quality_gate_passed':selected['auc']>=.8 and selected['recall']>=.5,'total_candidates':len(rows),'test_opened':False,
      'quantization_started':False,'rtl_changed':False,'hardware_estimate':hardware,
      'studies':{str(ROOT/'artifacts'/tag/'receipt.json'):digest(ROOT/'artifacts'/tag/'receipt.json') for tag in ['acoustic-v2-study','acoustic-v2-logpower']}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
