# Validation record

## Verified implementation baseline

- 23 Python tests passed on 18 October 2026 in the submission copy; includes a cloud-bootstrap test proving gateway-only authentication, signed originals, idempotent seed uploads and no seeded proposals; also covers duplicate/out-of-order delivery, repeated uploads, SQLite restart, signatures and authorization, preserved conflicts, bounded assessment validation/repair, stale approval rejection and competing resource transactions.
- 9 Android JVM tests passed in the original implementation CI; shared original-byte signature verification, tampering, authorization, packet bounds and assessment validation. Android app/test APKs compile; lint passes with warnings. These results are inherited baseline results until a new repository CI run completes.
- TypeScript/Vite production build passed. The original implementation container built, served dashboard/API and denied an unauthenticated write in CI.
- A three-store SQLite test simulates transfer and restart; it does not exercise Room or physical Nearby radios. Schema tests use authored fixtures; they are not model-quality evaluation results.

## Acceptance still pending

Actual Gemma device/model identity, checksum, load and inference latency; physical Nearby pairing and A-to-B-to-C relay after restart; executed Room instrumentation; real Gemini outputs and evaluation scores; live Firestore transactions; deployed Cloud Run and OAuth coordinator approval.

The five evaluation cases in `evals/` are separate from the showcased seed. No model scores are claimed. Every model failure must preserve evidence and appear as a failure.

## Submission-copy commands executed on 18 October 2026

- `python -m pytest -q`: 23 passed in 0.46 s; one Starlette/httpx deprecation warning. Run with the existing Python 3.11 virtual environment against this copy.
- `npm ci --prefix web --offline`: successful, 70 packages audited, zero vulnerabilities reported.
- `npm run build --prefix web`: TypeScript/Vite passed, 1578 modules.
- `bash -n scripts/deploy.sh scripts/deploy_demo.sh`: successful.
- `python -m compileall -q server scripts`: successful.

Cloud Shell scripts were not executed on GCP. New-repository CI results, when available, supersede the inherited build baseline.
