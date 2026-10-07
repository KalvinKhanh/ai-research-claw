# Patch paper-scene.tsx
path_paper = r"D:\ai-platform-project\ai-research-platform-fe\src\app\(main)\projects\[projectId]\_components\run-studio\scenes\paper-scene.tsx"
with open(path_paper, "r", encoding="utf-8") as f:
    c = f.read()

t1 = "d.actor === \"you\" ? \"text-amber-800 dark:text-amber-300\" : AGENTS[d.actor].text"
r1 = "d.actor === \"you\" ? \"text-amber-800 dark:text-amber-300\" : (AGENTS[d.actor]?.text ?? \"\")"

t2 = "d.actor === \"you\" ? \"You\" : AGENTS[d.actor].name"
r2 = "d.actor === \"you\" ? \"You\" : (AGENTS[d.actor]?.name ?? d.actor)"

if t1 in c:
    c = c.replace(t1, r1)
if t2 in c:
    c = c.replace(t2, r2)
with open(path_paper, "w", encoding="utf-8") as f:
    f.write(c)

# Patch scene-ui.tsx
path_ui = r"D:\ai-platform-project\ai-research-platform-fe\src\app\(main)\projects\[projectId]\_components\run-studio\scenes\scene-ui.tsx"
with open(path_ui, "r", encoding="utf-8") as f:
    c2 = f.read()

t3 = "!you && AGENTS[actor].text"
r3 = "!you && (AGENTS[actor]?.text ?? \"\")"

if t3 in c2:
    c2 = c2.replace(t3, r3)
with open(path_ui, "w", encoding="utf-8") as f:
    f.write(c2)

print("GUARDED paper-scene.tsx and scene-ui.tsx")
