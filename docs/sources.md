# Official implementation references

SDK/model references used for this prototype; version pins are in the build files and lockfiles. These links do not establish physical-device results or project-specific model access.

- [LiteRT-LM Kotlin API](https://github.com/google-ai-edge/LiteRT-LM/blob/main/docs/api/kotlin/getting_started.md), [conversation API](https://github.com/google-ai-edge/LiteRT-LM/blob/main/kotlin/java/com/google/ai/edge/litertlm/Conversation.kt), [Google AI Edge Gallery](https://github.com/google-ai-edge/gallery).
- [Gemma 4 edge models](https://developers.google.com/edge/litert-lm/models/gemma-4), [Gemma E2B artifact card](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm). Exact CPU filename, size and SHA-256 are recorded in `contracts/model-artifacts.json`.
- [Nearby Android setup](https://developers.google.com/nearby/connections/android/get-started), [pairing](https://developers.google.com/nearby/connections/android/manage-connections), [official connectivity sample](https://github.com/android/connectivity-samples/tree/main/NearbyConnectionsWalkieTalkie).
- [Configured Gemini model guide](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/guides/gemini-3-8-flash). Run `scripts/probe_gemini.py` to verify availability in the actual project; no fallback model is selected silently.
- [Cloud Run source deployment](https://docs.cloud.google.com/run/docs/deploying-source-code), [public access](https://docs.cloud.google.com/run/docs/authenticating/public), [Firestore transactions](https://docs.cloud.google.com/firestore/native/docs/manage-data/transactions). Deployment references rechecked 18 October 2026.
