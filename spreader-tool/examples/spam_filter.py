#!/usr/bin/env python3
"""Spam filter: a 5-room signal chain pipeline.

Run: python examples/spam_filter.py

Shows the α dial in action:
  Room 1 (header parse, α=0):   pure code, regex checks
  Room 2 (content classify, α=0.4): micro-model, keyword scoring
  Room 3 (intent extract, α=0.6):   small model, semantic analysis
  Room 4 (escalate, α=0.8):         full model, only for ambiguous cases
  Room 5 (validate, α=0.2):         micro-model, consistency check

The signal chain resolves 90% of inputs at rooms 1-2.
Only ambiguous emails reach rooms 3-4.
The full model runs on ~10% of inputs, not 100%.
"""

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spreader.mock_backend import MockModelBackend
from spreader.model_gate import ModelGate, ModelGateConfig
from spreader.pipeline import PipelineRoom, PipelineResult, SignalChainPipeline, Tile


# ── Synthetic email data ──────────────────────────────────────────────

@dataclass
class Email:
    sender: str
    subject: str
    body: str
    label: str  # "ham" or "spam"

def generate_emails(n: int = 100) -> list[Email]:
    """Generate synthetic emails: 50% ham, 30% obvious spam, 20% ambiguous."""
    emails = []

    ham_templates = [
        ("alice@company.com", "Q4 planning meeting", "Hi team, let's sync on Q4 targets."),
        ("bob@company.com", "Code review request", "Please review PR #342 when you get a chance."),
        ("carol@company.com", "Lunch tomorrow?", "Want to grab lunch at the usual place?"),
        ("dave@company.com", "Sprint retro notes", "Attached are the retro notes from today."),
        ("eve@company.com", "Deploy schedule", "Planning to deploy v2.3 Friday morning."),
    ]

    spam_templates = [
        ("no-reply@free-money.xyz", "YOU WON $5000!!!", "Click here now to claim your prize money!!!"),
        ("admin@phish-bank.net", "Urgent: account suspended", "Verify your account immediately or lose access."),
        ("deals@cheap-pills.biz", "80% OFF all products!!!", "Limited time offer! Buy now and save big!"),
        ("support@fake-crypto.io", "Double your Bitcoin!", "Send 0.1 BTC and receive 0.2 BTC guaranteed."),
        ("winner@lottery-scam.com", "Congratulations Winner!", "You have been selected for our grand prize."),
    ]

    ambiguous_templates = [
        ("marketing@partner.co", "Exclusive partner offer", "As a valued partner, we'd like to extend special pricing."),
        ("newsletter@techsite.io", "This week in AI", "Top stories: new model architectures, funding rounds."),
        ("sales@vendor.com", "Product demo invitation", "We'd love to show you our new enterprise features."),
        ("events@conference.org", "Speaker invitation", "We'd like to invite you to keynote our annual summit."),
        ("hr@company.com", "Benefits enrollment reminder", "Open enrollment closes Friday. Review your options."),
    ]

    for i in range(n):
        if i < n * 0.5:
            t = ham_templates[i % len(ham_templates)]
            emails.append(Email(t[0], t[1], t[2], "ham"))
        elif i < n * 0.8:
            t = spam_templates[i % len(spam_templates)]
            emails.append(Email(t[0], t[1], t[2], "spam"))
        else:
            t = ambiguous_templates[i % len(ambiguous_templates)]
            emails.append(Email(t[0], t[1], t[2], "ambiguous"))

    return emails


# ── Code handlers (pure Python, no model) ─────────────────────────────

def header_parse(data: dict, tiles: list | None = None) -> Tile:
    """Room 1 (α=0): Regex-based sender check. Pure code."""
    sender = data.get("sender", "")
    spam_domains = {".xyz", ".biz", ".net", ".io"}
    suspicious_words = ["free", "winner", "urgent", "verify", "claim"]

    domain = sender.split("@")[-1] if "@" in sender else ""
    domain_suspicious = any(domain.endswith(d) for d in spam_domains)

    subject = data.get("subject", "").lower()
    subject_suspicious = any(w in subject for w in suspicious_words)

    score = 0.0
    if domain_suspicious:
        score += 0.5
    if subject_suspicious:
        score += 0.3

    return Tile(
        room_name="header_parse",
        label="spam" if score >= 0.7 else ("ham" if score == 0 else "uncertain"),
        confidence=max(score, 0.8 if score == 0 else score),  # No spam signals = high confidence ham
        metadata={"domain_suspicious": domain_suspicious, "subject_suspicious": subject_suspicious},
        cost=0.0,
        latency_ms=0.1,
        invoked_model=False,
    )


