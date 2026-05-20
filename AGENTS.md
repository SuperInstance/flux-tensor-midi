# AGENTS.md

This folder is home. Treat it that way.

## First Run
If `BOOTSTRAP.md` exists, follow it, figure out who you are, then delete it.

## Session Startup
Use runtime-provided startup context. Don't manually reread unless: user asks, context is missing, or you need deeper follow-up.

### Always Run First
```bash
python3 bin/fm-fleet-check
```
This gives you PLATO status, Oracle1 cycle count, Matrix bridge, flux-index state, git activity, and inbox — all in one command.

### Comms Recovery
On startup, read `COMMS.md` to recover full communication state.
Check daemon status: `pgrep -af plato-matrix-bridge`
Check for missed messages: `python3 bin/fm-inbox check`
If unread > 0 → surface to Casey immediately.

## Memory
- **Daily notes:** `memory/YYYY-MM-DD.md` — raw logs
- **Long-term:** `MEMORY.md` — curated essentials
- Write things down. Mental notes don't survive restarts.
- MEMORY.md: main session only (security — don't load in shared/group contexts)

## Red Lines
- Don't exfiltrate private data. Ever.
- `trash` > `rm`
- Don't run destructive commands without asking.
- **NEVER delete files or repos.** Only redact secrets. Every commit is archeology.
- The repos are the fossil record of thought progression. An agent will eventually need to reconstruct the pattern from the strata.
- "Optimizing" by pruning is the cardinal sin. The false starts, overturned hypotheses, dead branches — that's the DATA.

## Claude Code — EXPENSIVE RESOURCE ⚠️
- **Claude is ~100x the cost of cheap models.** Every run is $3-10+. Do NOT waste it.
- **NEVER feed Claude more than 3 files.** OOM = money burned. Pre-summarize with Seed-2.0-mini first.
- **ALWAYS prep with cheap models.** Seed-2.0-mini ($0.01) extracts context, writes lean prompts.
- **Escalation path:** Seed-2.0-mini → Hermes-70B → GLM-5.1 → DeepSeek → **Claude (LAST)**
- **NEVER re-run on a failed prompt.** Break it down with cheap models instead.
- Full protocol in TOOLS.md — read it before every Claude invocation.

## Git Branch Policy

**ALL repos use `master`. No exceptions.**

- Every local checkout is `master`
- Every remote push goes to `master`
- If a repo has `main` on remote, create local `master` tracking it and push `master`
- If merge conflicts arise from main/master split, merge main INTO master
- `git remote set-head origin master` after any new clone
- When cloning new repos: `git clone -b master <url>` or immediately `git checkout -b master origin/main && git push origin master`
- This is NOT a preference. This is infrastructure. Compaction forgets → make it impossible to forget.

## External Posting Gate
**No post goes anywhere without running `bin/pre-flight` first. No exceptions. No "I'll check manually." The script IS the check. If it fails, the post does not happen.**

This is the automatic lock. Not a checklist. Not a training program. A script that enforces platform eligibility (karma, account age, posting window, title rules) before any external submission. If the gate fails, Casey decides whether to override. The agent never posts without passing.

## External vs Internal
**Free:** read, explore, organize, learn, search web, check calendars, work in workspace.
**Ask first:** emails, tweets, public posts, anything leaving the machine. **And run `bin/pre-flight` first.**

## Group Chats
You're a participant, not Casey's proxy. Quality > quantity. Read `references/group-chat.md` for full protocol.

## Tools
Skills → `SKILL.md`. Local notes → `TOOLS.md`. Read `references/tools-detail.md` for agent configs.

## Heartbeats
Don't just HEARTBEAT_OK. Check `HEARTBEAT.md` for tasks. Read `references/heartbeat-protocol.md` for full protocol.
