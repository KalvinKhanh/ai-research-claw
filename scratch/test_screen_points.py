import random
import hashlib

def generate_screen_points(shortlist, rejected, total_unique, topic):
    topic_hash = int(hashlib.md5(topic.encode("utf-8")).hexdigest(), 16) % 10000000
    rng = random.Random(topic_hash)

    points = []
    fixed = {}
    
    # Disperse shortlist and rejected papers across the sequence
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
        # Ensure non-shortlist papers stay outside keep zone (rel >= 0.7 and qual >= 0.5)
        if rel >= 0.70 and qual >= 0.50:
            rel = round(0.35 + rng.random() * 0.30, 2)
        points.append({
            "id": f"cand_{i+1}",
            "relevance": round(rel, 2),
            "quality": round(qual, 2),
        })

    return points

shortlist = [{"id": f"p{i+1}", "relevance": 0.80 + i * 0.01, "quality": 0.85} for i in range(12)]
rejected = [
    {"id": "rx1", "relevance": 0.75, "quality": 0.74, "false_friend": "sleep"},
    {"id": "rx2", "relevance": 0.72, "quality": 0.70, "false_friend": "exam"},
    {"id": "rx3", "relevance": 0.76, "quality": 0.80, "false_friend": "sleep"},
]

pts = generate_screen_points(shortlist, rejected, 214, "sleep quality exam")
print("Total points generated:", len(pts))
found_rx = [p for p in pts if p["id"].startswith("rx")]
found_p = [p for p in pts if p["id"].startswith("p") and not p["id"].startswith("cand")]
in_zone = [p for p in pts if p["relevance"] >= 0.7 and p["quality"] >= 0.5]
print("Found rejected points:", len(found_rx))
print("Found shortlist points:", len(found_p))
print("Points in keep zone:", len(in_zone))
