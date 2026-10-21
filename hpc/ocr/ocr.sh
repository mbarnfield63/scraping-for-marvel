#!/bin/bash
# Self-hosted MinerU OCR job. Submitted by hpc/ocr/run, not by hand: the job name is
# ocr-<batch-ts>, and the batch lives in ~/data/MARVEL_scraping/ocr/<batch-ts>/{in/,tier}.
# L40S fallback: hpc/ocr/run ... --gres=gpu:1 --nodelist=compute-gpu-0-5

#SBATCH -p GPU
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=marco.barnfield.24@ucl.ac.uk

set -euo pipefail

batch=$HOME/data/MARVEL_scraping/ocr/${SLURM_JOB_NAME#ocr-}
# vLLM's Triton kernels compile a C helper at startup; the slim image has no gcc.
export CTR_IMAGE=$HOME/containers/uv-bookworm.sif
# Models download once into ~/data and are reused by every later job.
export MINERU_HOME=$HOME/data/MARVEL_scraping/mineru
export HF_HOME=$MINERU_HOME/hf
export MINERU_MODEL_SMALL_BACKEND=torch
export MINERU_MODEL_VLM_ENGINE=vllm
# FlashInfer's sampler JIT-compiles with nvcc, which the container lacks; use vLLM's PyTorch sampler.
export VLLM_USE_FLASHINFER_SAMPLER=0
# Node /tmp sits on a small root disk (compute-gpu-0-5: 4.8 GB free); page renders filled it (job 1391096).
export TMPDIR=$batch/tmp
mkdir -p "$TMPDIR"

# Hypatia's gres has no device mapping: every 1-GPU job gets CUDA_VISIBLE_DEVICES=0 and sees
# all GPUs, which other jobs share. Take the one with the most free memory (MinerU's vLLM needs ~6 GB).
# ponytail: races with other jobs starting at the same moment; fine at our ~6 GB footprint.
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | sort -t, -k2 -nr | head -1 | cut -d, -f1)
nvidia-smi -i "$CUDA_VISIBLE_DEVICES" --query-gpu=index,name,memory.free,driver_version --format=csv,noheader
ctr uv run --frozen mineru-kit models download --tier standard
ctr uv run --frozen python ocr.py "$batch/in" "$batch/out" --tier "$(cat "$batch/tier")"
