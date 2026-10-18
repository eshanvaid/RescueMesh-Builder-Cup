# RescueMesh demo video - Double Descent

Target: **3 minutes 30 seconds**. Required range: **3-4 minutes**, including title/end cards. Team lead: Eshan Vaid.

This script demonstrates today's verified dashboard behavior. It does not claim a real phone inference, radio exchange, cloud deployment or model-generated assessment. A video made entirely from slides will not demonstrate the working application. The current preview also cannot establish the full end-to-end acceptance scenario.

## Before recording

1. Deploy using `docs/deployment.md` in the public repository and run its smoke checks. If deployment has not happened, record the local app as a **local prototype** and understand that the mandatory deployed-link requirement remains unmet. Never replace an address bar to make localhost look deployed.
2. Use a fresh browser session at the actual working URL. Select River School. Confirm three incidents, four observations and one structured-claim conflict. Keep **synthetic data / simulated transport** visible.
3. Set a readable browser zoom and 1920x1080 recording area where available. Close unrelated tabs and notifications. Keep tokens, terminal environment output, provisioning bundles, account menus and personal information out of frame.
4. Prepare a clean terminal at the submission repository with the environment activated. Rehearse `python -m pytest -q`; it must show the actual 23-test result. Do not display a copied result as a live run.
5. On macOS, press Shift-Command-5, choose the application/window area and select your microphone in Options. Do a ten-second audio check. Record real interactions; a narration recorded separately is fine if it describes exactly what the viewer sees.

## Timed narration and shot list

| Time | Show / do | Narration |
|---|---|---|
| 0:00-0:20 | Title for 3 seconds, then live dashboard. Keep cursor still. | “We are Double Descent, and this is RescueMesh. During a disaster, responders can lose internet access while reports keep changing. RescueMesh is our prototype for preserving those reports, keeping their sources visible, and supporting human-reviewed response decisions.” |
| 0:20-0:45 | Point to the synthetic banner, three counters and schematic map. Click East Bridge, then Hill Clinic. | “This is the working dashboard using synthetic exercise data. River School, East Bridge and Hill Clinic contain four signed observations. This preview uses host-generated events and simulated phone transport. The map is schematic, and its dashed routes do not establish that any approach is safe.” |
| 0:45-1:15 | Select River School; open Evidence and scroll to both original reports. Point to source IDs and sequences. | “At River School, one responder reports the north footpath clear from their position. Another reports it blocked from the east side. Both originals remain visible, with source device, sequence and event ID. We preserve the signed source bytes; an assessment is stored separately and cannot silently rewrite the evidence.” |
| 1:15-1:45 | Click Conflicts & questions. Click a citation, observe navigation to its source. Return to the conflict tab. | “The conflict view links directly to both reports. The conflict you see here is detected by comparing explicit structured claims, not by model inference. Clicking a supporting event takes us back to the source. This gives a coordinator a specific disagreement to investigate instead of presenting a generated summary as established fact.” |
| 1:45-2:10 | Open Relay history, point to gateway/origin fields and transport disclosure. | “Relay history distinguishes event origin from the gateway that delivered it. The Android application implements durable Room storage, foreground Nearby pairing, missing-event inventories and retries. Those integrations compile, but this recording is not evidence of physical radio relay. The three-phone restart and forwarding test remains pending.” |
| 2:10-2:35 | Click Proposals, then Reassess with Gemini while signed out. Show coordinator login requirement, then close the dialog. | “Central reassessment and resource approval require coordinator authentication. The Google model integrations are designed to cite evidence, preserve unknowns and ask a useful follow-up. A model may propose a response; it cannot approve one. We do not display an invented assessment when actual inference has not run.” |
| 2:35-2:55 | Briefly show the architecture slide, then return to the app. | “The Google architecture combines Gemma through LiteRT-LM on Android, Nearby between phones, and a FastAPI and React service prepared for Cloud Run. Firestore stores cloud mission state; Gemini reassesses combined evidence. Firestore is in the Firebase ecosystem. We do not use Firebase Hosting or Firebase Authentication.” |
| 2:55-3:15 | Run the real test command in the clean terminal; show the result. Return to dashboard. | “The submitted snapshot passes twenty-three Python tests, including signed ingestion, duplicate uploads, persistence, conflicts and stale approval protection. Public submission CI passes nine Android JVM tests, and the web production build passes. These results validate application logic; they do not establish device inference latency or live-cloud model quality.” |
| 3:15-3:30 | End card: project name, public repository and actual prototype URL only if verified. | “RescueMesh keeps source evidence and uncertainty visible while reserving resource decisions for people. Our remaining acceptance gates are real offline inference, physical relay and the complete deployed AI approval loop. Thank you.” |

Narration is approximately 450 words. Rehearse at a natural pace and use pauses for the clicks. Keep the final export between 3:00 and 4:00; aim for 3:30 rather than the upper limit.

## If real cloud inference is completed before recording

Replace the 2:10-2:35 segment only after authenticated Gemini reassessment actually succeeds. Show the real provider/model, source citations, missing information and proposed response. Say: “This is the actual Gemini assessment of the current evidence. Its cited disagreement and next question are visible, and its proposed response still needs human review.” Keep physical Gemma and radio testing explicitly pending unless separately proven.

To claim revision, actually add/synchronize new contradictory evidence, reassess again and show the changed proposal and preserved originals. To claim approval, actually verify the synthetic prerequisites, approve while authenticated and show the resulting human-confirmed record. Do not narrate either behavior over a static screenshot or unit-test fixture. Trim other narration to stay under four minutes.

## If real phone proof is available

Use a short continuous clip showing internet disabled, model identity, report entry, actual inference, citations and measured latency. Replace 20-30 seconds of architecture/testing footage. Do not label a desktop model, cloud response, emulator or mock screen as physical offline Gemma. The Android wireframes in the deck are design illustrations, not device proof.

## Editing and publication

- Prefer one screen recording with modest cuts. Keep clicks, resulting state and important timestamps/labels visible. Never accelerate model waiting time without an explicit on-screen speed-up label.
- Use clear narration and readable captions. Avoid music covering speech, lengthy logos or a pitch-only monologue.
- Export MP4, H.264 video and AAC audio, 1080p/30 fps where available. Watch the exported file from start to finish and check its real duration.
- Upload as an accessible, unlisted YouTube video or an organizer-accepted video host with viewer access enabled. This task prepares the script; it does not create or upload a recorded video.
- Open the final video URL in an incognito window. Confirm no permission request, account login or expired sharing link blocks playback. Leave it available throughout evaluation.
- Paste the real URL into the submission form and deck. Do not submit a local MP4 path, private editor link or an example URL.

## Final checks

- 3-4 minutes total; real UI interactions occupy most of the video.
- All data synthetic; actual inference provider and simulated transport disclosed.
- No credentials or unrelated personal information visible.
- No claim that blocked hardware/cloud acceptance passed.
- Prototype, public repository and video links open without special evaluator access.