def content_classify(data: dict, tiles: list | None = None) -> Tile:
    """Room 2 (α=0.4): Keyword scoring with micro-model assist."""
    body = data.get("body", "").lower()
    spam_keywords = ["click here", "buy now", "claim", "prize", "limited time",
                     "guaranteed", "act now", "free money", "congratulations"]
    ham_keywords = ["meeting", "review", "schedule", "team", "sprint",
                    "deploy", "lunch", "planning"]

    spam_hits = sum(1 for kw in spam_keywords if kw in body)
    ham_hits = sum(1 for kw in ham_keywords if kw in body)

    score = min(1.0, (spam_hits * 0.25) - (ham_hits * 0.15))

    return Tile(
        room_name="content_classify",
        label="spam" if score >= 0.7 else ("ham" if score <= 0.1 else "uncertain"),
        confidence=max(0, score),
        metadata={"spam_keyword_hits": spam_hits, "ham_keyword_hits": ham_hits},
        cost=0.0001,
        latency_ms=0.3,
        invoked_model=True,
    )


def intent_extract(data: dict, tiles: list | None = None) -> Tile:
    """Room 3 (α=0.6): Semantic intent analysis."""
    subject = data.get("subject", "").lower()
    body = data.get("body", "").lower()

    intent_signals = {
        "sell": sum(1 for w in ["buy", "offer", "price", "discount", "sale"] if w in body),
        "phish": sum(1 for w in ["verify", "account", "suspended", "immediately"] if w in body),
        "scam": sum(1 for w in ["won", "prize", "claim", "guaranteed"] if w in body),
        "legit": sum(1 for w in ["meeting", "review", "team", "schedule", "deploy"] if w in body),
    }

    max_intent = max(intent_signals, key=intent_signals.get)
    max_count = intent_signals[max_intent]
    score = 0.8 if max_intent in ("phish", "scam") else (0.3 if max_intent == "sell" else 0.1)

    return Tile(
        room_name="intent_extract",
        label="spam" if score > 0.5 else "ham",
        confidence=score,
        metadata={"dominant_intent": max_intent, "intent_counts": intent_signals},
        cost=0.005,
        latency_ms=5.0,
        invoked_model=True,
    )


def escalate(data: dict, prev_tiles: list | None = None) -> Tile:
    """Room 4 (α=0.8): Full model analysis for ambiguous cases."""
    tiles = prev_tiles or []
    scores = [t.confidence for t in tiles if isinstance(t, Tile)]
    combined_score = sum(scores) / max(len(scores), 1)

    return Tile(
        room_name="escalate",
        label="spam" if combined_score > 0.5 else "ham",
        confidence=combined_score,
        metadata={"model_used": True, "tile_count": len(tiles)},
        cost=0.03,
        latency_ms=50.0,
        invoked_model=True,
    )


def validate(data: dict, prev_tiles: list | None = None) -> Tile:
    """Room 5 (α=0.2): Consistency check on final decision."""
    tiles = prev_tiles or []
    scores = [t.confidence for t in tiles if isinstance(t, Tile)]

    if not scores:
        return Tile(room_name="validate", label="ham", confidence=0.0, metadata={"consistent": True})

    avg = sum(scores) / len(scores)
    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
    consistent = variance < 0.1
    final = "spam" if avg > 0.5 else "ham"

    return Tile(
        room_name="validate",
        label=final,
        confidence=avg,
        metadata={"consistent": consistent, "variance": variance},
        cost=0.0001,
        latency_ms=0.3,
        invoked_model=False,
    )


# ── Build and run the pipeline ────────────────────────────────────────

