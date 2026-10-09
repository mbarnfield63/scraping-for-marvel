# ADR-0013: Self-hosted MinerU OCR on Hypatia, cloud as fallback

Supersedes [ADR-0001](0001-cloud-ocr-over-self-hosted.md).

## Context

ADR-0001 chose the MinerU cloud API because the open MinerU-2.5 1.2B model, self-hosted, corrupted about 8% of values on hard scans. In October 2026 the cloud API became unreliable. MinerU 4.0.10 ships a newer VLM (`MinerU2.5-Pro-2605-1.2B`). ADR-0001 asked for new evidence of parity before revisiting, so the new model was gated against the cloud before switching.

## Evidence (2026-10-08)

Self-hosted MinerU 4.0.10, `standard` tier, vLLM, on a Hypatia L40S, compared against the cloud `vlm` output for the same PDFs. Coverage means verified values (crop-checked, reviewer-passed extraction CSVs) found in each `full.md`'s tables, matched on the printed digits:

| Paper | Cloud | Local | Local-only failures | Cloud-only failures |
|---|---|---|---|---|
| `57LaSe` (VO, hard scan) | 1035/1136 | 1024/1136 | 11 stacked doublets concatenated into one cell (`12,31` / `095,78` became `12,31095,78`) | none |
| `64Pl` (N2O, 1964 scan) | 2035/2444 | 2042/2444 | 21 dropped cells (row shifts left) | 28 dropped cells, plus one table caught in a repetition loop (`10.80` ×106, `colspan="101"`) |
| `96PlMaHo_CS2` (clean) | identical values | identical values | none | none |
| `19LiHuWa` (N2O, 2019) | same digits | same digits | local keeps the printed digit grouping (`0.415 654 098`) | none |

The shared misses (about 9% and 17%) are an artefact of the matching method and apply equally to both outputs. The `advanced` tier was never better than `standard`. The original ADR-0001 ground-truth set no longer exists, so this is two hard scans, not a full re-validation.

## Decision

Make self-hosted OCR on Hypatia (`hpc/ocr/run`) the primary Step 2 and keep `scripts/mineru_cloud.py` as the fallback. Use the `standard` tier.

## Consequences

- Neither OCR is clean on hard scans. The extractor's crop validation is the safeguard for both. Its brief now names the failure modes: two decimal separators in one cell (local doublet merge), one value repeated many times (cloud loop), space-split digit groups, and short rows (dropped cells, both).
- `hpc/ocr/run` prints a `CHECK` line for every cell with two decimal separators.
- Setup details tied to Hypatia: cu129 torch/vllm/torchaudio/torchcodec (driver 535 supports CUDA ≤ 12.2, so minor-version compatibility is used), the non-slim `uv-bookworm.sif` image (Triton needs gcc), `VLLM_USE_FLASHINFER_SAMPLER=0` (no nvcc), and choosing the freest GPU at job start (Hypatia's gres assigns every 1-GPU job device 0 and does not isolate GPUs).
- `full.md` keeps HTML `<table>` for every table through a monkeypatch of a private MinerU 4.0.10 renderer function. Recheck it when MinerU is upgraded.
- Revisit if a later gate shows the local error rate falling behind the cloud's.
