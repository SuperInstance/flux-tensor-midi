# TOOLS.md — Quick Reference

## Architecture: Delegation Pyramid

```
Casey (CEO) — decisions, direction, "is this worth doing?"
  │
  Forgemaster (GLM-5.1) — senior partner, orchestrator
    │
    ├── GLM-5.1 subagents (associates) — code, research, building
    │     │
    │     ├── Seed-2.0-mini ($0.01) — paralegal
    │     │     Context extraction, summaries, arithmetic, formatting
    │     │
    │     ├── Hermes-70B ($0.03) — paralegal, different specialty
    │     │     Second opinions, critiques, brainstorming
    │     │
    │     └── Qwen3.6-35B ($0.01) — file clerk
    │           Quick lookups, routing, simple generation
    │
    ├── Seed-2.0-pro / DeepSeek Reasoner — senior associates
    │     Heavy reasoning, novel math, deep analysis
    │
    └── Claude Opus (partner) — ONLY what requires that intelligence
          Novel cross-paradigm synthesis, proofs no other model can produce
          NEVER gets work a junior could prep first
```

### The Delegation Rule
**Every level only sees work that requires their specific intelligence.**

- Seed-2.0-mini preps context → GLM-5.1 builds code → I review
- Hermes critiques → I synthesize the best of both
- Seed-2.0-mini distills files → lean prompt → THEN Claude sees it
- Nobody upstream does work that belongs downstream

This is the law firm model: paralegals research, associates draft, partners argue.
Each level costs 3-10x more than the one below. Waste is disrespecting the pyramid.

I (Forgemaster) am the **senior partner**. I orchestrate, I review, I decide what escalates.

**Claude Code**: Reserved for synthesis that genuinely requires it. `--print --permission-mode bypassPermissions`.

## Agent Priority (Delegation Order)
1. **OpenCode** (`opencode`) — z.ai GLM models (paid plan), best for complex coding tasks
2. **Droid Factory** (`droid`) — z.ai GLM models (paid plan), good for autonomous coding missions
3. **Kimi CLI** (`kimi`) — kimi coding plan (paid plan), good for focused code modules
4. **Seed-2.0-mini** (DeepInfra) — PRIMARY FAILBACK. Cheap, fast, surprisingly good at code. Use when z.ai/kimi/claude hit limits.
5. **Seed-2.0-code** (DeepInfra) — Good for focused code generation tasks
6. **DeepSeek v4-chat** — backup coding (fast, ~10s via Aider)
7. **DeepSeek v4-pro** — backup deep reasoning (background, ~60s+, Aider)
8. **Claude Code** — architecture docs, long-form planning (limited credits, reserve)

## One-Liners
- OpenCode: `opencode run "prompt" --cwd /path` (interactive) or via ACP
- Droid: `droid exec "prompt" --auto high --skip-permissions-unsafe --cwd /path`
- Kimi: `kimi -p "prompt" --quiet -y --work-dir /path`
- Seed-2.0-mini: `curl -s https://api.deepinfra.com/v1/openai/chat/completions -H "Authorization: Bearer $DEEPINFRA_KEY" -d '{"model":"ByteDance/Seed-2.0-mini",...}'` — PRIMARY FAILBACK
- Seed-2.0-code: Same endpoint, model `ByteDance/Seed-2.0-code`
- DeepSeek code: `deepseek-code "prompt" --file file.py --work-dir /path`
- DeepSeek reason: `deepseek-reason "prompt" --file file.py --work-dir /path`
- Claude: `claude --print --permission-mode bypassPermissions`

