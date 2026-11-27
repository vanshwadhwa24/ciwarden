# Traces
Hash-chained JSONL (`python3 -c "from ciwarden import trace; print(trace.verify('FILE'))"`).
- real-failed-run-46054303024--no-model-escalate.jsonl: real failed GitHub Actions run, fetched live, reproduced 3/3 in the sandbox, no model, escalated, dry-run (no writes).
- real-failed-run-46054303024--STUB-MODEL.jsonl: same run with a SCRIPTED STAND-IN model, not an LLM. Shows fix verification and PR planning. PR #1 was later opened from it with human approval of the wording. Not a model result.
- Trap Pack traces: tests/trap-pack/traces/.
