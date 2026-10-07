import re

# 1. Patch scene-ui.tsx
path_ui = "d:/ai-platform-project/ai-research-platform-fe/src/app/(main)/projects/[projectId]/_components/run-studio/scenes/scene-ui.tsx"
with open(path_ui, "r", encoding="utf-8") as f:
    content_ui = f.read()

pattern_typetext = re.compile(
    r"/\*\* Types `text` out at `speed` characters a second while live; shows it whole otherwise\. \*/\s*"
    r"export function TypeText\(\{[\s\S]*?return \(\s*<span className=\{className\}>[\s\S]*?</span>\s*\);\s*\}",
    re.MULTILINE
)

replacement_typetext = """/** Types `text` out at `speed` characters a second while live; shows it whole otherwise. */
export function TypeText({
  text,
  live,
  speed = 110,
  className,
}: {
  text: any;
  live: boolean;
  speed?: number;
  className?: string;
}) {
  const safeText =
    typeof text === "string"
      ? text
      : typeof text === "object" && text !== null
        ? ((text as any).text ?? (text as any).value ?? (text as any).statement ?? JSON.stringify(text))
        : String(text ?? "");

  const [shown, setShown] = useState(live ? 0 : safeText.length);
  useEffect(() => {
    if (!live || typeof window === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(safeText.length);
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const next = Math.min(safeText.length, Math.round(((now - t0) / 1000) * speed));
      setShown(next);
      if (next < safeText.length) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [safeText, live, speed]);
  return (
    <span className={className}>
      {safeText.slice(0, shown)}
      {shown < safeText.length && <Caret />}
    </span>
  );
}"""

if pattern_typetext.search(content_ui):
    content_ui = pattern_typetext.sub(replacement_typetext, content_ui)
    with open(path_ui, "w", encoding="utf-8") as f:
        f.write(content_ui)
    print("Patched TypeText in scene-ui.tsx successfully!")
else:
    print("Could not match TypeText pattern in scene-ui.tsx")

# 2. Patch scope-scene.tsx for safe slice of data.approved.at
path_scope = "d:/ai-platform-project/ai-research-platform-fe/src/app/(main)/projects/[projectId]/_components/run-studio/scenes/scope-scene.tsx"
with open(path_scope, "r", encoding="utf-8") as f:
    content_scope = f.read()

target_scope = "Saved {data.approved.at.slice(0, 10)} · {data.approved.at.slice(11, 16)} UTC"
replacement_scope = "Saved {data.approved.at ? `${data.approved.at.slice(0, 10)} · ${data.approved.at.slice(11, 16)} UTC` : 'recently'}"

if target_scope in content_scope:
    content_scope = content_scope.replace(target_scope, replacement_scope)
    with open(path_scope, "w", encoding="utf-8") as f:
        f.write(content_scope)
    print("Patched scope-scene.tsx successfully!")
else:
    print("Target scope slice string not found or already patched")
