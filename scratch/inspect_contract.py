with open("d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/contract.ts", "r", encoding="utf-8") as f:
    text = f.read()

pos = text.find("export type RunEvent =")
print(text[pos:pos+4000])
