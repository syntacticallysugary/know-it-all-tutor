# Answer Evaluator Model

This directory holds the tokenizer config and ONNX model artifact for the
deployed answer evaluator. The `model.onnx` file is excluded from version
control due to size.

## Provenance

Base model: [`cross-encoder/nli-roberta-base`](https://huggingface.co/cross-encoder/nli-roberta-base)
from the Sentence Transformers project (Apache 2.0).

Fine-tuned on the STSB (Semantic Textual Similarity Benchmark) task to produce
a similarity score between a student answer and the reference definition.
Exported to ONNX and int8-quantized, yielding a ~79 MB artifact that runs
without PyTorch inside the Lambda container.

## Reproducing the artifact

1. Start from `cross-encoder/nli-roberta-base` on Hugging Face.
2. Fine-tune on STSB pairs (see `MNRL-Similarity/stsb_finetune.py` for the
   approach used here).
3. Export to ONNX via `optimum-cli export onnx`.
4. Quantize to int8 via `onnxruntime.quantization.quantize_dynamic`.
5. Place the resulting `model.onnx` in this directory before building the
   Docker image.

## Inference

Inference is handled by `lambda/answer-evaluator/lambda_function.py` using
`onnxruntime` with no PyTorch dependency. Scores are sigmoid-normalized and
min-max calibrated; pass threshold is 0.50.
