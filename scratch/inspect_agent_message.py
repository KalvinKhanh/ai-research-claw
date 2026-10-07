with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/mock/mock-run.ts", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("agent.message")
print("In mock-run.ts:", pos)
if pos != -1:
    print(text[pos-100:pos+300])

with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/run-state.ts", "r", encoding="utf-8") as f:
    state_text = f.read()

pos2 = state_text.find("agent.message")
print("In run-state.ts:", pos2)
if pos2 != -1:
    print(state_text[pos2-100:pos2+300])