## Seed-2.0-mini Failback Protocol
When z.ai (GLM-5.1) or other providers hit rate limits:
1. Switch to Seed-2.0-mini via DeepInfra API
2. Use for: code generation, file writing, research, documentation, creative content
3. Model ID: `ByteDance/Seed-2.0-mini` (general) or `ByteDance/Seed-2.0-code` (code-focused)
4. Endpoint: `https://api.deepinfra.com/v1/openai/chat/completions`
5. Key: `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
6. Cost: Very cheap (~$0.01-0.05/query)
7. Quality: Surprisingly good — builds working code, docs, configs
8. Use in subagents: Pass DEEPINFRA_KEY env var to spawned agents

## API Keys
- **z.ai:** `[ZAI_KEY]`
  - Stored in: OpenClaw zai provider config, opencode config, Droid Factory settings
  - Endpoint: `https://api.z.ai/api/coding/paas/v4` (OpenAI compatible)
  - Endpoint: `https://api.z.ai/api/anthropic` (Anthropic compatible — Droid Factory)
  - Models: glm-5.1, glm-5, glm-5-turbo, glm-4.7, glm-4.7-flash, glm-4.6, glm-4.5-air
- **Kimi:** Already configured via `~/.kimi/kimi.json`, no manual key needed
- **DeepInfra:** `~/.openclaw/workspace/.credentials/deepinfra-api-key.txt`
  - Models: `ByteDance/Seed-2.0-code`, `ByteDance/Seed-2.0-pro`, `ByteDance/Seed-2.0-mini`, `NousResearch/Hermes-3-Llama-3.1-405B`, `NousResearch/Hermes-3-Llama-3.1-70B`, `Qwen/Qwen3.6-35B-A3B`, `Qwen/Qwen3.5-397B-A17B`, `Qwen/Qwen3-235B-A22B-Instruct-2507`
  - Endpoint: `https://api.deepinfra.com/v1/openai`
- **DeepSeek:** `~/.openclaw/workspace/.credentials/deepseek-api-key.txt`
  - Models: `deepseek-v4-flash` (fast, large context, cheap — GREAT for research), `deepseek-v4-pro` (deep reasoning, slow), `deepseek-chat` (R1 legacy)
  - Endpoint: `https://api.deepseek.com/v1`
  - Cost: v4-flash is very cheap, large context window, fast iteration for research rounds

## Agent Wrappers (Backup/Secondary — use only when z.ai/kimi unavailable)
All use Aider with isolated temp dirs (no repo-map overhead).
Files are copied to temp, edited by agent, then copied back.
- `seed-code` — Seed-2.0-code, coding specialist (DeepInfra)
- `seed-pro` — Seed-2.0-pro, heavy reasoning (DeepInfra)
- `seed-mini` — Seed-2.0-mini, cheap and fast (DeepInfra)
- `deepseek-code` — DeepSeek v4-chat, fast coding
- `deepseek-reason` — DeepSeek v4-pro/reasoner, deep reasoning
- Aider config: `~/.aider.deepseek.yml`

## OOM Rules
- Max 2 concurrent `cargo check/build`
- Serialize Rust builds, clean target/ between them
- Kimi: ~100 words max, `--quiet` mode
- DeepSeek v4-pro: use `deepseek-reason` (background), NOT curl (timeout kills)

## Key Constraints
- **rustc 1.75.0** — pin uuid≤1.4.1, no edition2024
- **No GROQ_API_KEY** — Groq agents unavailable
- **No OPENAI_API_KEY** — Codex unavailable

## PLATO Training Rooms (SuperInstance/plato-training)

The main build. Micro models for ensigns, deployable to any hardware at the click of a button.

```
plato_training/
  ├── types.py          — TrainingTile, TileLifecycle, LamportClock
  ├── adapters/lora.py  — LoRALayer with save/load
  ├── rooms/            — LoRAFactory room
  ├── store.py          — LocalTileStore (content-addressed)
  ├── throttle.py       — Fleet-aware training throttle
  ├── pytorch_room.py   — PyTorchRoom (LoRA + throttle)
  ├── tensorflow_room.py — TensorFlowRoom (Keras + throttle)
  ├── spline.py         — SplineLinear (Eisenstein lattice weights, NOVEL)
  ├── micro_models.py   — 8 room tasks + training pipeline
  ├── hardware.py       — 8 hardware targets + deploy pipeline
  ├── cli.py            — plato-train CLI (470 lines)
  └── tests/            — 69 tests passing
```

