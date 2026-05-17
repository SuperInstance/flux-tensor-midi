"""
THE MODEL OCEAN — Scaled Up
Hundreds of cells, real evolution, real fitness

The ecosystem:
  🔬 Sandboxes: 100-200 cells, tiny (100 params), short-lived, high mutation
  🌊 Tide pools: 20-50 cells, small (300 params), task-specialized
  🐟 Schools: 5-15 cells, medium (850 params), self-organizing clusters
  🐋 Whales: 1-3 cells, large (2700 params), slow but deep

Population limit: 300 cells
Total params budget: ~100K (400KB) — fits in any device
"""
import torch, torch.nn as nn, torch.optim as optim
import numpy as np, json, os, time, hashlib, random
from collections import defaultdict

device = torch.device('cuda')
_p = print
def print(*a, **k): _p(*a, **k, flush=True)
OUT = "/home/phoenix/.openclaw/workspace/experiments/model-ocean"
os.makedirs(OUT, exist_ok=True)
print(f"GPU: {torch.cuda.get_device_name(0)}")
np.random.seed(42); random.seed(42)
torch.manual_seed(42)

# ============================================================
# Cell architecture — parameterized by niche
# ============================================================
CELL_CONFIGS = {
    'sandbox':   {'h': 8,  'life': 30,   'mut': 0.3, 'cost': 0.001},
    'tide_pool': {'h': 16, 'life': 200,  'mut': 0.1, 'cost': 0.005},
    'school':    {'h': 32, 'life': 1000, 'mut': 0.05,'cost': 0.01},
    'whale':     {'h': 64, 'life': 5000, 'mut': 0.01,'cost': 0.05},
}

class Cell(nn.Module):
    def __init__(self, cell_type, in_dim=8, out_dim=2, provenance=None):
        super().__init__()
        h = CELL_CONFIGS[cell_type]['h']
        self.cell_type = cell_type
        self.config = CELL_CONFIGS[cell_type]
        self.net = nn.Sequential(nn.Linear(in_dim,h),nn.ReLU(),nn.Linear(h,out_dim))
        self.fitness = 0.0
        self.age = 0
        self.generation = 0
        self.genome_id = hashlib.md5(f"{cell_type}:{time.time_ns()}:{random.random()}".encode()).hexdigest()[:8]
        self.parent_id = None
        self.provenance = provenance or []
    
    def forward(self, x): return self.net(x)
    
    @property
    def size(self): return sum(p.numel() for p in self.parameters())
    
    def clone_mutated(self, scale=0.05):
        child = Cell(self.cell_type)
        child.load_state_dict(self.state_dict())
        child.generation = self.generation + 1
        child.parent_id = self.genome_id
        child.provenance = self.provenance.copy()
        with torch.no_grad():
            for p in child.parameters():
                if random.random() < self.config['mut']:
                    p.add_(torch.randn_like(p) * scale)
        return child.to(device)

# ============================================================
# Data — multiple task streams from PLATO rooms
# ============================================================
def make_task_stream(task, n=200):
    """Each PLATO room produces a different classification task"""
    X = np.zeros((n, 8)); y = np.zeros(n, dtype=int)
    if task == 'drift':
        for i in range(n):
            drift = np.random.exponential(0.3)
            X[i] = [np.random.random(), drift, np.random.random(),
                     np.random.poisson(5), np.random.random(),
                     np.random.random(), np.random.exponential(0.5), np.random.random()]
            y[i] = int(drift > 0.4)
    elif task == 'anomaly':
        for i in range(n):
            is_anom = np.random.random() < 0.15
            X[i] = [np.random.random()*(5 if is_anom else 1),
                     np.random.exponential(1), np.random.random(),
                     np.random.random()*(3 if is_anom else 0.5),
                     np.random.random(), np.random.random(), np.random.random(),
                     np.random.exponential(0.3)]
            y[i] = int(is_anom)
    elif task == 'intent':
        for i in range(n):
            intent = np.random.randint(4)
            scales = [0.5, 1.5, 0.1, 2.0]
            X[i] = np.random.randn(8) * scales[intent]
            y[i] = intent
    elif task == 'priority':
        for i in range(n):
            pri = np.random.randint(3)
            X[i] = [np.random.random(), np.random.random(), pri/2,
                     np.random.random(), np.random.random(), np.random.random(),
                     np.random.random(), np.random.random()]
            y[i] = pri
    elif task == 'relevance':
        for i in range(n):
            rel = np.random.random() < 0.6
            X[i] = [np.random.random()*(2 if rel else 0.5),
                     np.random.random(), np.random.random()*(1.5 if rel else 0.3),
                     np.random.random(), np.random.random(), np.random.random(),
                     np.random.random(), np.random.random()]
            y[i] = int(rel)
    return torch.FloatTensor(X).to(device), torch.LongTensor(y).to(device)

