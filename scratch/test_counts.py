def test():
    shortlist = [{"id": f"p{i+1}", "relevance": 0.78 + (i % 5) * 0.03, "quality": 0.80 + (i % 4) * 0.04} for i in range(12)]
    rejected = [
        {"id": "rx1", "title": "Adaptive sleep scheduling for energy-efficient wireless sensor networks", "false_friend": "sleep", "relevance": 0.78, "quality": 0.74},
        {"id": "rx2", "title": "Exam timetabling with integer programming", "false_friend": "exam", "relevance": 0.73, "quality": 0.69},
        {"id": "rx3", "title": "CPAP adherence and sleep apnea outcomes in adults over 65", "false_friend": "sleep", "relevance": 0.75, "quality": 0.81},
    ]
    total_unique = 214
    
    import random, hashlib
    topic = "sleep quality exam score"
    topic_hash = int(hashlib.md5(topic.encode("utf-8")).hexdigest(), 16) % 10000000
    rng = random.Random(topic_hash)

    points = []
    fixed = {}

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
        rel = min(0.97, max(0.03, 0.18 + rng.random() * 0.5 + (rng.random() - 0.5) * 0.25))
        qual = min(0.98, max(0.05, 0.25 + rng.random() * 0.6))
        if rel >= 0.70 and qual >= 0.50:
            rel = round(0.35 + rng.random() * 0.30, 2)
        points.append({
            "id": f"p_cand_{i+1}",
            "relevance": round(rel, 2),
            "quality": round(qual, 2),
        })

    kept_set = set(p["id"] for p in shortlist)
    rej_set = set(p["id"] for p in rejected)
    in_zone = [p for p in points if p["relevance"] >= 0.7 and p["quality"] >= 0.5]
    kept_in_zone = [p for p in in_zone if p["id"] in kept_set]
    rej_in_zone = [p for p in in_zone if p["id"] in rej_set]
    below_bar = [p for p in points if p["id"] not in kept_set and p["id"] not in rej_set]

    print(f"Total points: {len(points)}")
    print(f"Total in keep zone: {len(in_zone)} (Kept: {len(kept_in_zone)}, Rejected: {len(rej_in_zone)})")
    print(f"Below bar: {len(below_bar)}")
    print(f"Legend: Kept {len(shortlist)} · Wrong field {len(rejected)} · Below a bar {len(below_bar)}")

test()
