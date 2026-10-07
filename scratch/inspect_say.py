with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/mock/mock-run.ts", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("words.slice(i, i + 2)")
print(text[pos-400:pos+300])
