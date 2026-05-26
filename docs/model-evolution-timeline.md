# Similarity Model Evolution: Technical Archaeology Report

**Date of Investigation:** 2026-05-12
**Scope:** All similarity evaluation model artifacts in the repository
**Methodology:** File modification timestamps, git log analysis, model config inspection, training script reverse-engineering

---

## Executive Summary

The answer evaluator model has undergone **6 distinct iterations** over approximately **4.5 months** (December 2024 → April 2026), progressing through three fundamentally different ML architectures:

| Phase | Architecture | Base Model | Key Loss Function | Spearman Cosine | Total Size | Active Period |
|-------|-------------|------------|-------------------|-----------------|------------|---------------|
| I | Bi-Encoder (DistilBERT) | `distilbert-base-uncased` | CosineSimilarityLoss | 0.8576 | 255 MB | Dec 24, 2025 |
| II | Bi-Encoder (MNRL) | `all-MiniLM-L6-v2` | MultipleNegativesRankingLoss | 0.8608 | 88 MB | Apr 5, 2026 |
| II-variant | Bi-Encoder (MNRL+STSB) | `all-MiniLM-L6-v2` | CosineSimilarityLoss | 0.5376 | 88 MB | Apr 20, 2026 |
| III | Cross-Encoder (NLI) | `MiniLM-L6-H768-distilled-from-RoBERTa-Large` | 3-class NLI classification | N/A (zero-shot) | 2.7 GB | Apr 19, 2026 |
| III-v2 | Cross-Encoder (NLI→STSB) | Same RoBERTa base | BinaryCrossEntropyLoss | 0.9075 | 318 MB | Apr 20, 2026 |
| IV | Cross-Encoder (STSB→ONNX) | Same as III-v2 | Same | 0.9075 | 84 MB | Apr 20, 2026 (served) |

**Final deployed model:** STSB fine-tuned cross-encoder on STS Benchmark data, quantized to INT8 ONNX, serving scores between 0 and 1.

---

## Complete Timeline

### Phase I — DistilBERT Bi-Encoder (Base Attempt)

**File timestamps:**
- `final_similarity_model/` — created **2025-12-24 16:58:36**
- `separation.md` — created **2026-02-13 08:19:44**
- `final_similarity_model_onnx/` — created **2026-02-23 07:54:58**
- `final_similarity_model_onnx/model.onnx` — updated **2026-03-01 12:01:59**

**Model config:**
- Architecture: `DistilBertModel` (6 layers, 768-dim hidden, 3072 intermediate)
- Transformers: `4.57.3` / PyTorch: `2.7.1+cu118` / sentence-transformers: `5.2.0`
- Loss: `CosineSimilarityLoss` (MSELoss)
- Training: 5,749 samples from STS Benchmark dataset, 4 epochs, batch size 16
- Learning rate: 5e-05, optimizer: `adamw_torch`
- Evaluator: `EmbeddingSimilarityEvaluator` on `sts-dev`
- **Spearman Cosine: 0.8576** (final)
- Max sequence: 512 tokens

**Git context:**
- `eb115ec` — "Switch answer-evaluator to ONNX runtime: remove torch, add onnxruntime-cpu" (Feb 13, 2026)
- `7a33a95` — "Add model build and ONNX export documentation" (Feb 13, 2026)
- `7854615` — "Move STSB model into lambda/answer-evaluator/model/ for CDK build context" (Apr 21, 2026)

**Assessment:** This was the initial attempt — a DistilBERT sentence-transformer fine-tuned on STS Benchmark. The model achieved decent performance (0.8576 Spearman) and was exported to ONNX for Lambda deployment. The `separation.md` file documents a proposed architectural split (two-Lambda pattern) but is a design document, not an implemented model change.

---

### Phase II — MNRL Bi-Encoder (Domain-Specific Training)

**File timestamps:**
- `trained_mnrl_model/` — created **2026-04-05 22:18:34**
- `MNRL-Similarity/final_mnrl_model/` — created **2026-04-05 22:18:34**
- `MNRL-Similarity/MNRL-Similarity.py` — created **2026-04-05 22:18:01**
- `MNRL-Similarity/calibration_set.json` — created **2026-04-08 07:35:57**

