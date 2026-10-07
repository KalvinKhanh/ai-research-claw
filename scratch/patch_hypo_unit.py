path = r"D:\ai-platform-project\ai-research-platform-fe\src\app\(main)\projects\[projectId]\_components\run-studio\scenes\hypothesize-scene.tsx"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

target = "Exam points. The result's 95% range must stay out of the red."
replacement = "{(h.falsify as any)?.unit ? `${(h.falsify as any).unit}. ` : 'Standardized effect size. '}The result's 95% range must stay out of the red."

if target in c:
    c = c.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("SUCCESS: Patched Exam points in hypothesize-scene.tsx")
else:
    print("NOT FOUND")
