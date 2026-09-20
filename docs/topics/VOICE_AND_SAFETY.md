# Voice, State Journal and Sherpa test protocol

## Historical baseline

Earlier EAON work used Porcupine wake word, Whisper on CPU, Piper TTS and local
Ollama. Reported files included `audio_loop.py`, `stt.py`, `tts.py`,
`tts_neural.py`, `tts_piper.py` and `wakeword.py`. These exact files were not recovered.
Wake/STT execution was evidenced in a report with an empty transcript; later voice
output/telemetry success was reported but not reproduced here.

The proposed microphone fix was phase ownership: stop the wake stream before
recording a command, then process/speak, wait briefly, and resume wake listening.
The previous 0.5-second delay was a proposed implementation detail, not measured tuning.

## Recovered C3/A1/B2 harness

`benchmarks/voice/` contains the manifest runner, WER and wake metrics, stage
percentiles, `Transition`/`Observation` State Journal, chain verifier and two tests.
It has a mock adapter and a command adapter expecting JSON on stdout.

The mock returns the reference transcript, expected wake result and synthetic
timings. Six manifest samples produce 42 journal events. This validates plumbing,
not wake accuracy or speech recognition. The command adapter executes a supplied
local program without a shell; it is not the later safety interlock or a sandbox.

The original README's `sherpa-onnx-1.13.6` JSON is a historical example. The later
agreed test target is **v1.13.8**. Record exact executable/model hashes before testing;
no version is claimed installed or benchmarked in this repository.

## Accepted target path

Wake/VAD → Sherpa STT → privacy gate → CAUC shadow → deterministic router →
permitted executor → State Journal. CAUC observes; it cannot authorize, reroute
or execute an action during the experiment.

## September 21 preparation plan

Historical planned sync: **Monday 2026-09-21, 09:00–09:30 Europe/Berlin**. This file
records the plan; it does not schedule a reminder or claim the session occurred.

Discussed scripts: `capture_audio`, `run_pipeline`, `inject_scenarios`,
`safety_interlock`, `summarize_results`. Their full implementations are missing.

The staged run was a 60-minute smoke/dry-run, followed by 8-hour and 48-hour stages
only after the earlier gates pass. The later smoke corpus was 30 RO/DE/EN commands.
The earlier C3 full benchmark protocol was larger: at least 50 positive commands
and 100 negative samples per language, near/far distances, quiet/household noise,
multiple speakers and similar-sounding negative wake words. These are different
test stages; the smoke corpus does not replace the larger evaluation.

Noise is recorded as **dBFS**, with microphone/gain/placement documented. Do not label
uncalibrated software levels as laboratory dBA sound-pressure measurements.

## Required startup interlock

All conditions must be true together:

| Condition | Required state |
|---|---|
| Run mode | `dry_run=true` |
| Executor | `MockToolExecutor` only |
| Real tools | Real registry disconnected |
| Network | Outbound network blocked by the test environment |
| Journal | Writable and available |
| Emergency stop | Armed and exercised |

Any false/unknown condition blocks the run. A dry-run flag alone is insufficient.
The existing C3 command adapter and INTEL mode flags do not implement these conditions.

## Acceptance/reporting

Hard safety requirements: **zero real tool executions, zero unauthorized actions,
zero mock executions without an authorized wake condition**. Also record blocked
attempts, journal failures and emergency-stop behavior. A clean physical-action
count cannot hide an unauthorized mock path.

Initial C3 quality targets, to calibrate on real data: quiet WER ≤12%, false reject
≤5%, false accept ≤0.2/hour, p95 wake-to-first-audio ≤1.2 seconds. These are proposed
targets, not achieved results. The harness's per-sample false-accept ratio is not
false accepts per hour; that needs measured negative-audio duration. Adapter stage
timings are not a measured end-to-end first-audio latency without actual instrumentation.

The final report should include version/config/corpus hashes, RO/DE/EN results,
noise/geometry, scenarios, false rates and denominators, blocked/unauthorized/real
calls, p50/p95 latency, resource use, journal integrity and an evidence-based verdict.
Raw audio stays out of the journal; benchmark transcripts need explicit retention.

## Pending work

Implement the real wrapper and fail-closed interlock, validate no-wake/false-wake/
missing-journal/emergency-stop scenarios, then run on the intended hardware. Mock
success is not authorization to connect physical tools.