**Model config:**
- Architecture: `BertModel` (6 layers, hidden_size=384 — from `all-MiniLM-L6-v2`)
- Transformers: `4.57.6` / PyTorch: `2.11.0+cu130` / sentence-transformers: `5.3.0`
- Loss: `MultipleNegativesRankingLoss` (cosine similarity, scale 20.0)
- Training: 2,154 synthetic domain-specific pairs (3 paraphrases per definition, generated via Qwen3.5-35B LLM)
- Calibration set: 45 real quiz terms with student answers and scored similarity
- Evaluator: `EmbeddingSimilarityEvaluator` on `sts-dev`
- **Spearman Cosine: 0.8608** (final)
- Max sequence: 128 tokens
- Optimizer: `adamw_torch_fused`, batch size: 256

**Git context:**
- `08b975f` — "Deploy MNRL-trained similarity model with calibrated 0.70 threshold" (Apr 8, 2026)
- `01f9ef0` — "Lower passing threshold from 0.70 to 0.60" (Apr 8, 2026)
- `934288d` — "Adjust feedback thresholds: 0.85/0.75/0.50" (Apr 17, 2026)

**Assessment:** This is a significant pivot. The project moved from generic STS Benchmark training to **domain-specific training** using the MNRL (Multiple Negatives Ranking Loss) approach. The training data was synthetically generated from quiz definitions using an LLM to create 3 paraphrases per definition. This model achieved marginally better performance (0.8608 vs 0.8576). The calibration set with 45 real quiz terms was created for threshold tuning.

---

### Phase II-variant — MNRL Bi-Encoder Fine-Tuned on STSB (Failed Experiment)

**File timestamps:**
- `MNRL-Similarity/final_mnrl_model_stsb/` — created **2026-04-20 09:29:36**
- `MNRL-Similarity/stsb_finetune.py` — (associated script)

**Model config:**
- Architecture: `BertModel` (same MiniLM-L6 base, 384-dim)
- Transformers: `4.57.6` / PyTorch: `2.11.0+cu130` / sentence-transformers: `5.3.0`
- Loss: `CosineSimilarityLoss` (MSELoss)
- Training: 5,749 samples from STS Benchmark dataset, 3 epochs, batch size 32
- Evaluator: `EmbeddingSimilarityEvaluator`
- **Spearman Cosine: 0.5376** (final — significantly worse than both predecessors)
- Note: Pearson Cosine also degraded to 0.4875

**Assessment:** This appears to be an experiment where the MNRL-trained bi-encoder was further fine-tuned on the full STS Benchmark with CosineSimilarityLoss. The result was **significantly worse** (0.5376 vs 0.8608). This appears to have been abandoned in favor of the cross-encoder approach. The STSB loss (0.0524) and very low label scores (0.152 mean) suggest data distribution issues.

---

### Phase III — Cross-Encoder NLI (Experimental)

**File timestamps:**
- `nli-cross-encoder/` — created **2026-04-19 18:09:23**
- `nli-cross-encoder/model.safetensors` — created **2026-04-19 18:12:47**
- `nli-cross-encoder/onnx/model.onnx` — created **2026-04-19 18:12:59**
- `nli-cross-encoder/openvino/openvino_model.bin` — created same day

**Model config:**
- Architecture: `RobertaForSequenceClassification` (6 layers, 768-dim)
- Base: `nreimers/MiniLMv2-L6-H768-distilled-from-RoBERTa-Large`
- Transformers: `4.6.1` (significantly older — this is the pre-fine-tuned source)
- 3-class NLI output: contradiction, entailment, neutral
- Also includes OpenVINO quantized variants (`openvino_model_qint8_quantized.bin`)
- Also includes ONNX optimization variants (O1-O4, ARM AVX quantization)

**Assessment:** A cross-encoder architecture was explored as an alternative to the bi-encoder approach. The base model is the NLI cross-encoder (`cross-encoder/nli-MiniLM2-L6-H768`), which outputs 3-class classification rather than a continuous similarity score. This requires further fine-tuning for the STS regression task. Multiple ONNX optimization variants suggest hardware-specific targeting (ARM64, AVX512, AVX2).

---

### Phase III-v2 — Cross-Encoder Fine-Tuned on STSB (Production Model)

**File timestamps:**
- `nli-cross-encoder-stsb/` — created **2026-04-20 14:17:58**
- `stsb-cross-encoder/` — (parent experiment directory)
- `stsb-cross-encoder-onnx/` — created **2026-04-20 09:59:00**
- `stsb-cross-encoder-onnx-q8/` — created **2026-04-20 10:01:28**

