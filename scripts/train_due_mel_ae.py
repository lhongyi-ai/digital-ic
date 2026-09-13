#!/usr/bin/env python3
"""DCASE-feature AE diagnostic on existing normal commissioning references."""
from pathlib import Path
import json
import numpy as np
import librosa
import torch
from torch import nn
from threadpoolctl import threadpool_limits
from train_due_three_sections import ROOT, BASE
from experiment_acoustic_v2 import dump, sha
from diagnose_acoustic_v3 import metrics


def features(pcm):
    mel = librosa.feature.melspectrogram(y=pcm.astype(np.float32)/32768,
        sr=16000, n_fft=1024, hop_length=512, n_mels=128, power=2,
        center=True, pad_mode="constant")
    logmel = (10*np.log10(mel+np.finfo(float).eps)).T
    return np.stack([logmel[i:i+5].reshape(-1) for i in range(len(logmel)-4)]).astype(np.float32)


def network():
    layers = []
    widths = [640,128,128,128,128,8,128,128,128,128]
    for a,b in zip(widths[:-1],widths[1:]):
        layers += [nn.Linear(a,b),nn.BatchNorm1d(b),nn.ReLU()]
    return nn.Sequential(*layers,nn.Linear(128,640))


def main():
    source = ROOT / "artifacts/acoustic-due-normal-reference-v1/results.json"
    prior = json.loads(source.read_text())
    out = ROOT / "artifacts/acoustic-due-mel-ae-v1"; out.mkdir(exist_ok=False)
    dump(out/"protocol.json", {
        "reference": "https://dcase.community/challenge2021/task-unsupervised-detection-of-anomalous-sounds",
        "task": "normal-reference commissioning diagnostic, not zero-shot or exact official reproduction",
        "differences": "153 normal fit recordings per section, separate 50 normal calibration records; per-section model; PyTorch; fixed seed; threshold maximum calibration normal",
        "features": "128 log-Mel bands, nfft1024 hop512, 5 frames, librosa constant center padding",
        "network": "640-128-128-128-128-8-128-128-128-128-640; BatchNorm/ReLU hidden",
        "training": "Adam lr .001, 100 epochs, batch512, shuffle, MSE; fixed last epoch",
        "score": "mean reconstruction MSE over every context of a recording",
        "source_results_sha256": sha(source), "script_sha256": sha(Path(__file__)),
        "versions": {"torch":torch.__version__,"librosa":librosa.__version__},
        "final_test_opened":False})
    def load(name):
        path=BASE/"pcm"/(Path(name).stem+".npy")
        assert sha(path)==prior["pcm_sha256"][str(path.relative_to(ROOT))]
        pcm=np.load(path,allow_pickle=False)
        assert pcm.dtype==np.int16 and pcm.shape==(160000,)
        return features(pcm)
    results=[]
    for section in prior["sections"]:
        torch.manual_seed(71); model=network()
        train=torch.from_numpy(np.concatenate([load(n) for n in section["reference"]]))
        optimizer=torch.optim.Adam(model.parameters(),lr=.001)
        losses=[]
        for epoch in range(100):
            model.train(); total=0.; count=0
            for ids in torch.randperm(len(train)).split(512):
                x=train[ids]; optimizer.zero_grad()
                loss=(model(x)-x).square().mean(); assert torch.isfinite(loss)
                loss.backward(); optimizer.step()
                total+=float(loss.detach())*len(x); count+=len(x)
            losses.append(total/count)
            if (epoch+1)%20==0: print(section["section"],epoch+1,losses[-1],flush=True)
        model.eval(); path=out/f"section-{section['section']}.pt"
        torch.save(model.state_dict(),path)
        restored=network(); restored.load_state_dict(torch.load(path,weights_only=True)); restored.eval()
        with torch.no_grad():
            torch.testing.assert_close(model(train[:16]),restored(train[:16]),rtol=0,atol=0)
            def score(name):
                x=torch.from_numpy(load(name)); return float((model(x)-x).square().mean())
            cal=[score(n) for n in section["calibration"]]
            scores=np.array([score(r["name"]) for r in section["records"]])
        y=np.array([r["label"] for r in section["records"]]); limit=max(cal)
        result=metrics(y,scores,limit)
        result.update(section=section["section"],scores=scores.tolist(),calibration_scores=cal,training_loss=losses,
            gate_passed=result["recall"]>.9 and result["fpr"]<.05 and result["auc"]>=.9)
        results.append(result); dump(out/"partial-results.json",results)
        print('RESULT',section["section"],result["recall"],result["fpr"],result["auc"],flush=True)
    dump(out/"results.json",{"sections":results,"all_passed":all(r["gate_passed"] for r in results)})


if __name__ == "__main__":
    torch.set_num_threads(2)
    with threadpool_limits(limits=2): main()