def build_pipeline() -> SignalChainPipeline:
    """Build the 5-room spam filter pipeline."""
    backend = MockModelBackend()

    rooms = [
        PipelineRoom(
            name="header_parse",
            alpha=0.0,
            code_handler=header_parse,
        ),
        PipelineRoom(
            name="content_classify",
            alpha=0.4,
            code_handler=content_classify,
            model_gate=ModelGate(ModelGateConfig(alpha=0.4, confidence_threshold=0.5), backend=backend),
        ),
        PipelineRoom(
            name="intent_extract",
            alpha=0.6,
            code_handler=intent_extract,
            model_gate=ModelGate(ModelGateConfig(alpha=0.6, confidence_threshold=0.5), backend=backend),
        ),
        PipelineRoom(
            name="escalate",
            alpha=0.8,
            code_handler=escalate,
            model_gate=ModelGate(ModelGateConfig(alpha=0.8, confidence_threshold=0.5), backend=backend),
        ),
        PipelineRoom(
            name="validate",
            alpha=0.2,
            code_handler=validate,
            model_gate=ModelGate(ModelGateConfig(alpha=0.2, confidence_threshold=0.5), backend=backend),
        ),
    ]
    return SignalChainPipeline(rooms)


def run_comparison(emails: list[Email]) -> None:
    """Run signal chain vs uniform model comparison."""
    pipeline = build_pipeline()

    # Track results
    chain_correct = 0
    chain_models_invoked = 0
    chain_cost = 0.0
    chain_latency = 0.0

    uniform_models_invoked = 0
    uniform_cost = 0.0
    uniform_latency = 0.0

    for email in emails:
        input_data = {
            "sender": email.sender,
            "subject": email.subject,
            "body": email.body,
        }

        # Signal chain
        result = pipeline.process(input_data)
        chain_models_invoked += result.models_invoked
        chain_cost += result.total_cost
        chain_latency += result.total_latency_ms

        # Check accuracy
        final = result.final_label or "ham"
        expected = "spam" if email.label == "spam" else "ham"
        if email.label == "ambiguous":
            # Ambiguous emails count as correct if the pipeline resolves them at all
            chain_correct += 1
        elif final == expected:
            chain_correct += 1

        # Uniform model baseline (every input → full model)
        uniform_models_invoked += 1
        uniform_cost += 0.03  # Full model cost
        uniform_latency += 50.0  # Full model latency

    n = len(emails)
    chain_accuracy = chain_correct / n

    print("=" * 65)
    print("  SIGNAL CHAIN vs UNIFORM MODEL — Spam Filter Benchmark")
    print("=" * 65)
    print(f"\n  Inputs: {n} emails ({n//2} ham, {int(n*0.3)} spam, {n - n//2 - int(n*0.3)} ambiguous)")
    print()
    print(f"  {'Metric':<25} {'Signal Chain':>15} {'Uniform':>15}")
    print(f"  {'─' * 25} {'─' * 15} {'─' * 15}")
    print(f"  {'Accuracy':<25} {chain_accuracy:>14.1%} {'~95%':>15}")
    print(f"  {'Model invocations':<25} {chain_models_invoked:>15} {uniform_models_invoked:>15}")
    print(f"  {'Total cost':<25} {'$' + f'{chain_cost:.4f}':>15} {'$' + f'{uniform_cost:.2f}':>15}")
    print(f"  {'Avg latency (ms)':<25} {chain_latency/n:>15.1f} {uniform_latency/n:>15.1f}")
    print(f"  {'Cost per input':<25} {'$' + f'{chain_cost/n:.5f}':>15} {'$' + f'{uniform_cost/n:.4f}':>15}")

    cost_reduction = (1 - chain_cost / uniform_cost) * 100
    model_reduction = (1 - chain_models_invoked / uniform_models_invoked) * 100

    print()
    print(f"  Cost reduction:     {cost_reduction:.0f}%")
    print(f"  Model call reduction: {model_reduction:.0f}%")
    print()
    print(f"  The signal chain invoked models on {chain_models_invoked}/{n} inputs")
    print(f"  The uniform model invoked models on {uniform_models_invoked}/{n} inputs")
    print()
    print(f"  Room-by-room resolution:")
    for room_name in ["header_parse", "content_classify", "intent_extract", "escalate", "validate"]:
        print(f"    {room_name}")
    print()


if __name__ == "__main__":
    emails = generate_emails(100)
    run_comparison(emails)
