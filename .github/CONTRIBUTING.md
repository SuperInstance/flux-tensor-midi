# Contributing to the SuperInstance Fleet

Welcome aboard. This repo is the `.github` heart of the SuperInstance fleet — every workflow, template, and convention that keeps the fleet sailing in sync. Whether you're adding a new agent, writing a PLATO tile, or tightening a CI/CD routine, this is the place.

## The Dojo Model

Every agent should leave each repo **better than they found it**. That means:
- Fix the bug *and* refactor the messy context around it
- Add the feature *and* update the docs it affects
- Touch a tile *and* check if the Q&A format is still clean

Growth is the metric, not just completion. Returning crew are welcome back stronger.

---

## Adding a New Agent to the Fleet

### 1. Define the Agent's Domain
Every agent needs a clear operational domain — the slice of the fleet it owns. Document:
- What problem it solves
- What inputs it expects
- What outputs it produces
- What other agents it communicates with

### 2. Set Up the Repo
```bash
# Clone the fleet template or an existing agent repo as a base
git clone https://github.com/SuperInstance/<agent-name>.git
cd <agent-name>
```

### 3. Implement the Core Loop
Agents in the fleet follow the **PLATO protocol** (see Links below). At minimum:
- **Perceive** — read environment, pull context from shared memory
- **Learn** — update internal state, write findings back to the oracle room
- **Act** — produce output (code, response, decision)

### 4. Add Your Agent to the Fleet Registry
Update the fleet manifest (usually `agents.json` or `fleet.toml` in the root repo) with:
```json
{
  "name": "<agent-name>",
  "domain": "<what it owns>",
  "repo": "SuperInstance/<agent-name>",
  "capabilities": ["capability-a", "capability-b"]
}
```

### 5. Test It
Write tests in `tests/` using the fleet test harness. See "Adding Tests" below.

### 6. Get Review
Open a PR. Fill out the PR template. Request review from at least one fleet senior agent or Casey.

---

## Writing PLATO Tiles

PLATO tiles are the fleet's Q&A knowledge units — small, structured pairs that teach agents how to handle domain-specific situations.

### Format
```
Q: <question>
A: <answer>
[EXAMPLES]
- <example case>
NOTES: <optional nuance or edge case>
```

### Conventions
- **One concept per tile.** If you're explaining two concepts, split it.
- **Q should be specific.** "How do I handle a NULL agent ID?" not "How do I handle errors?"
- **A should be actionable.** Code snippet or decision tree preferred over prose.
- **Edge cases in NOTES.** Don't bury them in the answer.
- **Domain prefix in filename:** `<domain>-<slug>.md`

### Example
```markdown
Q: How do I authenticate a newly paired agent?
A: Check the bootstrap token in the agent's handshake payload. If valid, issue a fleet credential.
EXAMPLES:
- Token expired → reject with `AUTH_TOKEN_EXPIRED`, log to oracle.
- Token valid → issue 24h session token, announce to fleet radar.
NOTES: Tokens are scoped to the pairing node. Cross-node auth requires keeper mediation.
```

---

## Adding Tests to Fleet Repos

### Test Structure
```
tests/
  unit/       # isolated function/reasoning tests
  integ/      # agent-to-agent communication tests
  e2e/        # full scenario tests (usually run in sandbox)
```

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires fleet services running)
pytest tests/integ/

# E2E in sandbox
sudo docker run --rm fleet-sandbox pytest tests/e2e/
```

### Writing Tests
- **Unit:** Pure functions, mock everything external
- **Integration:** Real services, but isolated network (use `fleet-net` docker network)
- **E2E:** Full scenarios. These run in the fleet-sandbox Docker image.

---

## Adding CI/CD with GitHub Actions

### Standard Workflow Pattern
Create `.github/workflows/ci.yml`:

```yaml
name: Fleet CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up environment
        run: |
          # your setup here
          echo "FLEET_CONTEXT=${{ github.event.repository.name }}" >> $GITHUB_ENV

      - name: Run unit tests
        run: pytest tests/unit/ -v

      - name: Run integration tests
        run: pytest tests/integ/ -v
        env:
          FLEET_NET_HOST: fleet-net

      - name: Lint
        run: |
          # your linter here
          flake8 . --max-line-length=100 || true

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build artifacts
        run: |
          # your build here
          python3 -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist

      - name: Deploy
        run: |
          # your deploy here
          echo "Deploying from ${{ github.sha }}"
```

### Publishing Workflow (for npm/PyPI/crates.io packages)
```yaml
publish:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '22'
        registry-url: 'https://registry.npmjs.org'
    - run: npm publish --access public
      env:
        NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## Getting Your Code Reviewed

### Before Requesting Review
- [ ] Tests pass locally
- [ ] Docs updated if behavior changed
- [ ] No breaking changes (or documented in changelog)
- [ ] CI/CD is green (or explicitly noted why it isn't)

### How to Request
1. Open a PR with a clear title: `feat: <short description>`
2. Fill out the PR template completely
3. Assign reviewers — at least one fleet senior or Casey
4. Respond to comments promptly. "Leaving it as-is for now, can revisit in a follow-up" is fine — just say it.

### Review Etiquette
- **Be specific in your own reviews.** "nit: s/this/that" is more helpful than "looks ok"
- **Don't merge your own PRs** unless explicitly approved to do so
- **Mark threads resolved only after addressed** — not preventatively

---

## Links

- [PLATO Protocol](https://github.com/SuperInstance/plato) — fleet communication and memory architecture
- [Fleet Identity (SOUL.md)](https://github.com/SuperInstance/.github/blob/main/SOUL.md) — who we are, how we operate
- [Constraint Theory Intro](https://github.com/SuperInstance/constraint-theory) — decision-making under constraints, fleet-wide
- [Fleet Sandbox](https://github.com/SuperInstance/fleet-sandbox) — containerized dev/test environment

---

*Last updated: 2026-05-07*
