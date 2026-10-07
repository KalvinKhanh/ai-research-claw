import json
import re
from researchclaw.pipeline.llm_pipeline_generator import _assemble_contract

d1 = {
    "working_title": "Sleep and Exam Performance Study",
    "problem": "Sleep loss impairs cognition.",
    "objective": "Quantify effect of sleep duration on exam grades.",
    "scope_boundary": "Undergraduates in higher education.",
    "success_criteria": "Adjusted R-squared > 0.35.",
    "sub_questions": [
        {"id": "SQ1", "text": "Does sleep duration predict GPA?", "priority": 1, "covers": ["duration"]},
        {"id": "SQ2", "text": "Does exam anxiety moderate sleep benefits?", "priority": 2, "covers": ["anxiety"]},
    ],
    "hypotheses": [
        {"id": "H1", "statement": "Greater sleep duration increases exam scores.", "short": "Sleep duration", "prediction": "> 0", "outcome": "exam_score", "exposure": "sleep_hours", "estimand": "Beta"},
        {"id": "H2", "statement": "Anxiety dampens sleep gains.", "short": "Anxiety moderation", "prediction": "< 0", "outcome": "exam_score", "exposure": "anxiety_interaction", "estimand": "Beta"},
    ],
    "gaps": [{"id": "G1", "text": "Lack of objective actigraphy sleep measures in exams.", "from": ["p1", "p2"]}],
    "queries": [{"id": "q1", "text": "sleep duration undergraduate exam performance", "estimated_hits": 60}],
}

d2 = {
    "shortlist": [
        {
            "id": f"p{i+1}",
            "citation": f"Author {i+1} et al., 202{i%4}",
            "title": f"The effect of sleep on academic performance: Study {i+1}",
            "venue": "Sleep Medicine Reviews",
            "year": 2020 + (i % 4),
            "relevance": 0.85,
            "quality": 0.82,
            "reason": "Kept because large cohort of university students.",
        }
        for i in range(12)
    ],
    "rejected": [
        {
            "id": "rx1",
            "title": "Adaptive sleep scheduling in wireless sensor networks",
            "venue": "IEEE Sensors",
            "false_friend": "sleep",
            "reason": "About radio sleep cycles, not people.",
            "relevance": 0.78,
            "quality": 0.74,
        },
        {
            "id": "rx2",
            "title": "Exam timetabling with integer programming",
            "venue": "Computers & Operations Research",
            "false_friend": "exam",
            "reason": "About scheduling exams, not student grades.",
            "relevance": 0.73,
            "quality": 0.70,
        },
        {
            "id": "rx3",
            "title": "Clinical sleep apnea outcomes in elderly patients",
            "venue": "Sleep Medicine",
            "false_friend": "sleep",
            "reason": "Elderly clinical population, not undergraduates.",
            "relevance": 0.75,
            "quality": 0.81,
        },
    ]
}

d3 = {
    "turns": [{"id": "t1", "actor": "theorist", "stance": "propose", "about": "H1", "text": "Sleep supports memory consolidation."}],
    "clusters": [{"id": "C1", "title": "Memory Consolidation", "claim": "Sleep promotes synaptic plasticity.", "card_ids": ["p1", "p2"]}],
    "tension": {"between": ["C1", "C2"], "text": "Tension between duration and quality."},
}

topic = "Sleep quality and exam performance in college students"
domains = ["Sleep Science", "Cognitive Psychology"]

contract = _assemble_contract(d1, d2, d3, topic, domains)

print("=== VALIDATING CONTRACT ===")
coll_unique = contract["COLLECTED"]["unique"]
screen_pts = contract["SCREEN_POINTS"]
print(f"COLLECTED unique: {coll_unique}")
print(f"SCREEN_POINTS length: {len(screen_pts)}")
assert len(screen_pts) == coll_unique, f"Length mismatch: {len(screen_pts)} != {coll_unique}"

# Keep zone check
rMin = 0.70
qMin = 0.50
in_zone = [p for p in screen_pts if p["relevance"] >= rMin and p["quality"] >= qMin]
kept_ids = set(p["id"] for p in contract["SHORTLIST"])
rej_ids = set(p["id"] for p in contract["REJECTED"])

print(f"In zone count: {len(in_zone)} (Expected: 15)")
assert len(in_zone) == 15, f"Expected 15 in keep zone, got {len(in_zone)}"

print(f"Legend: Kept · {len(contract['SHORTLIST'])} · Wrong field · {len(contract['REJECTED'])} · Below a bar · {len(screen_pts) - len(in_zone)}")

# Check shortlist reason formatting
assert not contract["SHORTLIST"][0]["reason"].lower().startswith("kept because"), "Shortlist reason should NOT start with 'Kept because'!"
print("Shortlist[0] reason:", contract["SHORTLIST"][0]["reason"])

# Check rejected items matching
for r in contract["REJECTED"]:
    pt = next((p for p in screen_pts if p["id"] == r["id"]), None)
    assert pt is not None, f"Rejected paper {r['id']} missing from screen points!"
    print(f"Rejected {r['id']}: ({pt['relevance']}, {pt['quality']}), label: \"{r['false_friend']}\"")
    
    parts = re.split(f"({r['false_friend']})", r["title"], flags=re.IGNORECASE)
    has_match = any(p.lower() == r["false_friend"].lower() for p in parts)
    assert has_match, f"Rejected title '{r['title']}' does not contain false_friend '{r['false_friend']}'!"
    print(f"  Highlighted title parts: {parts}")

print("ALL CONTRACT VALIDATIONS PASSED PERFECTLY!")
