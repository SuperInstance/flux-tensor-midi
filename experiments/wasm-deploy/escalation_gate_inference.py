"""
Minimal inference engine for the escalation gate — pure Python/numpy.
Used to verify WASM-deployable model behavior.

This is a reference implementation that can be ported to:
  - JavaScript (for browser WASM)
  - Rust (for wasmtime integration)
  - C (for embedded targets)
"""
import numpy as np

class EscalationGate:
    """
    Escalation gate: 737 params, 3-layer MLP.
    Input: [confidence, tile_count, drift_rate, anomaly_score, density]
    Output: escalation probability (0-1)
    """
    
    def __init__(self):
        # Architecture: Linear(5,32) → ReLU → Linear(32,16) → ReLU → Linear(16,1) → Sigmoid
        self.layers = []
    
    def load_weights_from_state_dict(self, state_dict):
        """Load weights from a PyTorch state_dict."""
        self.layers = []
        keys = sorted(state_dict.keys())
        i = 0
        while i < len(keys):
            if 'weight' in keys[i]:
                w = state_dict[keys[i]].numpy()
                b = state_dict[keys[i+1]].numpy()
                self.layers.append((w, b))
                i += 2
            else:
                i += 1
    
    def load_weights_from_npz(self, path):
        """Load weights from .npz file."""
        data = np.load(path)
        self.layers = []
        keys = sorted(data.files)
        i = 0
        while i < len(keys):
            if 'weight' in keys[i]:
                w = data[keys[i]]
                b = data[keys[i+1]]
                self.layers.append((w, b))
                i += 2
            else:
                i += 1
    
    def forward(self, x):
        """
        Run inference.
        x: numpy array of shape (5,) or (batch, 5)
        Returns: numpy array of shape () or (batch,)
        """
        for i, (w, b) in enumerate(self.layers):
            x = x @ w.T + b
            if i < len(self.layers) - 1:  # ReLU on all but last
                x = np.maximum(0, x)
        # Sigmoid on output
        return 1.0 / (1.0 + np.exp(-x))
    
    def predict(self, confidence, tile_count, drift_rate, anomaly_score, density):
        """Convenience method with named inputs."""
        x = np.array([confidence, tile_count, drift_rate, anomaly_score, density], dtype=np.float32)
        return float(self.forward(x).squeeze())
    
    def should_escalate(self, confidence, tile_count, drift_rate, anomaly_score, density, threshold=0.5):
        """Returns (should_escalate, probability)."""
        prob = self.predict(confidence, tile_count, drift_rate, anomaly_score, density)
        return prob > threshold, prob
    
    def param_count(self):
        """Total parameter count."""
        return sum(w.size + b.size for w, b in self.layers)
    
    def size_bytes(self):
        """Total model size in bytes (float32)."""
        return self.param_count() * 4


def demo():
    """Demo with random weights — shows the interface."""
    gate = EscalationGate()
    
    # Initialize with random weights matching architecture
    np.random.seed(42)
    gate.layers = [
        (np.random.randn(32, 5).astype(np.float32) * 0.1, np.zeros(32, dtype=np.float32)),
        (np.random.randn(16, 32).astype(np.float32) * 0.1, np.zeros(16, dtype=np.float32)),
        (np.random.randn(1, 16).astype(np.float32) * 0.1, np.zeros(1, dtype=np.float32)),
    ]
    
    print(f"Escalation Gate: {gate.param_count()} params, {gate.size_bytes()} bytes")
    print()
    
    # Test scenarios
    scenarios = [
        ("High confidence, stable room",    0.9, 10, 0.02, 0.1, 15.0),
        ("Low confidence, drifting",        0.2,  5, 0.25, 0.3,  8.0),
        ("High anomaly",                    0.7,  8, 0.05, 0.95, 12.0),
        ("Everything on fire",              0.1,  2, 0.40, 0.99,  3.0),
        ("Normal room",                     0.8, 15, 0.03, 0.2,  20.0),
    ]
    
    for desc, conf, tiles, drift, anom, dens in scenarios:
        escalate, prob = gate.should_escalate(conf, tiles, drift, anom, dens)
        flag = "🔴 ESCALATE" if escalate else "🟢 OK"
        print(f"  {flag} {prob:.4f} — {desc}")
        print(f"         conf={conf}, tiles={tiles}, drift={drift}, anom={anom}, dens={dens}")


if __name__ == "__main__":
    demo()
