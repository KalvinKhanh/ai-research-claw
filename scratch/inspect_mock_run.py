with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/mock/mock-run.ts", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("Split it into sub-questions")
print(text[pos:pos+2500])
