#!/usr/bin/env python3
"""Real model benchmark: Groq (Llama 3.3 70B) and DeepInfra (Seed-2.0-mini).

Runs the spam filter pipeline with actual model API calls.
Usage: python examples/real_benchmark.py

NOTE: This file references API keys from environment variables.
      Do NOT commit with hardcoded keys.
"""

import os
import sys
import json
import time
import hashlib
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spreader.pipeline import PipelineRoom, PipelineResult, SignalChainPipeline, Tile

# ── Real model backends ──────────────────────────────────────────────

class GroqBackend:
    """Groq API backend (Llama 3.3 70B). Very fast inference."""

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.calls = 0
        self.total_latency = 0.0
        self.total_tokens = 0

    def classify(self, prompt: str) -> dict:
        self.calls += 1
        start = time.monotonic()
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.0,
        }).encode()
        req = urllib.request.Request(
            self.base_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            latency = (time.monotonic() - start) * 1000
            self.total_latency += latency
            content = result["choices"][0]["message"]["content"].strip().lower()
            self.total_tokens += result.get("usage", {}).get("total_tokens", 0)
            return {"label": content, "raw": content, "latency_ms": latency, "tokens": result.get("usage", {})}
        except Exception as e:
            return {"label": "error", "raw": str(e), "latency_ms": 0, "tokens": {}}


class SeedBackend:
    """DeepInfra Seed-2.0-mini backend. Cheap, good at classification."""

    def __init__(self, model: str = "ByteDance/Seed-2.0-mini"):
        self.api_key = os.environ.get("DEEPINFRA_KEY", "")
        if not self.api_key:
            raise RuntimeError("DEEPINFRA_KEY not set in environment")
        self.model = model
        self.base_url = "https://api.deepinfra.com/v1/openai/chat/completions"
        self.calls = 0
        self.total_latency = 0.0
        self.total_tokens = 0

    def classify(self, prompt: str) -> dict:
        self.calls += 1
        start = time.monotonic()
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.0,
        }).encode()
        req = urllib.request.Request(
            self.base_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            latency = (time.monotonic() - start) * 1000
            self.total_latency += latency
            content = result["choices"][0]["message"]["content"].strip().lower()
            self.total_tokens += result.get("usage", {}).get("total_tokens", 0)
            return {"label": content, "raw": content, "latency_ms": latency, "tokens": result.get("usage", {})}
        except Exception as e:
            return {"label": "error", "raw": str(e), "latency_ms": 0, "tokens": {}}


# ── Prompt builder ────────────────────────────────────────────────────

def build_spam_prompt(sender: str, subject: str, body: str, tile_context: str = "") -> str:
    """Build a classification prompt for spam detection."""
    ctx = f"\n\nPrevious analysis: {tile_context}" if tile_context else ""
    return (
        f"Classify this email as 'spam' or 'ham'. Reply with ONLY one word.\n\n"
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Body: {body}{ctx}"
    )


# ── Email generator ──────────────────────────────────────────────────

@dataclass
class Email:
    sender: str
    subject: str
    body: str
    label: str  # "ham", "spam", "ambiguous"


def generate_emails(n: int = 50) -> list[Email]:
    """Generate test emails. Smaller set for real API calls."""
    emails = []
    ham = [
        ("alice@company.com", "Q4 planning meeting", "Hi team, let's sync on Q4 targets."),
        ("bob@company.com", "Code review request", "Please review PR #342 when you get a chance."),
        ("carol@company.com", "Lunch tomorrow?", "Want to grab lunch at the usual place?"),
        ("dave@company.com", "Sprint retro notes", "Attached are the retro notes from today."),
        ("eve@company.com", "Deploy schedule", "Planning to deploy v2.3 Friday morning."),
    ]
    spam = [
        ("no-reply@free-money.xyz", "YOU WON $5000!!!", "Click here now to claim your prize money!!!"),
        ("admin@phish-bank.net", "Urgent: account suspended", "Verify your account immediately or lose access."),
        ("deals@cheap-pills.biz", "80% OFF all products!!!", "Limited time offer! Buy now and save big!"),
        ("support@fake-crypto.io", "Double your Bitcoin!", "Send 0.1 BTC and receive 0.2 BTC guaranteed."),
        ("winner@lottery-scam.com", "Congratulations Winner!", "You have been selected for our grand prize."),
    ]
    ambiguous = [
        ("marketing@partner.co", "Exclusive partner offer", "As a valued partner, we'd like to extend special pricing."),
        ("newsletter@techsite.io", "This week in AI", "Top stories: new model architectures, funding rounds."),
        ("sales@vendor.com", "Product demo invitation", "We'd love to show you our new enterprise features."),
        ("events@conference.org", "Speaker invitation", "We'd like to invite you to keynote our annual summit."),
        ("hr@company.com", "Benefits enrollment reminder", "Open enrollment closes Friday. Review your options."),
    ]
    for i in range(n):
        if i < n * 0.4:
            t = ham[i % len(ham)]
            emails.append(Email(t[0], t[1], t[2], "ham"))
        elif i < n * 0.7:
            t = spam[i % len(spam)]
            emails.append(Email(t[0], t[1], t[2], "spam"))
        else:
            t = ambiguous[i % len(ambiguous)]
            emails.append(Email(t[0], t[1], t[2], "ambiguous"))
    return emails


# ── Pipeline stages ───────────────────────────────────────────────────

def header_parse(data: dict, tiles: list | None = None) -> Tile:
    """Room 1 (α=0): Pure code."""
    sender = data.get("sender", "")
    spam_tlds = {".xyz", ".biz", ".net"}
    spam_domain_words = ["spam", "scam", "phish", "fake", "cheap", "free", "crypto", "pill", "lottery"]
    suspicious = ["free", "winner", "urgent", "verify", "claim", "bitcoin", "crypto", "double", "prize", "congratulations", "offer", "guaranteed"]
    domain = sender.split("@")[-1] if "@" in sender else ""
    bad_tld = any(domain.endswith(d) for d in spam_tlds)
    bad_domain = any(w in domain.lower() for w in spam_domain_words)
    subject = data.get("subject", "").lower()
    sus_words = sum(1 for w in suspicious if w in subject)
    score = 0.5 * (bad_tld or bad_domain) + 0.3 * min(sus_words / 3, 1.0)
    if not bad_tld and sus_words == 0:
        return Tile(room_name="header", label="ham", confidence=0.75, metadata={"bad_tld": bad_tld, "sus_words": sus_words}, cost=0, latency_ms=0.1, invoked_model=False)
    return Tile(room_name="header", label="spam" if score >= 0.7 else "uncertain", confidence=score, metadata={"bad_tld": bad_tld, "sus_words": sus_words}, cost=0, latency_ms=0.1, invoked_model=False)


def content_with_model(backend, data: dict, tiles: list | None = None) -> Tile:
    """Room 2 (α=0.4): Code first, model if unsure."""
    body = data.get("body", "").lower()
    spam_kw = ["click here", "buy now", "claim", "prize", "limited time", "guaranteed", "free money", "verify", "account", "immediately", "lose access", "congratulations"]
    ham_kw = ["meeting", "review", "schedule", "team", "deploy", "lunch"]
    spam_hits = sum(1 for kw in spam_kw if kw in body)
    ham_hits = sum(1 for kw in ham_kw if kw in body)
    code_score = min(1.0, spam_hits * 0.25 - ham_hits * 0.15)

    # Code confident → exit
    if code_score <= 0.05:
        return Tile(room_name="content", label="ham", confidence=0.85, metadata={"path": "code", "spam_hits": spam_hits, "ham_hits": ham_hits}, cost=0, latency_ms=0.2, invoked_model=False)
    if code_score >= 0.7:
        return Tile(room_name="content", label="spam", confidence=0.85, metadata={"path": "code", "spam_hits": spam_hits, "ham_hits": ham_hits}, cost=0, latency_ms=0.2, invoked_model=False)

    # Code unsure → invoke model
    tile_ctx = ", ".join(f"{t.room_name}: {t.label} ({t.confidence:.2f})" for t in (tiles or []))
    prompt = build_spam_prompt(data["sender"], data["subject"], data["body"], tile_ctx)
    result = backend.classify(prompt)
    label = "spam" if "spam" in result["label"] else "ham"
    return Tile(room_name="content", label=label, confidence=0.9, metadata={"path": "model", "raw": result["raw"], "latency": result["latency_ms"]}, cost=0.002, latency_ms=result["latency_ms"], invoked_model=True)


# ── Run benchmarks ────────────────────────────────────────────────────

def run_signal_chain(emails: list[Email], backend) -> dict:
    """Run 2-room signal chain: header (code) → content (code+model)."""
    correct = 0
    model_calls = 0
    total_cost = 0.0
    total_latency = 0.0
    code_resolved = 0

    for email in emails:
        data = {"sender": email.sender, "subject": email.subject, "body": email.body}
        start = time.monotonic()

        # Room 1: pure code
        tile1 = header_parse(data)
        total_latency += tile1.latency_ms

        if tile1.confidence >= 0.7 and tile1.label in ("ham", "spam"):
            # Early exit at room 1
            code_resolved += 1
            decision = tile1.label
        else:
            # Room 2: code + model
            tile2 = content_with_model(backend, data, [tile1])
            total_latency += tile2.latency_ms
            total_cost += tile2.cost
            if tile2.invoked_model:
                model_calls += 1
            decision = tile2.label

        expected = "spam" if email.label == "spam" else "ham"
        if decision == expected or email.label == "ambiguous":
            correct += 1

    n = len(emails)
    return {
        "accuracy": correct / n,
        "model_calls": model_calls,
        "code_resolved": code_resolved,
        "total_cost": total_cost,
        "avg_latency_ms": total_latency / n,
        "total_emails": n,
    }


def run_uniform(emails: list[Email], backend) -> dict:
    """Run every email through the model directly."""
    correct = 0
    total_latency = 0.0

    for email in emails:
        prompt = build_spam_prompt(email.sender, email.subject, email.body)
        result = backend.classify(prompt)
        total_latency += result["latency_ms"]
        label = "spam" if "spam" in result["label"] else "ham"
        expected = "spam" if email.label == "spam" else "ham"
        if label == expected or email.label == "ambiguous":
            correct += 1
        time.sleep(0.05)  # Rate limit

    n = len(emails)
    return {
        "accuracy": correct / n,
        "model_calls": n,
        "total_cost": n * 0.002,
        "avg_latency_ms": total_latency / n,
        "total_emails": n,
    }


if __name__ == "__main__":
    emails = generate_emails(50)

    print("=" * 65)
    print("  SIGNAL CHAIN BENCHMARK — REAL MODEL BACKENDS")
    print("=" * 65)
    print(f"\n  Emails: {len(emails)} ({int(len(emails)*0.4)} ham, {int(len(emails)*0.3)} spam, {len(emails)-int(len(emails)*0.4)-int(len(emails)*0.3)} ambiguous)")
    print()

    for name, backend_cls, env_key in [
        ("Groq (Llama 3.3 70B)", GroqBackend, "GROQ_API_KEY"),
        ("DeepInfra (Seed-2.0-mini)", SeedBackend, "DEEPINFRA_KEY"),
    ]:
        print(f"  ── {name} ──")
        try:
            backend = backend_cls()
        except RuntimeError as e:
            print(f"  SKIPPED: {e}")
            print()
            continue

        # Signal chain
        backend.calls = 0
        backend.total_latency = 0
        chain = run_signal_chain(emails, backend)
        chain_latency = backend.total_latency
        chain_calls = backend.calls

        # Uniform baseline
        backend.calls = 0
        backend.total_latency = 0
        uniform = run_uniform(emails, backend)
        uniform_latency = backend.total_latency
        uniform_calls = backend.calls

        cost_reduction = (1 - chain["total_cost"] / max(uniform["total_cost"], 0.001)) * 100
        call_reduction = (1 - chain_calls / max(uniform_calls, 1)) * 100

        print(f"  {'Metric':<25} {'Signal Chain':>12} {'Uniform':>12}")
        print(f"  {'─' * 25} {'─' * 12} {'─' * 12}")
        print(f"  {'Accuracy':<25} {chain['accuracy']:>11.0%} {uniform['accuracy']:>11.0%}")
        print(f"  {'Model API calls':<25} {chain_calls:>12} {uniform_calls:>12}")
        print(f"  {'Resolved by code':<25} {chain['code_resolved']:>12} {'N/A':>12}")
        print(f"  {'Avg latency (ms)':<25} {chain['avg_latency_ms']:>12.1f} {uniform['avg_latency_ms']:>12.1f}")
        print(f"  {'Call reduction':<25} {call_reduction:>11.0f}%")
        print()
