/**
 * Escalation Gate — Pure JavaScript inference engine
 * 
 * 737 params, 3-layer MLP. No dependencies. Runs anywhere JS runs.
 * Can be compiled to WASM via emscripten, or used as-is.
 * 
 * Usage:
 *   const gate = new EscalationGate(weights);
 *   const prob = gate.predict(0.3, 5, 0.2, 0.9, 15.0);
 *   if (prob > 0.5) { /* escalate to LLM */ }
 */

class EscalationGate {
    /**
     * @param {Object} weights - { w0, b0, w1, b1, w2, b2 } Float32Arrays
     * w0: [32*5], b0: [32], w1: [16*32], b1: [16], w2: [1*16], b2: [1]
     */
    constructor(weights) {
        this.w = [weights.w0, weights.w1, weights.w2];
        this.b = [weights.b0, weights.b1, weights.b2];
        this.paramCount = this.w.reduce((s, w) => s + w.length, 0) 
                        + this.b.reduce((s, b) => s + b.length, 0);
    }

    /**
     * Run forward pass.
     * @param {Float32Array|number[]} input - [confidence, tile_count, drift_rate, anomaly_score, density]
     * @returns {number} escalation probability (0-1)
     */
    forward(input) {
        let x = new Float32Array(input);
        
        for (let i = 0; i < 3; i++) {
            const w = this.w[i];
            const b = this.b[i];
            const inSize = (i === 0) ? 5 : (i === 1) ? 32 : 16;
            const outSize = (i === 0) ? 32 : (i === 1) ? 16 : 1;
            
            const y = new Float32Array(outSize);
            for (let j = 0; j < outSize; j++) {
                let sum = b[j];
                for (let k = 0; k < inSize; k++) {
                    sum += x[k] * w[j * inSize + k];
                }
                // ReLU for layers 0,1; Sigmoid for layer 2
                if (i < 2) {
                    y[j] = Math.max(0, sum);
                } else {
                    y[j] = 1.0 / (1.0 + Math.exp(-sum));
                }
            }
            x = y;
        }
        
        return x[0];
    }

    /**
     * Predict with named inputs.
     */
    predict(confidence, tileCount, driftRate, anomalyScore, density) {
        return this.forward([confidence, tileCount, driftRate, anomalyScore, density]);
    }

    /**
     * Returns { escalate: bool, probability: number }
     */
    shouldEscalate(confidence, tileCount, driftRate, anomalyScore, density, threshold = 0.5) {
        const prob = this.predict(confidence, tileCount, driftRate, anomalyScore, density);
        return { escalate: prob > threshold, probability: prob };
    }
}

// For Node.js / WASM module export
if (typeof module !== 'undefined') {
    module.exports = { EscalationGate };
}

// For browser
if (typeof window !== 'undefined') {
    window.EscalationGate = EscalationGate;
}
