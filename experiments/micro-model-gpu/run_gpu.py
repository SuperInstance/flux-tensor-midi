"""GPU micro model training — vectorized, fast"""
import torch, torch.nn as nn, torch.optim as optim
import numpy as np, json, os, time

device = torch.device('cuda')
_print = print
def print(*a, **k): _print(*a, **k, flush=True)
OUT = "/home/phoenix/.openclaw/workspace/experiments/micro-model-gpu"
os.makedirs(OUT, exist_ok=True)
print(f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB")

# Fast data gen
np.random.seed(42)
N = 1000
# Drift data
X_d = np.zeros((N, 160)); y_d = np.zeros(N, dtype=int)
for i in range(N):
    if np.random.random() < 0.5:
        X_d[i] = (np.random.randn(20,8)*0.1 + np.random.randn(8)).flatten(); y_d[i]=0
    else:
        X_d[i] = (np.random.randn(20,8)*0.3 + np.linspace(0,1,20)[:,None]*np.random.randn(1,8)*2).flatten(); y_d[i]=1

X_d = torch.FloatTensor(X_d); y_d = torch.LongTensor(y_d)
Xtr, Xte = X_d[:800].to(device), X_d[800:].to(device)
ytr, yte = y_d[:800].to(device), y_d[800:].to(device)

# Simple model
M = nn.Sequential(nn.Linear(160,64),nn.ReLU(),nn.Linear(64,2)).to(device)
opt = optim.Adam(M.parameters(), lr=0.01)
crit = nn.CrossEntropyLoss()

# GPU train
torch.cuda.synchronize(); t0=time.time()
for _ in range(50):
    opt.zero_grad(); crit(M(Xtr),ytr).backward(); opt.step()
torch.cuda.synchronize(); gpu_t=time.time()-t0
M.eval()
with torch.no_grad(): gpu_acc=(M(Xte).argmax(1)==yte).float().mean().item()
vram=torch.cuda.max_memory_allocated()/1e9; torch.cuda.reset_peak_memory_stats()

# CPU train
Mc=nn.Sequential(nn.Linear(160,64),nn.ReLU(),nn.Linear(64,2))
oc=optim.Adam(Mc.parameters(),lr=0.01)
Xc,yc=X_d[:800],y_d[:800]
t0=time.time()
for _ in range(50):
    oc.zero_grad(); crit(Mc(Xc),yc).backward(); oc.step()
cpu_t=time.time()-t0
Mc.eval()
with torch.no_grad(): cpu_acc=(Mc(X_d[800:]).argmax(1)==y_d[800:]).float().mean().item()

print(f"\n=== Drift-Detect ===")
print(f"  GPU: acc={gpu_acc:.4f}, {gpu_t:.3f}s, VRAM={vram:.3f}GB")
print(f"  CPU: acc={cpu_acc:.4f}, {cpu_t:.3f}s, speedup={cpu_t/gpu_t:.1f}x")

# Intent data
X_i=np.zeros((N,160)); y_i=np.zeros(N,dtype=int)
for i in range(N):
    l=np.random.randint(4)
    if l==0: X_i[i]=(np.random.randn(10,16)*0.5).flatten()
    elif l==1: X_i[i]=(np.random.randn(10,16)*1.5).flatten()
    elif l==2: X_i[i]=np.tile(np.random.randn(16)*0.1,10)
    else: X_i[i]=np.cumsum(np.random.randn(160))*0.3
    y_i[i]=l
Xi=torch.FloatTensor(X_i).to(device); yi=torch.LongTensor(y_i).to(device)
M2=nn.Sequential(nn.Linear(160,128),nn.ReLU(),nn.Linear(128,4)).to(device)
o2=optim.Adam(M2.parameters(),lr=0.01)
for _ in range(50):
    o2.zero_grad(); crit(M2(Xi[:800]),yi[:800]).backward(); o2.step()
M2.eval()
with torch.no_grad(): intent_acc=(M2(Xi[800:]).argmax(1)==yi[800:]).float().mean().item()
print(f"\n=== Intent-Detect (4-class) ===")
print(f"  GPU: acc={intent_acc:.4f}")

# Spectral conservation during training
print(f"\n=== Spectral Conservation During Training ===")
for lr_v, lr_n in [(0.01,'lr=0.01'),(0.001,'lr=0.001')]:
    M3=nn.Sequential(nn.Linear(160,64),nn.ReLU(),nn.Linear(64,2)).to(device)
    o3=optim.Adam(M3.parameters(),lr=lr_v)
    I_hist=[]
    for ep in range(100):
        W=list(M3.parameters())[0]
        G=W.T@W; ev=torch.linalg.eigvalsh(G); pos=ev[ev>1e-10]
        if len(pos)>=2:
            s=torch.sort(pos,descending=True)[0]
            g=s[0]-s[1]; tot=torch.sum(s); p=s/tot; m=p>1e-15
            I_hist.append((g-torch.sum(p[m]*torch.log(p[m]))).item())
        o3.zero_grad(); crit(M3(Xtr),ytr).backward(); o3.step()
    arr=np.array(I_hist)
    cv=np.std(arr[5:])/abs(np.mean(arr[5:])) if abs(np.mean(arr[5:]))>1e-12 else 999
    drift=abs(arr[-1]-arr[0])/abs(arr[0])
    print(f"  {lr_n}: CV={cv:.6f}, drift={drift:.4f}, I: {arr[0]:.2f}→{arr[-1]:.2f}")

# Escalation Gate
print(f"\n=== Escalation Gate ===")
n=3000
Xd2=np.zeros((n,5)); yd2=np.zeros(n)
for i in range(n):
    conf=np.random.random(); dr=np.random.exponential(0.1); anom=np.random.random()
    Xd2[i]=[conf,np.random.poisson(5),dr,anom,np.random.exponential(10)]
    esc=(conf<0.4 and dr>0.15) or anom>0.8
    if np.random.random()<0.05: esc=not esc
    yd2[i]=int(esc)
Xe=torch.FloatTensor(Xd2).to(device); ye=torch.FloatTensor(yd2).to(device)
G=nn.Sequential(nn.Linear(5,32),nn.ReLU(),nn.Linear(32,16),nn.ReLU(),nn.Linear(16,1),nn.Sigmoid()).to(device)
og=optim.Adam(G.parameters(),lr=0.01); cg=nn.BCELoss()
for _ in range(80):
    og.zero_grad(); cg(G(Xe[:2400]).squeeze(),ye[:2400]).backward(); og.step()
G.eval()
with torch.no_grad():
    pr=(G(Xe[2400:]).squeeze()>0.5).float()
    ea=(pr==ye[2400:]).float().mean().item()
    ae=ye[2400:]==1
    caught=(pr[ae]==1).float().mean().item()
    fp=(pr[ye[2400:]==0]==1).float().mean().item()
    er=pr.float().mean().item()
params=sum(p.numel() for p in G.parameters())
print(f"  Accuracy: {ea:.4f}")
print(f"  Caught escalations: {caught*100:.1f}%")
print(f"  False positives: {fp*100:.1f}%")
print(f"  Escalation rate: {er*100:.1f}%")
print(f"  Model: {params} params ({params*4}B) — WASM-ready")

# GPU spectral scale
print(f"\n=== GPU Spectral Scale ===")
for N_sz in [32,64,128,256]:
    torch.cuda.empty_cache()
    x=torch.randn(N_sz,device=device)*0.5; Iv=[]
    torch.cuda.synchronize(); t0=time.time()
    for t in range(50):
        C=torch.outer(x,x)/N_sz+torch.eye(N_sz,device=device)*0.01; C=(C+C.T)/2
        ev=torch.linalg.eigvalsh(C); pos=ev[ev>1e-10]
        if len(pos)>=2:
            s=torch.sort(pos,descending=True)[0]
            g=s[0]-s[1]; tot=torch.sum(s); p=s/tot; m=p>1e-15
            Iv.append((g-torch.sum(p[m]*torch.log(p[m]))).item())
        x=torch.tanh(C@x)
    torch.cuda.synchronize(); el=time.time()-t0
    cv=np.std(Iv[3:])/abs(np.mean(Iv[3:])) if abs(np.mean(Iv[3:]))>1e-12 else 999
    mem=torch.cuda.max_memory_allocated()/1e9
    print(f"  N={N_sz:4d}: CV={cv:.6f}, {el:.3f}s, VRAM={mem:.2f}GB")
    torch.cuda.reset_peak_memory_stats()

with open(os.path.join(OUT,'results.json'),'w') as f:
    json.dump({'drift_gpu_acc':float(gpu_acc),'drift_cpu_acc':float(cpu_acc),
        'gpu_speedup':float(cpu_t/gpu_t),'intent_acc':float(intent_acc),
        'esc_acc':float(ea),'esc_caught':float(caught),'esc_fp':float(fp),
        'esc_params':params,'vram_used':float(vram)},f,indent=2)
print("\nDone!")
