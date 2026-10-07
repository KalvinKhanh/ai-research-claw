import re
import random
import hashlib

def generate_screen_points(shortlist, rejected, total_unique, topic):
    topic_hash = int(hashlib.md5(topic.encode("utf-8")).hexdigest(), 16) % 10000000
    rng = random.Random(topic_hash)

    points = []
    fixed = {}

    # Disperse shortlist and rejected papers across the sequence (matches mock discovery.ts: 11 + i * 13)
    special_papers = shortlist + rejected
    for i, p in enumerate(special_papers):
        idx = min(total_unique - 1, 11 + i * 13)
        fixed[idx] = {
            "id": p["id"],
            "relevance": round(float(p.get("relevance", 0.85)), 2),
            "quality": round(float(p.get("quality", 0.85)), 2),
        }

    for i in range(total_unique):
        if i in fixed:
            points.append(fixed[i])
            continue
        # Most candidates are loosely related: low relevance, mixed quality. None reaches keep zone.
        rel = min(0.97, max(0.03, 0.18 + rng.random() * 0.5 + (rng.random() - 0.5) * 0.25))
        qual = min(0.98, max(0.05, 0.25 + rng.random() * 0.6))
        # Ensure non-shortlist papers stay outside keep zone (rel >= 0.70 and qual >= 0.50)
        if rel >= 0.70 and qual >= 0.50:
            rel = round(0.40 + rng.random() * 0.28, 2)
        points.append({
            "id": f"p{i}",
            "relevance": round(rel, 2),
            "quality": round(qual, 2),
        })

    return points

shortlist = [
    {"id": f"p{i+1}", "citation": f"Author et al., 202{i%4}", "title": f"Study {i+1}", "venue": "Nature", "year": 2020 + i%4, "relevance": round(0.75 + (i%5)*0.04, 2), "quality": round(0.70 + (i%4)*0.06, 2), "reason": "Empirical benchmark."}
    for i in range(12)
]
rejected = [
    {"id": "rx1", "title": "Adaptive sleep scheduling for energy-efficient wireless sensor networks", "venue": "IEEE Sensors Journal", "false_friend": "sleep", "reason": "About radios switching to sleep mode, not people.", "relevance": 0.78, "quality": 0.74},
    {"id": "rx2", "title": "Exam timetabling with integer programming", "venue": "Computers & Operations Research", "false_friend": "exam", "reason": "About scheduling exams, not how students score.", "relevance": 0.73, "quality": 0.69},
    {"id": "rx3", "title": "CPAP adherence and sleep apnea outcomes in adults over 65", "venue": "Sleep Medicine", "false_friend": "sleep", "reason": "A clinical population far from undergraduates.", "relevance": 0.75, "quality": 0.81},
]

total_unique = 214
points = generate_screen_points(shortlist, rejected, total_unique, "sleep exam performance")

# Test frontend logic
rMin = 0.7
qMin = 0.5
in_zone = [p for p in points if p["relevance"] >= rMin and p["quality"] >= qMin]
kept_ids = set(p["id"] for p in shortlist)
rej_ids = set(p["id"] for p in rejected)

print(f"Total points: {len(points)}")
print(f"In zone count: {len(in_zone)} (expected 15)")
print(f"Aside header: {len(points)} of {total_unique} scored · {len(in_zone)} in the keep zone")

below_bar = len(points) - len(in_zone)
print(f"Legend: Kept · {len(shortlist)}  Wrong field · {len(rejected)}  Below a bar · {below_bar}")

# Test rejected point lookup
for r in rejected:
    pt = next((p for p in points if p["id"] == r["id"]), None)
    assert pt is not None, f"Rejected point {r['id']} not found in points!"
    print(f"Found {r['id']}: ({pt['relevance']}, {pt['quality']}) with label \"{r['false_friend']}\"")
    # Test title regex split
    parts = re.split(f"({r['false_friend']})", r["title"], flags=re.IGNORECASE)
    matches = [p for p in parts if p.lower() == r["false_friend"].lower()]
    assert len(matches) > 0, f"false_friend '{r['false_friend']}' not matched in '{r['title']}'"
    print(f"  Title regex match parts: {parts}")

print("ALL CHECKS PASSED!")
