path = "d:/ai-platform-project/ai-research-platform-fe/src/app/(main)/projects/[projectId]/_components/run-studio/scenes/synthesize-scene.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                    <span className="col-start-2 flex flex-wrap items-center gap-1 text-muted-foreground text-xs">
                      from the limits of
                      {gap.from.map((id) => (
                        <span key={id} className="inline-flex h-5 items-center rounded-md bg-muted px-1.5 text-[11px]">
                          {label(id)}
                        </span>
                      ))}
                    </span>"""

replacement = """                    {gap.from && gap.from.length > 0 && (
                      <span className="col-start-2 flex flex-wrap items-center gap-1 text-muted-foreground text-xs">
                        from the limits of
                        {(gap.from ?? []).map((id) => (
                          <span key={id} className="inline-flex h-5 items-center rounded-md bg-muted px-1.5 text-[11px]">
                            {label(id)}
                          </span>
                        ))}
                      </span>
                    )}"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched synthesize-scene.tsx successfully!")
else:
    print("Target not found in synthesize-scene.tsx")