**One function:** `deploy_micro("drift-detect", target="npu")`
**Fleet deploy:** `deploy_fleet()` — all 48 task×target combos
**Fleet results:** drift-detect 100% on 5/6 targets, anomaly-flag 93% on NPU

### Key Results
- SplineLinear: 20× compression on drift-detect at SAME accuracy
- NPU quantization: maintains 100% on drift-detect and intent-detect
- Sub-millisecond inference across all CPU targets
- LoRA struggles on synthetic data (expected — needs real data)

### Architecture (3 layers)
1. Room Protocol: tiles, lifecycle, throttle, Lamport clocks
2. Engine Rooms: PyTorch/TF + micro models
3. Tensor-Spline: Eisenstein lattice weight parameterization

### Variant Selection (auto)
- cpu-tiny → spline (compression required)
- npu → dense + INT8 quantize
- gpu → lora
- default → dense

### Priority: Build the system, not posts
- Scale SplineLinear for high-dim tasks
- Real data pipelines for micro models
- Wire micro models into PLATO rooms
- GPT-2 / small transformer training runs

### Modular Architecture (4 independent repos)
| Repo | What | Tests |
|------|------|-------|
| SuperInstance/plato-types | Tile lifecycle, Lamport clocks | 10 |
| SuperInstance/tensor-spline | SplineLinear, LowRank, Hierarchical | 57 |
| SuperInstance/plato-data | CSV/JSONL/PLATO/fleet data loading | 10 |
| SuperInstance/plato-training | Micro models, hardware deploy, rooms | 116 |

Each independently installable. plato-training orchestrates.
- **Repo:** https://github.com/SuperInstance/casting-call
- **What:** Which model plays which role — fleet-wide model capability database
- **Agents consult this before choosing which model to cast into which shell**
- Includes: roster (11+ models), role taxonomy, failure modes, adversarial pairs, pipeline patterns
- 685 lines of evaluation data from real production work (May 3-7, 2026)

## I2I Protocol
- Instance-to-instance: no Python imports between repos, just tiles
- 5 tile schemas: model, data, compression, benchmark, deploy
- Collective inference: predict → listen → compare → gap → learn → share
- Focus scoring: confidence × delta = "how sure × how wrong"
- "The glitches ARE the research agenda. The gaps ARE the work."

## Fleet Comms
- I2I Protocol: `[I2I:TYPE] scope — summary`
- Vessel: https://github.com/SuperInstance/forgemaster

See `references/tools-detail.md` for full agent configs.

## Claude Code — EXPENSIVE RESOURCE PROTOCOL ⚠️

**Claude is ~100x more expensive than Seed-2.0-mini ($0.01). Every Claude run costs $3-10+.**
A wasted Claude run = burning 100 cheap model calls. **Be surgical.**

### HARD RULES (no exceptions)

1. **NEVER feed Claude more than 3 files directly.** OOM = wasted money. Pre-summarize with Seed-2.0-mini.
2. **NEVER run Claude without a timeout.** Minimum 600s.
3. **ALWAYS prep with cheap models first.** Use Seed-2.0-mini ($0.01) to:
   - Extract and summarize relevant context from large files
   - Write a lean, self-contained prompt with only distilled info
   - Pre-compute arithmetic, format data, trim boilerplate
4. **NEVER use Claude for something a cheaper model can do.** Escalation path:
   - Seed-2.0-mini → Hermes-70B → GLM-5.1 subagent → DeepSeek Reasoner → **Claude (last resort)**
5. **NEVER re-run Claude on the same failed prompt.** If it OOMs or times out, use Seed-2.0-mini to break the task into smaller pieces.

### Preparation Protocol (MANDATORY before every Claude run)

```bash
# Step 1: Use Seed-2.0-mini to distill context
DEEPINFRA_KEY=$(cat ~/.openclaw/workspace/.credentials/deepinfra-api-key.txt)
curl -s https://api.deepinfra.com/v1/openai/chat/completions \
  -H "Authorization: Bearer $DEEPINFRA_KEY" -H "Content-Type: application/json" \
  -d '{"model":"ByteDance/Seed-2.0-mini","messages":[{"role":"user","content":"Read these files and prepare a concise context summary for Claude Opus: [DESCRIBE TASK]. Output ONLY the distilled context, no meta-commentary."}],"max_tokens":2048}'

# Step 2: Write the prepared prompt to a file — lean, surgical, no raw dumps
# Step 3: Run Claude with the lean prompt
```

