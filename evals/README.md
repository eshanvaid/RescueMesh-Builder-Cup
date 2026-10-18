# Separate assessment evaluation set

These five cases are separate from the dashboard seed/demo. Reports are synthetic inputs, not expected model outputs. No evaluation of real model behavior has run yet: GCP and phone are unavailable.

Run `.venv/bin/python scripts/evaluate.py --out artifacts/gemini-eval.json` with GCP project and ADC configured. It performs real Gemini inference only. Invalid configuration exits with BLOCKED, never a fake assessment. Exact citations and schema are automatically checked; lexical question themes are a weak screening measure, not a judgment of usefulness. A human must grade useful questions, preserved uncertainty, malicious-instruction handling and warranted response revisions on 0–2 each. Record provider/model, latency, actual output and scores.

On the phone, enter each case using new incident IDs `eval-{id}`, run real offline inference, capture evidence and fill the same rubric. For `revision-check`, capture the first assessment, append the additional report, and capture the revised assessment. Do not use a cloud response as a substitute for the phone result.
