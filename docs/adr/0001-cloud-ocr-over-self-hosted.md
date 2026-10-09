# ADR-0001: MinerU cloud OCR over self-hosted

**Status:** Superseded by [ADR-0013](0013-self-hosted-ocr-on-hypatia.md) (2026-10-08).

## Context

The pipeline needs OCR on scanned spectroscopy papers with dense numeric tables, where a single misread digit silently corrupts the MARVEL spectroscopic network — there is no downstream physical check that would catch it.

A self-hosted OCR pipeline was built first (Gemini pre-screener, HPC OCR models, SLURM scripts — retired, see `archive/ocr-pipeline-v1/`). The open MinerU-2.5 1.2B model, run locally/on HPC, silently corrupted ~8% of values on hard scanned papers when validated cell-by-cell against ground truth: digit misreads (e.g. `2186→2189`), high-J column drops, decimal-comma confusion.

## Decision

Use the MinerU **cloud** API with the `vlm` model (OCR on) instead of self-hosting. The cloud `vlm` model's output was validated cell-by-cell against ground truth and did not show the local model's corruption rate. Data egress is not a concern — these are published papers.

## Consequences

- Requires an API token and network access at OCR time; free tier caps at 2000 pages/day at top priority.
- The entire self-hosted pipeline is retired but kept in `archive/ocr-pipeline-v1/` rather than deleted, in case a future local-model version closes the accuracy gap.
- Do not re-litigate self-hosting without new evidence that the local model's error rate has closed to parity with the cloud `vlm` model.
