# AutoResearchClaw Paper-Only Input Sample

This bundle contains:

1. `paper_input_contract_v1.md` — proposed source-informed input contract.
2. `paper-input/` — the public/external package a research system should produce.
3. `adapter-materialized/` — an example of how the adapter maps those files into the
   `stage-*` artifact layout already read by AutoResearchClaw.

The benchmark data inside this bundle were measured locally while generating the fixture.
The study is intentionally trivial and exists only to validate the integration contract.

Start by reading `paper_input_contract_v1.md`, then compare:
- `paper-input/evidence/*`
- `adapter-materialized/stage-12` through `stage-15`.