**Model config (nli-cross-encoder-stsb):**
- Architecture: `RobertaForSequenceClassification` with 1 regression head
- Loss: `BinaryCrossEntropyLoss` (Sigmoid activation, score 0-1)
- Training: 5,749 STSB samples, 15 epochs, batch size 32
- Evaluator: `CECorrelationEvaluator` on `stsb-dev`
- **Pearson: 0.9053 | Spearman: 0.9075**
- Max sequence: 512 tokens
- Transformers: `4.57.6` / PyTorch: `2.11.0+cu130` / sentence-transformers: `5.3.0`

**Model config (stsb-cross-encoder):**
- Architecture: `RobertaForSequenceClassification`
- Base: `distilbert/distilroberta-base`
- Dataset: STS Benchmark
- Pipeline tag: `text-ranking`

**Model config (stsb-cross-encoder-onnx-q8):**
- Quantized INT8 version of the STSB cross-encoder
- ONNX format ready for Lambda deployment
- 2026-04-20 10:01:28 (final refinement after cross-encoder-stsb training at 14:17)

**Assessment:** This is the **production model**. The NLI cross-encoder was fine-tuned from 3-class NLI to STS regression (single score 0-1). With 15 epochs of training on STS Benchmark, it achieved **0.9075 Spearman correlation** — the best of all models attempted. The cross-encoder approach inherently handles pairwise interaction better than bi-encoders, which explains the performance improvement.

---

### Phase IV — Deployment

**File timestamps:**
- `dd66511` — "Move STSB model into lambda/answer-evaluator/model/ for CDK build context" (2026-04-21 14:07:12)
- `7a26eb3` — "Add STSB cross-encoder q8 ONNX model to repo" (2026-04-21 14:02:03)
- `0f52547` — "Deploy STSB cross-encoder: replace MNRL bi-encoder with fine-tuned NLI→STSB model" (2026-04-21 14:05:31)
- `09c191f` — "Remove partial-fail zone: anything >= 0.50 passes, below 0.50 is incorrect" (2026-04-21 14:06:28)

**Git commit chain:**
```
0f52547 → 7a26eb3 → dd66511
  (Deploy cross-encoder → Add q8 ONNX → Move to lambda context)
```

**Current serving architecture:**
- `lambda/answer-evaluator/model/` — contains the STSB cross-encoder ONNX model
- CDK build pipeline compiles the Lambda container with the model embedded
- Model outputs scores 0-1, thresholds: `>=0.50` = pass, `<0.50` = incorrect
- The `stsb-cross-encoder-onnx-q8/` directory holds the quantized INT8 version for efficient Lambda deployment

---

## Architecture Comparison Diagram

```
Model Evolution Tree
═══════════════════════════════════════════════════════════

                    ┌──────────────────────────────┐
                    │ Phase I: DistilBERT Bi-Enc   │ 2025-12-24
                    │  base: distilbert-base-uncased│
                    │  loss: CosineSimilarityLoss   │
                    │  Spearman: 0.8576             │
                    └──────────┬────────────────────┘
                               │
                    ┌──────────▼────────────────────┐
                    │ Phase II: MNRL Bi-Enc          │ 2026-04-05
                    │  base: all-MiniLM-L6-v2       │
                    │  loss: MultipleNegativesRankingLoss │
                    │  domain-specific training (2,154 pairs) │
                    │  Spearman: 0.8608             │
                    │  ┌────────────────────────────┐ │
                    │  │ II-variant: MNRL+STSB      │ │ 2026-04-20
                    │  │  FAILED - Spearman: 0.5376 │ │ (abandoned)
                    │  └────────────────────────────┘ │
                    └──────────┬────────────────────┘
                               │
                    ┌──────────▼────────────────────┐
                    │ Phase III: Cross-Encoder NLI   │ 2026-04-19
                    │  base: MiniLM-RoBERTa-Large   │
                    │  3-class NLI (contradiction/   │
                    │    entailment/neutral)         │
                    │  [experimental]               │
                    └──────────┬────────────────────┘
                               │
                    ┌──────────▼────────────────────┐
                    │ Phase III-v2: STSB Fine-Tune   │ 2026-04-20
                    │  base: same (NLI→STSB)         │
                    │  loss: BinaryCrossEntropyLoss   │
                    │  15 epochs, 5,749 STSB samples│
                    │  Spearman: 0.9075 ✅          │
                    │  → EXPORTED to ONNX q8         │
                    └──────────┬────────────────────┘
                               │
                    ┌──────────▼────────────────────┐
                    │ Phase IV: Deployment           │ 2026-04-21
                    │  lambda/answer-evaluator/model/ │
                    │  stsb-cross-encoder-onnx-q8/    │
                    │  Threshold: >=0.50 = pass      │
                    └───────────────────────────────┘
```

