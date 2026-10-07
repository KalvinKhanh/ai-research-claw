with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/run-store.ts", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("agent.message")
print("In run-store.ts:", pos)
if pos != -1:
    print(text[pos-200:pos+500])
