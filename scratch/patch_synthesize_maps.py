path = r"D:\ai-platform-project\ai-research-platform-fe\src\app\(main)\projects\[projectId]\_components\run-studio\scenes\synthesize-scene.tsx"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Add betweenList helper near tension
old_tension_def = "  const tension = data.tensions[0];"
new_tension_def = """  const tension = data.tensions[0];
  const betweenList = Array.isArray(tension?.between)
    ? tension.between
    : typeof tension?.between === "string"
      ? ((tension.between as string).match(/C\\d+/g) ?? ["C1", "C2"])
      : ["C1", "C2"];"""

if old_tension_def in c:
    c = c.replace(old_tension_def, new_tension_def, 1)

# 2. Fix pulled check
c = c.replace("const pulled = tension?.between.includes(cluster.id);", "const pulled = Boolean(betweenList.includes(cluster.id));")

# 3. Fix tension.between[0] and tension.between[1]
c = c.replace("toneOf(tension.between[0]).badge", "toneOf(betweenList[0] ?? 'C1').badge")
c = c.replace("{tension.between[0]}", "{betweenList[0] ?? 'C1'}")
c = c.replace("toneOf(tension.between[1]).badge", "toneOf(betweenList[1] ?? 'C2').badge")
c = c.replace("{tension.between[1]}", "{betweenList[1] ?? 'C2'}")

# 4. Fix tension.between.map
c = c.replace("{tension.between.map((id) => {", "{betweenList.map((id) => {")

# 5. Fix cluster.card_ids.map and cards.map
c = c.replace("{cluster.card_ids.map((id) => (", "{(cluster.card_ids ?? []).map((id) => (")
c = c.replace("{cluster.card_ids.length} paper", "{(cluster.card_ids ?? []).length} paper")
c = c.replace("const cite = new Map(cards.map((c) => [c.id, shortCite(c.citation)]));", "const cite = new Map((cards ?? []).map((c) => [c.id, shortCite(c.citation)]));")
c = c.replace("const rankOf = new Map(data.ranking.map((r) => [r.gap_id, r]));", "const rankOf = new Map((data.ranking ?? []).map((r) => [r.gap_id, r]));")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("SUCCESS: Patched synthesize-scene.tsx with safe mapping guards")
