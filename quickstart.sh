#!/bin/bash
# Quick Start: Flux Tensor MIDI — Tensor Field Music Generation
set -e
pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e . --quiet 2>/dev/null || true
python3 examples/basic_musician.py
echo ""
echo "🎉 Flux tensor music generated — check MIDI output above!"
