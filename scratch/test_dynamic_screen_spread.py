import json
import re
import random
import hashlib

def _generate_screen_points(shortlist, rejected, total_unique, topic):
    topic_hash = int(hashlib.md5(topic.encode("utf-8")).hexdigest(), 16) % 10000000
    rng = random.Random(topic_hash)

    points = []
    fixed = {}
    used_indices = set()

    special_papers = shortlist + rejected
    step = max(1, (total_unique - 15) // max(1, len(special_papers)))

    for i, p in enumerate(special_papers):
        target_idx = 11 + i * step
        idx = target_idx if target_idx < total_unique and target_idx not in used_indices else None
        if idx is None:
            for candidate in range(total_unique):
                if candidate not in used_indices:
                    idx = candidate
                    break
        if idx is not None:
            used_indices.add(idx)
            fixed[idx] = {
                "id": p["id"],
                "relevance": round(float(p.get("relevance", 0.85)), 2),
                "quality": round(float(p.get("quality", 0.85)), 2),
            }

    for i in range(total_unique):
        if i in fixed:
            points.append(fixed[i])
            continue
        rel = min(0.97, max(0.03, 0.18 + rng.random() * 0.5 + (rng.random() - 0.5) * 0.25))
        qual = min(0.98, max(0.05, 0.25 + rng.random() * 0.6))
        rel = round(rel, 2)
        qual = round(qual, 2)
        if rel >= 0.70 and qual >= 0.50:
            rel = round(0.35 + rng.random() * 0.30, 2)
        points.append({
            "id": f"cand_{i+1}",
            "relevance": round(rel, 2),
            "quality": round(qual, 2),
        })

    return points

# Test with 38 points and with 214 points
shortlist = [{"id": f"p{i+1}", "relevance": 0.85, "quality": 0.82} for i in range(12)]
rejected = [
    {"id": "rx1", "relevance": 0.78, "quality": 0.74, "false_friend": "sleep"},
    {"id": "rx2", "relevance": 0.73, "quality": 0.70, "false_friend": "exam"},
    {"id": "rx3", "relevance": 0.76, "quality": 0.81, "false_friend": "sleep"},
]

for total_u in [38, 100, 214, 300]:
    pts = _generate_screen_points(shortlist, rejected, total_u, "sleep exam performance")
    assert len(pts) == total_u
    in_zone = [p for p in pts if p["relevance"] >= 0.70 and p["quality"] >= 0.50]
    print(f"total_u={total_u}: points={len(pts)}, in_zone={len(in_zone)} (expected 15)")
    assert len(in_zone) == 15, f"Failed for {total_u}: in_zone={len(in_zone)}"
    for r in rejected:
        assert any(p["id"] == r["id"] for p in pts), f"Missing {r['id']} in {total_u}"

print("ALL TEST CASES PASSED!")