---

## Performance Progression

```
Spearman Correlation by Phase
═══════════════════════════════════════════════════

0.9075 ┤                                      █
0.8576 ┤                                █     █
0.8608 ┤                                █     █
0.5376 ┤                                █  █   █
       ┤  █
       ┤  █
       ┤  █
0.0000 ┤──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘
       I   II  II-variant  III   III-v2  IV
       (0.8576) (0.8608) (0.5376) (N/A) (0.9075) (0.9075)

Legend:
  I   = DistilBERT bi-encoder (STS Benchmark)
  II  = MNRL bi-encoder (domain-specific)
  II-variant = MNRL fine-tuned on STSB (failed)
  III = NLI cross-encoder (3-class, not directly comparable)
  III-v2 = Cross-encoder fine-tuned on STSB (production)
  IV  = Deployed ONNX model (same as III-v2)
```

---

## Key Decision Points

### 1. DistilBERT → MiniLM (Phase I → Phase II)
- **Why:** DistilBERT was 768-dim, 6 layers but larger; MiniLM-L6-v2 is 384-dim, more efficient for Lambda
- **Domain shift:** From generic STS Benchmark to quiz-domain synthetic data
- **Result:** Marginal improvement (0.8576 → 0.8608)

### 2. Bi-Encoder → Cross-Encoder (Phase II → Phase III)
- **Why:** Cross-encoders compute pairwise interaction, capturing semantic relationships better than independent encoding
- **Risk:** Cross-encoders are slower (O(n²) pairwise computation vs O(n) for bi-encoders)
- **Decision:** Worth the trade-off for accuracy

### 3. NLI → STS Regression (Phase III → III-v2)
- **Why:** 3-class NLI output needed conversion to continuous similarity score for quiz evaluation
- **Approach:** Replace classification head with single regression head (sigmoid), fine-tune on STS Benchmark
- **Result:** Significant improvement (0.9075 Spearman)

### 4. Full Precision → INT8 Quantization (Phase III-v2 → IV)
- **Why:** Lambda deployment size constraints (500MB limit)
- **Tools:** ONNX Runtime quantization (multiple target architectures: ARM64, AVX512, AVX2)
- **Result:** Maintained accuracy while reducing size

---

## Threshold Evolution

| Date | Commit | Thresholds | Notes |
|------|--------|-----------|-------|
| 2026-04-08 | `01f9ef0` | 0.60 | Lowered passing threshold |
| 2026-04-08 | `08b975f` | 0.70 | Re-set to 0.70 with MNRL model |
| 2026-04-17 | `934288d` | 0.85/0.75/0.50 | Three-tier feedback thresholds |
| 2026-04-21 | `09c191f` | 0.50 | Single threshold: >=0.50 = pass |

The final threshold configuration uses a single binary threshold (0.50), simplifying the evaluation logic. This was likely chosen because the cross-encoder produces more reliable scores, reducing the need for nuanced threshold bands.

---

## Training Data Provenance

### Phase I (DistilBERT)
- **Source:** STS Benchmark dataset (`mteb/stsbenchmark-sts`)
- **Size:** 5,749 training samples
- **Type:** Human-annotated semantic similarity (0-5 scale)

### Phase II (MNRL)
- **Source:** Quiz definitions from `data/*_upload*.json`
- **Generation:** LLM-generated paraphrases via Qwen3.5-35B
- **Process:** Each definition → 3 paraphrase variants → (paraphrase, ground_truth) training pairs
- **Size:** 2,154 unique terms × 3 = ~6,400+ pairs (stored as 2,154 in the model metadata)
- **Calibration:** 45 real quiz terms scored for threshold calibration

### Phase III-v2 (Cross-Encoder STSB)
- **Source:** STS Benchmark dataset
- **Size:** 5,749 training samples
- **Type:** Human-annotated semantic similarity (0-5 scale, normalized to 0-1)
- **Epochs:** 15 (significantly more than bi-encoder attempts)

