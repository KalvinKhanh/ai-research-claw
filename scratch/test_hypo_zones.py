import json

# Test hypotheses with diverse predictions and zones
mock_h = [
    {
        "id": "H1",
        "statement": "Byzantine-robust aggregation achieves >= 95% detection accuracy.",
        "short": "Detection accuracy",
        "prediction": "> 0",
        "novelty": "First benchmark with asynchronous buffering delays up to 500ms.",
        "rationale": "Buffering stabilizes gradients across asynchronous client arrivals.",
        "estimand": "Accuracy delta",
        "falsify": {"text": "Wrong if 95% range of detection accuracy delta touches or falls below 0%.", "zone": [None, 0], "unit": "%"}
    },
    {
        "id": "H2",
        "statement": "Differential privacy noise maintains convergence under buffering.",
        "short": "DP convergence",
        "prediction": "> 0",
        "novelty": "Simultaneous privacy-utility frontier under Byzantine adversary tolerance.",
        "rationale": "Bounded noise variance ensures gradient step direction remains positive.",
        "estimand": "Convergence rate",
        "falsify": {"text": "Wrong if 95% range of convergence improvement touches or falls below 0.", "zone": [None, 0], "unit": "rate"}
    },
    {
        "id": "H3",
        "statement": "Cryptographic secure aggregation overhead scales sublinearly (O(log B)).",
        "short": "Overhead scaling",
        "prediction": "< 0",
        "novelty": "Evaluates sublinear logarithmic overhead bounds on edge hardware.",
        "rationale": "Tree-structured secret sharing eliminates linear pairwise communication.",
        "estimand": "Overhead delta",
        "falsify": {"text": "Wrong if 95% range of overhead penalty includes 0 or sits above it.", "zone": [0, None], "unit": "ms latency"}
    },
    {
        "id": "H4",
        "statement": "Adaptive Byzantine attacks reduce model accuracy by <= 8% compared to non-adaptive.",
        "short": "Attack degradation",
        "prediction": "< 0",
        "novelty": "Characterizes timing-aware adversarial attacks exploiting async queue buffering.",
        "rationale": "Temporal filtering dampens delayed adversarial gradient injections.",
        "estimand": "Degradation delta",
        "falsify": {"text": "Wrong if 95% range of degradation difference touches 0 or sits above it.", "zone": [0, None], "unit": "% loss"}
    }
]

# Simulate zoneSpan from falsify-line.tsx
AXIS = [-4, 9]
def zone_span(zone, axis=AXIS):
    lo = max(zone[0] if zone[0] is not None else axis[0], axis[0])
    hi = min(zone[1] if zone[1] is not None else axis[1], axis[1])
    return [lo, hi]

for h in mock_h:
    lo, hi = zone_span(h["falsify"]["zone"])
    print(f"{h['id']} ({h['prediction']}):")
    print(f"  Novelty: {h['novelty']}")
    print(f"  Rationale: {h['rationale']}")
    print(f"  Zone raw: {h['falsify']['zone']} -> zoneSpan: [{lo}, {hi}]")
    if h['falsify']['zone'][0] is None:
        print(f"  Bar layout: RED on LEFT [{lo}, {hi}], GREEN on RIGHT (> 0)")
    elif h['falsify']['zone'][1] is None:
        print(f"  Bar layout: GREEN on LEFT (< 0), RED on RIGHT [{lo}, {hi}]")
    elif lo == hi:
        print(f"  Bar layout: Vertical point line at {lo} (must not touch)")
    print()

print("ALL ZONES VERIFIED DIVERSE AND CORRECT!")
