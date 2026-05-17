import torch
import torch.nn as nn
import torch.optim as optim
import json, os, time
import numpy as np

OUT = "/home/phoenix/.openclaw/workspace/experiments/micro-model-gpu"
os.makedirs(OUT, exist_ok=True)

device = torch.device('cuda')
print(f"GPU: {torch.cuda.get_device_name(0)}, VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f}GB")

# Task 1: drift-detect (binary: drifting vs stable room)
def generate_room_data(n_samples=2000, seq_len=20, n_features=8):
    X, y = [], []
    for _ in range(n_samples):
        if np.random.random() < 0.5:
            tiles = np.random.randn(seq_len, n_features) * 0.1 + np.random.randn(1, n_features)
            label = 0
        else:
            drift = np.outer(np.linspace(0, 1, seq_len), np.random.randn(n_features) * 2)
            tiles = np.random.randn(seq_len, n_features) * 0.3 + drift
            label = 1
        X.append(tiles)
        y.append(label)
    return torch.FloatTensor(np.array(X)), torch.LongTensor(y)

# Task 2: intent-detect (4-class: query, update, delete, create)
def generate_intent_data(n_samples=2000, seq_len=10, n_features=16):
    X, y = [], []
    intents = {
        0: lambda: np.random.randn(seq_len, n_features) * 0.5,
        1: lambda: np.random.randn(seq_len, n_features) * 1.5,
        2: lambda: np.zeros((seq_len, n_features)) + np.random.randn(1, n_features) * 0.1,
        3: lambda: np.cumsum(np.random.randn(seq_len, n_features) * 0.3, axis=0),
    }
    for _ in range(n_samples):
        label = np.random.randint(4)
        tiles = intents[label]()
        X.append(tiles)
        y.append(label)
    return torch.FloatTensor(X), torch.LongTensor(y)

class MicroModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, n_classes, model_type='dense'):
        super().__init__()
        self.type = model_type
        if model_type == 'dense':
            self.net = nn.Sequential(
                nn.Flatten(),
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, n_classes),
            )
        elif model_type == 'lstm':
            self.lstm = nn.LSTM(input_dim // 10, hidden_dim, batch_first=True)
            self.fc = nn.Linear(hidden_dim, n_classes)
    
    def forward(self, x):
        if self.type == 'dense':
            return self.net(x)
        else:
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :])

def train_and_eval(model, X_train, y_train, X_test, y_test, epochs=50, batch_size=64):
    model = model.to(device)
    X_train, y_train = X_train.to(device), y_train.to(device)
    X_test, y_test = X_test.to(device), y_test.to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    model.train()
    start = time.time()
    for epoch in range(epochs):
        perm = torch.randperm(len(X_train))
        for i in range(0, len(X_train), batch_size):
            batch_X = X_train[perm[i:i+batch_size]]
            batch_y = y_train[perm[i:i+batch_size]]
            optimizer.zero_grad()
            out = model(batch_X)
            loss = criterion(out, batch_y)
            loss.backward()
            optimizer.step()
    train_time = time.time() - start
    
    model.eval()
    with torch.no_grad():
        preds = model(X_test).argmax(dim=1)
        acc = (preds == y_test).float().mean().item()
    
    vram = torch.cuda.max_memory_allocated() / 1e9
    torch.cuda.reset_peak_memory_stats()
    
    return acc, train_time, vram

# ===== DRIFT DETECT =====
print("\n=== DRIFT DETECT ===")
X, y = generate_room_data(2000, 20, 8)
split = 1600
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# GPU
model_dense = MicroModel(20*8, 64, 2, 'dense')
acc_dd_gpu, t_gpu, vram_dd = train_and_eval(model_dense, X_train, y_train, X_test, y_test, epochs=50)
print(f"  Dense GPU: acc={acc_dd_gpu:.4f}, time={t_gpu:.3f}s, VRAM={vram_dd:.3f}GB")

