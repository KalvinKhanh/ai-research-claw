import re
import json
from pathlib import Path

disc_path = Path(r"d:\ai-platform-project\ai-research-platform-fe\src\lib\run-stream\mock\discovery.ts")
scen_path = Path(r"d:\ai-platform-project\ai-research-platform-fe\src\lib\run-stream\mock\scenario.ts")

# We can run a small node script with sucrase or @swc or esbuild or typescript
# Let's see if typescript is in node_modules
import subprocess

node_script = """
const fs = require('fs');
const ts = require('d:/ai-platform-project/ai-research-platform-fe/node_modules/typescript');

function transpileAndEval(filePath) {
    const code = fs.readFileSync(filePath, 'utf8');
    const js = ts.transpile(code, { module: ts.ModuleKind.CommonJS });
    const module = { exports: {} };
    const fn = new Function('exports', 'require', 'module', '__filename', '__dirname', js);
    fn(module.exports, require, module, filePath, '');
    return module.exports;
}

try {
    const scen = transpileAndEval('d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/mock/scenario.ts');
    const disc = transpileAndEval('d:/ai-platform-project/ai-research-platform-fe/src/lib/run-stream/mock/discovery.ts');
    
    const output = {
        GOAL: disc.GOAL,
        COMPUTE: disc.COMPUTE,
        ESTIMATES: disc.ESTIMATES,
        ESTIMATE_CHECKS: disc.ESTIMATE_CHECKS,
        SCOPE_ADJUSTED: disc.SCOPE_ADJUSTED,
        SUB_QUESTIONS: disc.SUB_QUESTIONS,
        RISKS: disc.RISKS,
        TOPIC_SCORES: disc.TOPIC_SCORES,
        TOPIC_ADVICE: disc.TOPIC_ADVICE,
        STRATEGIES: disc.STRATEGIES,
        QUERIES: disc.QUERIES,
        SOURCES: disc.SOURCES,
        HITS: disc.HITS,
        MERGED: disc.MERGED,
        COLLECTED: disc.COLLECTED,
        SCREEN_RULES: disc.SCREEN_RULES,
        SHORTLIST: disc.SHORTLIST,
        REJECTED: disc.REJECTED,
        CARDS: disc.CARDS,
        CLUSTERS: disc.CLUSTERS,
        TENSION: disc.TENSION,
        OVERVIEW: disc.OVERVIEW,
        GAPS: disc.GAPS,
        RANKING: disc.RANKING,
        DEBATES: disc.DEBATES,
        HYPOTHESES: scen.HYPOTHESES
    };
    
    fs.writeFileSync('d:/AutoResearchClaw/researchclaw/pipeline/full_pipeline_data.json', JSON.stringify(output, null, 2), 'utf8');
    console.log('SUCCESS: full_pipeline_data.json generated! Cards count:', disc.CARDS.length, 'Hypotheses count:', Object.keys(scen.HYPOTHESES).length);
} catch (e) {
    console.error('ERROR in transpileAndEval:', e);
    process.exit(1);
}
"""

Path(r"d:\AutoResearchClaw\scratch\transpile_dump.js").write_text(node_script, encoding="utf-8")
res = subprocess.run(["node", r"d:\AutoResearchClaw\scratch\transpile_dump.js"], cwd=r"d:\ai-platform-project\ai-research-platform-fe", capture_output=True, text=True)
print("Return code:", res.returncode)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
