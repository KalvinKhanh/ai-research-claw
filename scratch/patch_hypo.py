import re

path = r"D:\ai-platform-project\ai-research-platform-fe\src\app\(main)\projects\[projectId]\_components\run-studio\scenes\hypothesize-scene.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """          const reply = turn.reply_to ? byId.get(turn.reply_to) : undefined;
          const depth = depthOf(turn, byId);
          const stance = STANCE[turn.stance];
          const agent = AGENTS[turn.actor];"""

replacement = """          const reply = turn.reply_to ? byId.get(turn.reply_to) : undefined;
          const depth = depthOf(turn, byId);
          const stance = (turn.stance && STANCE[turn.stance]) ? STANCE[turn.stance] : STANCE.propose;
          const agent = (turn.actor && AGENTS[turn.actor]) ? AGENTS[turn.actor] : AGENTS.theorist;"""

assert target in content, "target not found!"
content = content.replace(target, replacement)

reply_target = "{reply && <span className=\"text-muted-foreground\">replying to {AGENTS[reply.actor].name}</span>}"
reply_replacement = "{reply && AGENTS[reply.actor] && <span className=\"text-muted-foreground\">replying to {AGENTS[reply.actor].name}</span>}"
if reply_target in content:
    content = content.replace(reply_target, reply_replacement)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("PATCH APPLIED SUCCESSFULLY")