# CPU
model_cpu = MicroModel(20*8, 64, 2, 'dense')
start = time.time()
Xc, yc = X_train.cpu(), y_train.cpu()
Xtc, ytc = X_test.cpu(), y_test.cpu()
opt = optim.Adam(model_cpu.parameters(), lr=0.001)
crit = nn.CrossEntropyLoss()
model_cpu.train()
for epoch in range(50):
    perm = torch.randperm(len(Xc))
    for i in range(0, len(Xc), 64):
        opt.zero_grad()
        out = model_cpu(Xc[perm[i:i+64]])
        loss = crit(out, yc[perm[i:i+64]])
        loss.backward()
        opt.step()
cpu_time = time.time() - start
model_cpu.eval()
with torch.no_grad():
    preds = model_cpu(Xtc).argmax(dim=1)
    cpu_acc = (preds == ytc).float().mean().item()
print(f"  CPU:       acc={cpu_acc:.4f}, time={cpu_time:.3f}s")
print(f"  GPU speedup: {cpu_time/t_gpu:.1f}x")

speedup_dd = cpu_time / t_gpu

# ===== SCALING TEST =====
print("\n=== SCALING TEST ===")
scale_results = []
for hidden in [64, 128, 256, 512]:
    model = MicroModel(20*8, hidden, 2, 'dense')
    acc, t, vram = train_and_eval(model, X_train, y_train, X_test, y_test, epochs=50)
    print(f"  hidden={hidden}: acc={acc:.4f}, time={t:.3f}s, VRAM={vram:.3f}GB")
    scale_results.append({'hidden': hidden, 'acc': acc, 'time': t, 'vram': vram})

# ===== INTENT DETECT =====
print("\n=== INTENT DETECT (4-class) ===")
X, y = generate_intent_data(2000, 10, 16)
split = 1600
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

model = MicroModel(10*16, 128, 4, 'dense')
acc_id, t_id, vram_id = train_and_eval(model, X_train, y_train, X_test, y_test, epochs=100)
print(f"  Dense: acc={acc_id:.4f}, time={t_id:.3f}s, VRAM={vram_id:.3f}GB")

# ===== SPECTRAL CONSERVATION =====
print("\n=== SPECTRAL CONSERVATION DURING TRAINING ===")
# Re-gen drift data
X, y = generate_room_data(2000, 20, 8)
split = 1600
X_train_d = X[:split].to(device)
y_train_d = y[:split].to(device)

model = MicroModel(20*8, 64, 2, 'dense').to(device)
opt = optim.Adam(model.parameters(), lr=0.001)
crit = nn.CrossEntropyLoss()

I_history = []
for epoch in range(100):
    W = list(model.parameters())[0]
    G = W.T @ W
    eigenvalues = torch.linalg.eigvalsh(G)
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) >= 2:
        s = torch.sort(pos, descending=True)[0]
        gamma = s[0] - s[1]
        total = torch.sum(s)
        p = s / total
        mask = p > 1e-15
        H = -torch.sum(p[mask] * torch.log(p[mask]))
        I_val = (gamma + H).item()
        I_history.append(I_val)
    
    perm = torch.randperm(len(X_train_d))
    for i in range(0, len(X_train_d), 64):
        opt.zero_grad()
        out = model(X_train_d[perm[i:i+64]])
        loss = crit(out, y_train_d[perm[i:i+64]])
        loss.backward()
        opt.step()

I_arr = np.array(I_history)
cv = np.std(I_arr[5:]) / abs(np.mean(I_arr[5:])) if abs(np.mean(I_arr[5:])) > 1e-12 else 999
drift = abs(I_arr[-1] - I_arr[0]) / abs(I_arr[0])
print(f"  Training I(x): CV={cv:.6f}, drift={drift:.4f}")
print(f"  I: {I_arr[0]:.2f} → {I_arr[-1]:.2f}")

# Save results
results = {
    'drift_detect_gpu_acc': acc_dd_gpu,
    'drift_detect_cpu_acc': cpu_acc,
    'gpu_speedup_vs_cpu': speedup_dd,
    'intent_detect_gpu_acc': acc_id,
    'intent_detect_time': t_id,
    'intent_detect_vram': vram_id,
    'training_conservation_cv': cv,
    'training_conservation_drift': drift,
    'spectral_I_start': I_arr[0],
    'spectral_I_end': I_arr[-1],
    'scale_results': scale_results,
}
with open(os.path.join(OUT, 'gpu_training_results.json'), 'w') as f:
    json.dump(results, f, indent=2)

print("\nDone!")
