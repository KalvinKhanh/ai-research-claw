with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/mock/mock-run.ts", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("async runStage")
if pos == -1:
    pos = text.find("runStage")
print(text[pos:pos+3000])