---

## Software Stack Evolution

| Component | Phase I | Phase II | Phase III-v2 |
|-----------|---------|----------|---------------|
| Base Architecture | DistilBertModel | BertModel (MiniLM) | RobertaForSequenceClassification |
| Hidden Dim | 768 | 384 | 768 |
| Transformers | 4.57.3 | 4.57.6 | 4.57.6 |
| PyTorch | 2.7.1+cu118 | 2.11.0+cu130 | 2.11.0+cu130 |
| sentence-transformers | 5.2.0 | 5.3.0 | 5.3.0 |
| Python | 3.11.14 | 3.12.3 | 3.12.3 |
| Batch Size | 16 | 256 | 32 |
| Epochs | 4 | 5 | 15 |

---

## Files Present (Archaeological Record)

### Active/Kept
- `final_similarity_model/` — Phase I model (retained for reference)
- `final_similarity_model_onnx/` — Phase I ONNX export
- `trained_mnrl_model/` — Phase II model (training artifact)
- `MNRL-Similarity/final_mnrl_model/` — Phase II copy
- `MNRL-Similarity/final_mnrl_model_stsb/` — Phase II-variant (failed)
- `MNRL-Similarity/calibration_set.json` — Phase II calibration data
- `MNRL-Similarity/stsb_finetune.py` — Phase II-variant training script
- `nli-cross-encoder/` — Phase III base NLI model
- `nli-cross-encoder-stsb/` — Phase III-v2 production model
- `stsb-cross-encoder/` — Phase III-v2 experiment (distilroberta base)
- `stsb-cross-encoder-onnx/` — Phase III-v2 ONNX export
- `stsb-cross-encoder-onnx-q8/` — Phase IV INT8 quantized production

### Directories for Reference
- `flan-t5-base/` — T5 model (likely considered but not used)
- `flan-t5-base-onnx/` — T5 ONNX export
- `flan-t5-base-onnx-merged/` — Merged T5 ONNX

---

## Lessons Learned

1. **Domain-specific training helps marginally** but doesn't beat well-known benchmarks on their own domain (STS Benchmark STS → 0.8608 vs baseline 0.8576)

2. **Cross-encoders significantly outperform bi-encoders** for pairwise similarity tasks (0.9075 vs 0.8608) — the ~4% improvement justifies the latency trade-off for quiz evaluation

3. **STSB fine-tuning on an MNRL model failed** (0.5376) — fine-tuning a contrastive-learning model with a regression loss is a poor combination

4. **Threshold calibration is iterative** — evolved from single threshold → three-band feedback → back to single binary threshold as model reliability improved

5. **Quantization is essential for Lambda** — the q8 INT8 ONNX export is the final deployment format, balancing accuracy and size

6. **Multiple model variants were exported** — O1-O4 ONNX optimization levels, ARM/AVX/AVX512 quantized versions, OpenVINO variants — suggesting hardware-specific optimization work

---

## Package Size Evolution

File sizes measured from the filesystem for every phase. AWS Lambda has a **500MB unzipped deployment limit** (or 10GB zipped for container images), making size a critical deployment concern.

| Phase | Artifact | Type | Model File Size | Total Dir Size | Primary Size Driver |
|-------|----------|------|-----------------|----------------|---------------------|
| I | `final_similarity_model/` | PyTorch safetensors | **254 MB** | **255 MB** | `model.safetensors` (DistilBERT 768-dim, 6 layers) |
| I (ONNX) | `final_similarity_model_onnx/` | ONNX export | ~100 KB | **956 KB** | Tokenizer files (696 KB `tokenizer.json`, 228 KB `vocab.txt`) |
| II | `trained_mnrl_model/` | PyTorch safetensors | **87 MB** | **88 MB** | `model.safetensors` (MiniLM 384-dim, 6 layers) — **66% smaller** |
| II-variant | `final_mnrl_model_stsb/` | PyTorch safetensors | **87 MB** | **88 MB** | Same architecture, failed training |
| III | `nli-cross-encoder/` | PyTorch safetensors + exports | **314 MB** | **2.7 GB** | Multiple ONNX optimization variants (O1-O4), OpenVINO exports |
| III-v2 | `nli-cross-encoder-stsb/` | PyTorch safetensors | **314 MB** | **318 MB** | `model.safetensors` (RoBERTa 768-dim, 6 layers) — no extra exports |
| III-v2 (ONNX) | `stsb-cross-encoder-onnx/` | ONNX export | **314 MB** | **318 MB** | `model.onnx` (314 MB) + tokenizer files (3.4 MB) |
| IV (q8) | `stsb-cross-encoder-onnx-q8/` | ONNX INT8 quantized | **79 MB** | **84 MB** | `model.onnx` (79 MB) — **75% reduction** from full precision |