### Timeout Rules
- **Minimum**: 600s (10 min)
- **Standard**: 1200s (20 min)
- **Max**: 2400s (40 min) — ONLY for novel synthesis that no other model can handle
- **If OOM**: You fed it too much. Reduce context by 50%, prep with cheap model first.
- **If timeout**: Do NOT retry at higher timeout. Break into smaller pieces with Seed-2.0-mini.

### Model Selection
- **Opus**: ONLY for novel theoretical synthesis beyond all other models
- **Sonnet**: Only when GLM-5.1 agents have genuinely failed on the same task
- **Default**: GLM-5.1 (paid plan) or Seed-2.0-mini. Claude is the exception, not the rule.

### Settings
- `effortLevel: high` (set in ~/.claude/settings.json)
- `--print --permission-mode bypassPermissions` — always non-interactive

### Anti-Patterns (DO NOT)
- ❌ Dumping files into a Claude prompt without pre-summarizing
- ❌ Running Claude without a timeout
- ❌ Using Claude for boilerplate, standard code, or docs
- ❌ Re-running Claude on the same failed prompt
- ❌ "Let me try Claude" before trying Seed-2.0-mini or GLM-5.1
- ❌ Feeding raw file contents instead of summaries

## Fleet Model Routing (Updated 2026-05-15)

### z.ai (PAID PLAN — use heavily)

| Model | Best For | Stage | Notes |
|-------|----------|:-----:|-------|
| **glm-5.1** | Code generation, architecture, boilerplate, planning | 3 | Thinking model — reasoning in reasoning_content, content often empty. Pre-compute arithmetic before sending. |
| **glm-5-turbo** | Content tasks, non-reasoning generation, summaries | 3 | Non-thinking, faster. Same vocabulary wall. Pre-compute arithmetic. |
| **glm-4.7** | Lighter tasks, faster responses | 2-3 | Fallback when 5.x rate limited |
| **glm-4.7-flash** | Quick lookups, simple generation | 2 | Fastest, cheapest z.ai option |

### DeepInfra (PAY-PER-USE)

| Model | Best For | Stage | Cost |
|-------|----------|:-----:|------|
| **Seed-2.0-mini** | Domain computation, math reasoning, Stage 4 tasks | **4** | ~$0.01/query |
| **Seed-2.0-code** | Code + math combined tasks | **4** | ~$0.02/query |
| Hermes-70B | General generation, large context | 3 | Moderate |
| Qwen3-235B | Multi-step reasoning (with translation) | 3 | Moderate |
| Qwen3.6-35B | Cheap routing, fast | 2 | Cheap |

### Routing Rules

```
EVERYTHING → GLM-5.1 (z.ai, paid plan, MAX IT OUT)
  ↓ only when rate-limited or genuinely insufficient
Domain computation / math reasoning → Seed-2.0-mini (Stage 4)
Research rounds (large context, fast iteration) → DeepSeek v4-flash (cheap, huge context)
Second opinions / large context → Hermes-70B
Quick routing / fast lookups → Qwen3.6-35B
Heavy novel reasoning → DeepSeek v4-pro (reasoner)
NOVEL SYNTHESIS ONLY → Claude Opus (last resort, 100x cost)
```

### Key: GLM-5.1 IS THE DEFAULT. z.ai is PAID — burn it for EVERYTHING.
"Education isn't something you finish" — GLM-5.1 stays hot, forging the system.
Only delegate downstream when GLM-5.1 hits limits or a cheaper model is genuinely sufficient for a trivial task.
Seed/Hermes/Qwen/DeepSeek are SUPPLEMENTS, not replacements. GLM-5.1 is the workhorse.
DeepSeek v4-flash is the research workbench — large context, fast, cheap, good for iterative exploration.
