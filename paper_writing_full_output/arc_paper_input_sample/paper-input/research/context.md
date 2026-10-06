# Research Context

## Working title
Vectorized Rolling-Mean Computation in Python: A Small Reproducible Integration Fixture

## Problem
A paper-writing pipeline that consumes externally generated experimental evidence needs a compact,
machine-readable example containing research context, method, real run metrics, aggregate analysis,
figures, and a proceed decision.

## Objective
Demonstrate the complete external-input contract for a paper-only AutoResearchClaw adapter using a
small deterministic benchmark whose measurements can be reproduced locally.

## Scope
This fixture compares two numerically equivalent rolling-mean implementations on the same array:
a Python-side loop wrapper around precomputed values and a direct NumPy vectorized return path.

> This is an integration fixture, not a claim of scientific novelty or a submission-ready study.