# Map tasks to rooms
TASK_ROOMS = {
    'drift': 'room-drift-detect',
    'anomaly': 'room-anomaly-flag',
    'intent': 'room-intent-classify',
    'priority': 'room-priority-rank',
    'relevance': 'room-tile-relevance',
}

# ============================================================
# The Ocean
# ============================================================
MAX_POP = 300

class Ocean:
    def __init__(self):
        self.cells = []
        self.tick = 0
        self.history = []
    
    def add(self, cell):
        if len(self.cells) < MAX_POP:
            self.cells.append(cell.to(device))
    
    def train_tick(self, X, y, task_name):
        """All cells train on current data, compete for fitness"""
        self.tick += 1
        
        # Batch train ALL cells in parallel (vectorized)
        new_cells = []
        for cell in self.cells:
            cell.age += 1
            if cell.age > cell.config['life']:
                continue  # die of old age
            
            # Train on this batch — 5 steps
            opt = optim.Adam(cell.parameters(), lr=0.01)
            for _ in range(5):
                opt.zero_grad()
                out = cell(X)
                if out.shape[-1] != y.shape[-1]:
                    break
                loss = nn.functional.cross_entropy(out, y)
                loss.backward()
                opt.step()
            
            # Evaluate fitness
            with torch.no_grad():
                try:
                    pred = cell(X).argmax(1)
                    cell.fitness = (pred == y).float().mean().item()
                except:
                    cell.fitness = 0.0
            
            new_cells.append(cell)
            
            # Reproduction — fit cells spawn offspring
            if cell.fitness > 0.75 and random.random() < cell.config['mut'] * 0.5:
                if len(new_cells) < MAX_POP:
                    child = cell.clone_mutated(0.05)
                    child.provenance.append(f"{TASK_ROOMS.get(task_name,'?')}:tick{self.tick}")
                    new_cells.append(child)
        
        self.cells = new_cells
    
    def promote(self):
        """Promote successful cells to next niche level"""
        promoted = []
        for i, cell in enumerate(self.cells):
            if cell.cell_type == 'sandbox' and cell.fitness > 0.85 and cell.age > 8:
                p = Cell('tide_pool')
                # Copy weights where possible (different sizes, so just init fresh with provenance)
                p.provenance = cell.provenance + [f'promoted:sandbox→tide_pool@tick{self.tick}']
                p.generation = cell.generation
                p.fitness = cell.fitness
                promoted.append((i, p.to(device)))
            elif cell.cell_type == 'tide_pool' and cell.fitness > 0.9 and cell.age > 50:
                p = Cell('school')
                p.provenance = cell.provenance + [f'promoted:tide_pool→school@tick{self.tick}']
                p.generation = cell.generation
                p.fitness = cell.fitness
                promoted.append((i, p.to(device)))
        
        for idx, p in promoted:
            self.cells[idx] = p.to(device)
    
    def census(self):
        counts = defaultdict(int)
        fit_sum = defaultdict(float)
        param_sum = defaultdict(int)
        best_fit = defaultdict(float)
        max_gen = defaultdict(int)
        
        for c in self.cells:
            counts[c.cell_type] += 1
            fit_sum[c.cell_type] += c.fitness
            param_sum[c.cell_type] += c.size
            best_fit[c.cell_type] = max(best_fit[c.cell_type], c.fitness)
            max_gen[c.cell_type] = max(max_gen[c.cell_type], c.generation)
        
        return counts, fit_sum, param_sum, best_fit, max_gen
    
    def summary(self):
        counts, fit_sum, param_sum, best_fit, max_gen = self.census()
        total = sum(counts.values())
        total_p = sum(param_sum.values())
        emoji = {'sandbox':'🔬','tide_pool':'🌊','school':'🐟','whale':'🐋'}
        
        lines = [f"  Tick {self.tick:3d}: {total} cells | {total_p:,} params ({total_p*4/1024:.1f}KB)"]
        for ct in ['sandbox','tide_pool','school','whale']:
            if counts[ct] > 0:
                af = fit_sum[ct]/counts[ct]
                lines.append(f"    {emoji[ct]} {ct:10s}: {counts[ct]:3d} cells | fit={af:.3f} best={best_fit[ct]:.3f} | gen={max_gen[ct]} | {param_sum[ct]:,} params")
        return '\n'.join(lines)

