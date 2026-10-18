# Physical device acceptance

Status: **NOT RUN**. Emulator tests cannot satisfy physical radio or offline hardware acceptance.

## Single-phone offline inference

1. Install the debug APK and open RescueMesh. Record manufacturer/model, Android version, RAM, available storage, APK checksum and LiteRT-LM runtime version (0.18.0). A physical phone needs a supported 64-bit ABI; allow at least 8 GB free for the model import's temporary duplication.
2. Obtain the CPU `gemma-4-E2B-it.litertlm` from the official model card linked in `contracts/model-artifacts.json`. Verify its 2,588,147,712-byte size and SHA-256 `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`. Import through **Model → Import .litertlm weights**. Never disable checksum validation to make a model load.
3. Disable Wi-Fi and mobile data; record the network settings. Use **Load real model and measure** and record actual load time. In **Report**, use incident `offline-spike-01`, River School, and enter: `Synthetic: six people wait upstairs. Water is rising at the entrance. Depth and access route are unknown.` Save source evidence, then run the real offline assessment.
4. Record actual output, latency, useful follow-up and supporting event IDs. Answer the generated question and run reassessment, preserving both source reports. Add a contradictory approach report and inspect the revision. A failure is a failure; no cloud output may substitute for this test.
5. Force-stop and reopen the application; verify original IDs remain. Run `./scripts/capture_device.sh` after actual inference, review its telemetry/screenshots and record the results without publishing credentials or weights.

Record cold/warm model load, initial/revised inference time, official checksum, exact phone/runtime/backend, network evidence, citation correctness, useful-question score, preserved uncertainty and restart outcome. The assessment must appear while internet access is unavailable.

## Nearby spike (two physical phones)

1. Install the same APK on both. Export identities through **Nearby → Export public device identity**. Copy these public JSON files to the host.
2. Run `.venv/bin/python scripts/provision.py identity-A.json identity-B.json --out local-demo/two-phones`. Transfer only `trust.json` to both phones, then import it through Nearby. Do not transfer backend `auth.json` to a phone.
3. Enable Bluetooth/Wi-Fi while disabling internet. Nearby needs radios; airplane mode alone may disable them. Enable any required precise location permission/location services on Android 8–12L.
4. Open Nearby, tap **Discover and advertise** on both. Confirm matching digits on both. A peer is accepted only after its enrolled signing key passes the nonce proof.
5. Tap **Send small Nearby spike payload**. The other phone must show `Nearby small payload received` with the authorized peer ID. Record both screens. One phone sending to zero peers is NOT success.
6. Deliberately reject pairing and attempt a peer absent from the manifest; ensure no report is received. Reimport the trusted manifest if needed.

## A → B → C store-and-forward (three physical phones)

1. Provision all three exported identities in one manifest. No weights needed on B or C. All join the same demo mission.
2. A without internet creates `mesh-school-01` at River School. Run real Gemma inference and save its actual assessment/follow-up.
3. Connect A and B in foreground. Record A's event IDs and B's `Durably stored` log / evidence. Verify B sees original origin A and a receipt referencing A's source IDs.
4. Stop A's Nearby or turn it off. Force-stop B with `adb shell am force-stop org.rescuemesh`, reopen B, and verify those same bytes/IDs remain. Do not clear app storage or reinstall with uninstall.
5. B connects to C with A still off. C must receive missing original events and signed receipt events. Record identical original A IDs, independent of sequence gaps; repeat exchange to check no duplicate source records.
6. Drop a connection during transfer; reopen foreground exchange. Retry must converge and log failures honestly.
7. After GCP deployment, give C its own issued sync token and HTTPS backend URL. Enable internet on C, use Gateway → Upload durable events. Cloud ACK must mark event IDs synced; repeat upload must not duplicate reports.
8. Open the deployed dashboard: verify original sources, citations, draft assessments, receipts and freshness.
9. Add a contradictory report about a previously reported clear approach being blocked. Source events remain visible. Authenticated coordinator requests actual Gemini reassessment, verifies contradiction citations and revised response, then confirms prerequisites and approves.
10. Add new evidence after a proposal and attempt to approve the old revision: expect HTTP 409. Reassess, review and approve the new one. Another incident cannot reserve an already assigned resource.

## Instrumentation and emulator setup

Room restart instrumentation is compiled and supplied, but not yet executed. It is useful on an emulator or phone, and distinct from physical mesh proof:

```bash
./android/gradlew -p android :app:connectedDebugAndroidTest
```

For an emulator install a Google Play system image through Android Studio, create an API 35 virtual device, boot it and verify `adb devices`. The app's local report/storage UI can run there; current LiteRT-LM packaged native ABI must match. Do not claim emulator inference proves the physical phone latency or radio relay.

Record results in a dated hardware report, with screenshots under ignored `artifacts/device-test/`. Use the provided capture script after actual inference. Do not commit credentials, weights or unintended device telemetry.
