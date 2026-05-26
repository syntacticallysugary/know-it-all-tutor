# Definition Cleanup Agent — AI/ML Domain

## Task

Rewrite every `definition` field in the AI/ML domain upload file so that
the term being defined does not appear anywhere in the definition sentence.
The definition is used as the "given" in a quiz — the student must supply
the term — so the definition must not name or allude to the term by name.

## Files to Process

1. `/home/jimbob/Dev/AWS_Dev/data/ai_ml_upload.json`

## Output Files

Write the corrected version to a new file with `-fix` appended before the
extension:

1. `/home/jimbob/Dev/AWS_Dev/data/ai_ml_upload-fix.json`

## Transformation Rule

**Before:** The definition names the term anywhere in the text.
**After:** The definition describes the concept without naming it.

### Examples

| Term | Before | After |
|------|--------|-------|
| `Neural Network` | `A neural network is a computational model composed of layers of interconnected nodes that transform input data into predictions.` | `A computational model composed of layers of interconnected nodes that transform input data into predictions.` |
| `Gradient Descent` | `Gradient descent is an iterative optimization algorithm that minimizes a loss function by updating parameters in the direction of the negative gradient.` | `An iterative optimization algorithm that minimizes a loss function by updating parameters in the direction of the negative gradient.` |
| `Dropout` | `Dropout is a regularization technique that randomly sets a fraction of neuron activations to zero during training.` | `A regularization technique that randomly sets a fraction of neuron activations to zero during training.` |
| `RAG` | `RAG (Retrieval-Augmented Generation) combines a language model with an external knowledge retrieval step to ground responses in factual sources.` | `Combines a language model with an external knowledge retrieval step to ground responses in factual sources.` |

### Pattern variants to handle

- `"X is a ..."` → `"A ..."`
- `"X (full name) is ..."` → keep predicate, capitalize
- `"The X is ..."` → keep predicate, capitalize
- `"X does/computes/combines/..."` → keep verb phrase, capitalize
- `"An X is ..."` → reopen with the predicate noun phrase
- Term appears mid-sentence (e.g., in a contrast: "Unlike X, ...") → rephrase
- Definitions that contain **no** form of the term → **leave unchanged**
- When the term includes a parenthetical acronym (e.g., `Generative Adversarial
  Network (GAN)`), treat **both** the full name and the acronym alone as the
  term. If the definition opens with `"A GAN ..."` or uses `GANs` anywhere,
  that counts as a match — rewrite it.

### Grammatical constraints

- Every output sentence must be grammatically complete and natural.
- Do **not** simply delete words mechanically — rewrite the sentence if needed
  to maintain correctness.
- Apply the rewrite rule to **every sentence** in the definition independently.
  Do not stop after fixing the first sentence — scan all sentences and rewrite
  any that contain the term in any form.
- Preserve all sentences after the first sentence verbatim unless they also
  contain the term name.
- Do not change `term`, `category`, `module`, `difficulty`, `code_example`,
  or any other field — only `definition`.
- If the term is singular and the definition contains the plural form (or
  vice versa), treat it as a match and rewrite the sentence.
- Term matching is **case-insensitive**: if the term appears anywhere in the
  definition in any capitalization form, treat it as a match and rewrite.
  Examples: term `Residual Connection` matches `residual connection`; term
  `LoRA` matches `Lora` or `LORA`; term `Dropout` matches `dropout`.

## Process

1. Read each file with the `read` tool.
2. Parse the JSON.
3. For each term object, inspect `data.definition`. If it names the term
   in any position in the sentence, rewrite it. If it does not, leave it unchanged.
4. After processing the file, write it back to disk using the
   `write` tool with `-fix` appended to the file name (create a new file).
5. Validate by re-reading the output file and confirming it parses as valid JSON.
6. Report: total terms inspected, total definitions changed.

## Quality Check

Before writing the file, review 5 randomly chosen changed definitions and
confirm each one:
- Is grammatically correct as a standalone sentence
- Does not name the term in any form (including plural, different capitalization,
  or common abbreviation)
- Preserves the original meaning