# ============================================================
# RUN THE OCEAN
# ============================================================
print("="*60)
print("THE MODEL OCEAN — Cellular Intelligence Ecosystem")
print("="*60)

ocean = Ocean()

# Colonize
print("\n=== Colonization ===")
for _ in range(80):
    ocean.add(Cell('sandbox', provenance=['room-experimental']))
for task in TASK_ROOMS:
    for _ in range(5):
        ocean.add(Cell('tide_pool', provenance=[TASK_ROOMS[task]]))
for _ in range(3):
    ocean.add(Cell('school', provenance=['room-fleet-coord','room-strategy']))
ocean.add(Cell('whale', provenance=['room-deep-reasoning']))

print(ocean.summary())

# Evolution loop — 100 ticks, cycling through tasks
print("\n=== Evolution ===")
tasks = list(TASK_ROOMS.keys())

t0 = time.time()
for tick in range(100):
    # Pick a task stream — rotate through rooms
    task = tasks[tick % len(tasks)]
    X, y = make_task_stream(task, 100)
    
    ocean.train_tick(X, y, task)
    
    # Promotion every 10 ticks
    if (tick+1) % 10 == 0:
        ocean.promote()
    
    # Inject new sandboxes periodically
    if (tick+1) % 5 == 0 and len(ocean.cells) < MAX_POP:
        for _ in range(5):
            ocean.add(Cell('sandbox', provenance=['room-experimental']))
    
    if (tick+1) % 25 == 0:
        print(ocean.summary())

elapsed = time.time() - t0
print(f"\n  Evolution took {elapsed:.1f}s")

# ============================================================
# Final Census
# ============================================================
print("\n" + "="*60)
print("FINAL ECOSYSTEM")
print("="*60)
print(ocean.summary())

# ============================================================
# Collective Decision — The Ocean Votes
# ============================================================
print("\n" + "="*60)
print("COLLECTIVE DECISION — The Ocean Decides")
print("="*60)

# Test on each task
for task in tasks:
    Xt, yt = make_task_stream(task, 50)
    
    # Every cell votes
    type_weights = {'sandbox': 0.5, 'tide_pool': 1.0, 'school': 1.5, 'whale': 2.0}
    votes = defaultdict(float)
    individual_acc = []
    
    for cell in ocean.cells:
        try:
            with torch.no_grad():
                out = cell(Xt)
                if out.shape[-1] != yt.shape[-1]:
                    continue
                pred = out.argmax(1)
                acc = (pred == yt).float().mean().item()
                w = cell.fitness * type_weights[cell.cell_type]
                
                # Each cell votes for the majority class it predicts
                majority = pred.bincount().argmax().item()
                votes[majority] += w
                individual_acc.append(acc)
        except:
            pass
    
    total_v = sum(votes.values()) or 1
    decision = max(votes, key=votes.get) if votes else -1
    
    # Individual accuracy vs collective
    if individual_acc:
        print(f"\n  {task}: {len(individual_acc)} cells voted")
        print(f"    Avg individual acc: {np.mean(individual_acc):.3f}")
        print(f"    Best individual: {max(individual_acc):.3f}")
        print(f"    Collective decision: class {decision}")
        print(f"    True distribution: {yt.bincount().tolist()}")

# Save
counts, fit_sum, param_sum, best_fit, max_gen = ocean.census()
results = {
    'total_cells': sum(counts.values()),
    'total_params': sum(param_sum.values()),
    'total_kb': sum(param_sum.values())*4/1024,
    'evolution_ticks': ocean.tick,
    'evolution_time_s': elapsed,
    'counts': dict(counts),
    'best_fitness': {k:float(v) for k,v in best_fit.items()},
    'max_generation': {k:int(v) for k,v in max_gen.items()},
}
with open(os.path.join(OUT, 'ocean_results.json'), 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nDone! Ecosystem in {elapsed:.1f}s")
