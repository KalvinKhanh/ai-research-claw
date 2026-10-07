import json
import random
import hashlib
import re

def _generate_screen_points(shortlist, rejected, total_unique, topic):
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
            rel = round(0.40 + rng.random() * 0.28, 2)
        points.append({
            "id": f"cand_{i+1}",
            "relevance": round(rel, 2),
            "quality": round(qual, 2),
        })

    return points

# Test with mock LLM output
topic = "Impact of sleep duration and exam anxiety on undergraduate GPA"
domains = ["Sleep Science", "Cognitive Psychology"]

d2_mock = {
    "shortlist": [
        {
            "id": f"p{i+1}",
            "citation": f"Author {i+1} et al., 202{i%4}",
            "title": f"Sleep quality, duration and academic scores in undergraduates study {i+1}",
            "venue": "Sleep Medicine Reviews",
            "year": 2020 + (i % 4),
            "relevance": 0.85,
            "quality": 0.80,
            "reason": "Kept because large cohort study with standardized GPA metrics.",
        }
        for i in range(12)
    ],
    "rejected": [
        {
            "id": "rx1",
            "title": "Adaptive sleep modes in wireless ad-hoc sensor networks",
            "venue": "IEEE Sensors",
            "false_friend": "sleep",
            "reason": "Hardware radio states, not human physiology.",
            "relevance": 0.78,
            "quality": 0.74,
        },
        {
            "id": "rx2",
            "title": "Exam scheduling using constraint satisfaction algorithms",
            "venue": "Computers & Operations Research",
            "false_friend": "exam",
            "reason": "Logistical timetabling, not student academic performance.",
            "relevance": 0.73,
            "quality": 0.70,
        },
        {
            "id": "rx3",
            "title": "Continuous sleep tracking in elderly nursing home residents with dementia",
            "venue": "Geriatric Medicine",
            "false_friend": "sleep",
            "reason": "Clinical geriatric population far from university undergraduates.",
            "relevance": 0.76,
            "quality": 0.81,
        },
    ]
}

# Process shortlist
shortlist = []
for idx, p in enumerate(d2_mock["shortlist"][:12]):
    pid = f"p{idx+1}"
    reason = str(p.get("reason", "")).strip()
    if reason.lower().startswith("kept because "):
        reason = reason[13:].strip()
    shortlist.append({
        "id": pid,
        "citation": p["citation"],
        "title": p["title"],
        "venue": p["venue"],
        "year": p["year"],
        "relevance": p["relevance"],
        "quality": p["quality"],
        "reason": reason,
        "source": "OpenAlex",
        "citations": 500,
    })

# Process rejected
topic_clean_words = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in topic.split()]
topic_candidates = [w for w in topic_clean_words if len(w) >= 4 and w.lower() not in {"with", "that", "this", "from", "into", "over", "under", "about", "effect", "effects", "study", "analysis"}]
default_keyword = topic_candidates[0] if topic_candidates else "sleep"

rejected = []
for idx in range(3):
    r_item = d2_mock["rejected"][idx]
    rx_id = f"rx{idx+1}"
    title = str(r_item.get("title", "")).strip()
    venue = str(r_item.get("venue", "")).strip()
    false_friend = str(r_item.get("false_friend", default_keyword)).strip()
    false_friend = re.sub(r'[^a-zA-Z0-9]', '', false_friend)
    if not false_friend or false_friend.lower() not in title.lower():
        matched_word = next((w for w in topic_candidates if w.lower() in title.lower()), None)
        if matched_word:
            false_friend = matched_word
        else:
            false_friend = topic_candidates[idx % len(topic_candidates)] if topic_candidates else default_keyword
            title = f"{title.rstrip('.')} with {false_friend} optimization"

    rejected.append({
        "id": rx_id,
        "title": title,
        "venue": venue,
        "false_friend": false_friend,
        "reason": r_item.get("reason", ""),
        "relevance": r_item.get("relevance", 0.75),
        "quality": r_item.get("quality", 0.72),
    })

pts = _generate_screen_points(shortlist, rejected, 214, topic)

print(f"Generated {len(pts)} points")
in_zone = [p for p in pts if p["relevance"] >= 0.70 and p["quality"] >= 0.50]
print(f"In zone: {len(in_zone)} (expected 15)")
print(f"Below bar: {len(pts) - len(in_zone)} (expected 199)")
print("Shortlist reason[0]:", shortlist[0]["reason"])

for r in rejected:
    p = next((x for x in pts if x["id"] == r["id"]), None)
    print(f"Rejected dot {r['id']}: found={p is not None}, false_friend='{r['false_friend']}', title='{r['title']}'")
    parts = re.split(f"({r['false_friend']})", r["title"], flags=re.IGNORECASE)
    assert any(pt.lower() == r['false_friend'].lower() for pt in parts)
    print("  Highlight parts:", parts)

print("SUCCESS!")
