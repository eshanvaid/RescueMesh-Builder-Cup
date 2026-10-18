# Dependency and model notices

Source references and lockfiles are retained for reproducibility. Public repository access does not declare a license for the application or confer rights to third-party SDKs or models.

Verified cached Maven POM metadata for selected direct dependencies declares:

| Component | Version | POM license declaration |
|---|---|---|
| AndroidX Activity Compose | 1.10.1 | Apache License 2.0 |
| AndroidX Lifecycle Runtime KTX | 2.9.0 | Apache License 2.0 |
| kotlinx-coroutines-android | 1.10.2 | Apache License 2.0 |
| kotlinx-serialization-json | 1.9.0 | Apache License 2.0 |
| LiteRT-LM Android | 0.18.0 | Apache License 2.0 |
| Google Play services Nearby | 19.5.1 | Android Software Development Kit License |

This is not an exhaustive transitive dependency/license audit. Runtime packages, native libraries, samples and model artifacts can have separate terms. Consult the [Android SDK terms](https://developer.android.com/studio/terms.html), [LiteRT-LM source](https://github.com/google-ai-edge/LiteRT-LM), [Google AI Edge Gallery source](https://github.com/google-ai-edge/gallery), [Nearby sample source](https://github.com/android/connectivity-samples/tree/main/NearbyConnectionsWalkieTalkie) and the [model card](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm).

Do not bundle model weights or credentials. Verify downstream notice and redistribution obligations before distributing binaries. Changing repository history or adding a project license does not determine an unidentified snippet's provenance.
