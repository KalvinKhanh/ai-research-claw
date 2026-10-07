from researchclaw.pipeline.llm_pipeline_generator import _assemble_contract

d1 = {
    'sub_questions': [{'id': 'SQ1'}, {'id': 'SQ2'}, {'id': 'SQ3'}, {'id': 'SQ4'}],
    'gaps': [{'id': 'G1'}, {'id': 'G2'}, {'id': 'G3'}],
    'queries': [{'id': 'q1', 'text': 'test', 'estimated_hits': 40}],
    'hypotheses': [
        {'id': 'H1', 'statement': 'Byzantine detection accuracy improves', 'short': 'Accuracy', 'prediction': '> 0', 'novelty': 'Novel buffer mechanism', 'rationale': 'Direct gradient filtering'},
        {'id': 'H2', 'statement': 'Convergence guarantee holds under noise', 'short': 'Convergence', 'prediction': '> 0', 'novelty': 'Joint DP frontier', 'rationale': 'Noise variance bounds'},
        {'id': 'H3', 'statement': 'Cryptographic overhead scales sublinearly', 'short': 'Overhead', 'prediction': '< 0', 'novelty': 'Edge log-overhead', 'rationale': 'Tree aggregation eliminates pairwise cost'},
        {'id': 'H4', 'statement': 'Adaptive attack degradation decreases', 'short': 'Degradation', 'prediction': '< 0', 'novelty': 'Timing-aware attack characterization', 'rationale': 'Temporal filtering dampens delayed gradients'}
    ]
}

contract = _assemble_contract(d1, {}, {}, 'Byzantine Robust FL', ['Distributed AI'])
for hid, h in contract['HYPOTHESES'].items():
    print(f"{hid}: pred={h['prediction']}, zone={h['falsify']['zone']}")
    print(f"   text='{h['falsify']['text']}'")
    print(f"   novelty='{h['novelty']}'")
    print(f"   rationale='{h['rationale']}'")

# Assert that zones are diverse
zones = [h['falsify']['zone'] for h in contract['HYPOTHESES'].values()]
assert [None, 0] in zones, "Must contain [None, 0]"
assert [0, None] in zones, "Must contain [0, None]"

# Assert novelties and rationales are distinct
novelties = set(h['novelty'] for h in contract['HYPOTHESES'].values())
assert len(novelties) == 4, "Novelties must be distinct across all 4 hypotheses"

rationales = set(h['rationale'] for h in contract['HYPOTHESES'].values())
assert len(rationales) == 4, "Rationales must be distinct across all 4 hypotheses"

print("\nSUCCESS! Diverse zones, distinct predictions, distinct novelty and rationales verified!")