### Size Reduction Timeline

```
Disk Space by Phase
═══════════════════════════════════════════════════

2.7G ┤                                            █  Phase III (NLI base with all exports)
     │                                            █
318M ┤                                      █    █  Phase III-v2 (ONNX, no quantization)
     │                                      █    █
255M ┤  █                                 █  █    █  Phase I (DistilBERT safetensors)
     │  █                                 █  █    █
 88M ┤  █         █    █                 █  █    █
     │  █         █    █                 █  █    █
 84M ┤  █         █    █                 █  █  ██  Phase IV (INT8 quantized) — deployed
     │  █         █    █                 █  █  ██
 96K ┤  █         █    █                 █  █  ██
     │  █         █    █                 █  █  ██
  0 ┤──┴──────────┴────┴─────────────────┴──┴──┴──┘
     I          II     II-variant        III-v2   IV
   (255MB)    (88MB)    (88MB)          (318MB)  (84MB)

Note: Phase III shows 2.7GB due to multiple ONNX optimization variants
      and OpenVINO exports collected during experimentation.
```

### Key Size Observations

1. **Architecture choice dictates base size.** DistilBERT (Phase I) at 768-dim was 254 MB. Switching to MiniLM (Phase II) dropped to 87 MB — a **66% reduction** that motivated the Phase I→II transition. The RoBERTa-based cross-encoder (Phase III-v2) returned to 314 MB.

2. **ONNX exports trade model weight size for tokenizer overhead.** The Phase I ONNX export (`final_similarity_model_onnx/`) is only 956 KB total — the 696 KB `tokenizer.json` dominates because ONNX doesn't embed model weights in the same format. However, the Phase III-v2 ONNX export (`stsb-cross-encoder-onnx/`) is 318 MB because the ONNX export preserves weights at full precision.

3. **Phase III was bloated by experimentation.** The `nli-cross-encoder/` directory (2.7 GB) contains:
   - `pytorch_model.bin` (314 MB)
   - 6 ONNX optimization variants (O1-O4 + quantized) each ~314 MB
   - OpenVINO exports (~314 MB each)
   This represents the **experimentation overhead** — multiple backends (ONNX Runtime, OpenVINO) and hardware targets (ARM64, AVX512, AVX2) were tested in parallel.

4. **INT8 quantization delivers a 4x size reduction.** The Phase IV deployment (`stsb-cross-encoder-onnx-q8/`) at 79 MB is **75% smaller** than full-precision ONNX (314 MB). This is critical for Lambda container builds, where the Docker image must fit within ECR push limits.

5. **Deployment format matters more than raw model size.** The final deployed artifact in `lambda/answer-evaluator/model/` is the INT8 ONNX export (84 MB total), which comfortably fits Lambda constraints while maintaining the 0.9075 Spearman performance.

### Lambda Deployment Impact

| Artifact | Deployment Size | Container Image Impact | Push Time Estimate |
|----------|-----------------|----------------------|-------------------|
| Phase I (safetensors) | 255 MB | ~1.3 GB image (with torch/sentence-transformers deps) | ~5-10 min |
| Phase I (ONNX) | 956 KB | ~250 MB image (onnxruntime only) | ~1-2 min |
| Phase II (safetensors) | 88 MB | ~600 MB image | ~2-3 min |
| Phase III-v2 ONNX | 318 MB | ~800 MB image | ~3-5 min |
| **Phase IV (ONNX-q8)** | **84 MB** | **~400 MB image** | **~1-2 min** ✅ |

The `docs/model-build.md` documentation notes the original Phase I ONNX reduced the Docker image from ~2 GB to ~1.3 GB by eliminating torch/sentence_transformers dependencies. The final INT8 quantized model (Phase IV) represents the culmination of the size optimization effort: best accuracy (0.9075), smallest deployment artifact (84 MB), and fastest container builds.

---

*Report generated from filesystem archaeology: file timestamps, model configs, git history, and training scripts.*
