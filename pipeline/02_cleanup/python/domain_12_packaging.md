# Definition Cleanup Agent — Python — Packaging (7 terms)

## CRITICAL INSTRUCTION — Read This First

**Do NOT write a Python script, shell script, or any other code.**
**Do NOT use the Bash tool.**
Read the JSON file with the Read tool. Edit each term's `definition` field
manually in your context. Write the result with the Write tool.
If you write a script instead, you have failed the task.

---

## Task

Rewrite every `definition` field in this domain file so that the term being
defined does not appear anywhere in the definition text.

The definition is used as the "given" in a reverse quiz — the student sees
the definition and must supply the term. A definition that names the term
gives the answer away and must be rewritten.

This file covers **Python — Packaging** — **7 terms**.

---

## Files

| Role | Path |
|------|------|
| Source (read this) | `/home/jimbob/Dev/AWS_Dev/data/python_domains/domain_12_packaging.json` |
| Output (write this) | `/home/jimbob/Dev/AWS_Dev/data/python_domains/domain_12_packaging_fix.json` |

Write the output fresh from scratch. Copy all fields exactly except `data.definition`
where rewrites are needed.

---

## JSON Structure

```json
{
  "domain_index": 12,
  "domain_name": "Python — Packaging",
  "term_count": 7,
  "terms": [
    {
      "node_type": "term",
      "data": {
        "term": "Example Term",
        "definition": "An example term is a placeholder ...",
        "difficulty": "beginner",
        "module": "example-module",
        "category": "example",
        "code_example": "...",
        "short_reference": "..."
      },
      "metadata": { "has_examples": true }
    }
  ]
}
```

**The only field to edit is:** `terms[N].data.definition`

**Leave completely untouched:**
`term`, `difficulty`, `module`, `category`, `code_example`, `short_reference`,
`node_type`, `metadata`, `domain_index`, `domain_name`, `term_count`.

---

## ⚠️ THE MOST COMMON MISTAKES — Read This Before Anything Else

There are two equally common failures:

**Mistake 1 — Fixing only the first sentence:**
Most definitions where the term appears in sentence 1 ALSO have the term
in sentence 2, 3, or 4. You must scan every sentence in every definition.
Fixing sentence 1 while leaving the term in sentence 3 is a failed cleanup.

**Mistake 2 — Deleting when you should be substituting:**
When the term appears as the **sentence subject** (`"Canary differs..."`) or as
a **modifier before a noun** (`"canary releases"`), deleting it leaves broken grammar.
You must **replace** it with `"This"`, `"these [noun]"`, or another appropriate pronoun.
See the **"Subject or Modifier"** section below.

---

## How to Process Each Definition

### Step 1 — Write out ALL variants of the term before scanning

For each term, explicitly list every form it can appear in the definition:

| Source | Derive |
|--------|--------|
| Full name | Lowercase version: `"Multi-Head Attention"` → `"multi-head attention"` |
| Abbreviation in parentheses | `"Convolutional Neural Network (CNN)"` → also match `CNN`, `CNNs` |
| Plural / singular | `"Residual Connection"` → also match `"residual connections"` |
| AWS/Amazon prefix | `"Amazon ECS"` → also match `"ECS"`, `"ecs"` |
| All of the above | case-insensitive: `"Loss Function"` matches `"loss function"`, `"LOSS FUNCTION"` |

**Write out the lowercase form explicitly.** Definitions naturally use lowercase
mid-sentence. `"Residual Connection"` → definitions will say `"residual connections
are standard in transformers"` — this is still a match and must be rewritten.

### Step 2 — TWO-PASS scan of the definition

**Pass 1 — sentence by sentence:**

For each sentence in the definition, in order:
- Does this sentence contain the term in any form (any case, any variant)? → **Yes: rewrite it. No: copy it unchanged.**

**Pass 2 — full re-read:**

After Pass 1, read the entire output definition from beginning to end.
Search for every variant (including abbreviations and lowercase forms).
If any instance remains anywhere — even in sentence 3 or 4 — fix it now.

### Multi-sentence example (term appears in sentences 1 AND 3)

**Term:** `Residual Connection`
**Variants:** `residual connection`, `residual connections` (all case-insensitive)

**Source (3 sentences):**
> "A residual connection (skip connection) adds the input of a layer directly to
> its output. This creates a shortcut path that allows gradients to flow more easily
> during backpropagation. Residual connections are standard in transformers, where
> each sub-layer output is added to its input before normalization."

**Sentence-by-sentence scan:**
- Sentence 1: contains `residual connection` → **REWRITE**
  → `"A shortcut path (also called a skip connection) that adds a layer's input directly to its output."`
- Sentence 2: no term → **COPY UNCHANGED**
- Sentence 3: contains `Residual connections` → **REWRITE**
  → `"Standard in transformers, where each sub-layer output is added to its input before normalization."`

**Output:**
> "A shortcut path (also called a skip connection) that adds a layer's input directly
> to its output. This creates a shortcut path that allows gradients to flow more easily
> during backpropagation. Standard in transformers, where each sub-layer output is
> added to its input before normalization."

---

### When the Term Is a Subject or Modifier in a Later Sentence

After Pass 1 fixes the opening, the most common **residual** is the term appearing
in a later sentence as the **sentence subject** or as a **modifier before a noun**.
Deleting it in these positions produces broken grammar — you must **substitute** it.

| Position | Before | Correct After |
|----------|--------|---------------|
| Sentence subject | `"Canary Deployment differs from blue/green..."` | `"This differs from blue/green..."` |
| Modifier + plural noun | `"...supports canary releases natively."` | `"...supports these releases natively."` |
| Modifier + singular noun | `"The canary version receives 10%..."` | `"The new version receives 10%..."` |
| Possessive | `"Canary deployment's rollback triggers..."` | `"Its rollback triggers..."` |

**Rule of thumb:**
- Term as sentence subject → `"This"` or `"It"`
- Term modifying a **plural** noun → `"these [noun]"` or `"such [noun]"`
- Term modifying a **singular** noun → `"this [noun]"` or `"the [noun]"`
- Term used alone as object → `"this approach"`, `"this pattern"`, `"this mechanism"`

**Full example — Canary Deployment (two residuals in one definition):**

**Term:** `Canary Deployment`
**Variants:** `canary deployment`, `canary deployments`, `canary release`, `canary releases`

**Source:**
> "Routes a small percentage of production traffic to a new version while the majority
> continues to the current version. In AWS, CodeDeploy supports canary deployments for
> Lambda and ECS with automatic alarm-based rollback; API Gateway supports canary
> releases natively. Canary differs from blue/green in that both versions serve
> production traffic simultaneously rather than a full cutover."

**Sentence-by-sentence scan:**
- Sentence 1: no term → **COPY UNCHANGED**
- Sentence 2: `canary deployments` (modifier+noun), `canary releases` (modifier+noun) → **REWRITE**
  → `"In AWS, CodeDeploy supports this pattern for Lambda and ECS with automatic alarm-based rollback; API Gateway supports these releases natively."`
- Sentence 3: `Canary` is the sentence subject → **REWRITE**
  → `"This differs from blue/green in that both versions serve production traffic simultaneously rather than a full cutover."`

**Output:**
> "Routes a small percentage of production traffic to a new version while the majority
> continues to the current version. In AWS, CodeDeploy supports this pattern for Lambda
> and ECS with automatic alarm-based rollback; API Gateway supports these releases
> natively. This differs from blue/green in that both versions serve production traffic
> simultaneously rather than a full cutover."

---

### Common opening-sentence patterns

| Pattern | Before | After |
|---------|--------|-------|
| `"A X is ..."` | `"A loss function measures..."` | `"Measures..."` or `"The metric that..."` |
| `"X is a ..."` | `"Backpropagation is the algorithm..."` | `"The algorithm for..."` |
| `"X are ..."` | `"Residual connections are shortcuts..."` | `"Shortcuts that..."` |
| `"An X is ..."` | `"An embedding layer maps..."` | `"Maps discrete tokens..."` |
| `"The X ..."` | `"The learning rate controls..."` | `"Controls the step size..."` |
| `"X (ABBREV) ..."` | `"Dropout (a regularization technique)..."` | `"A regularization technique..."` |
| `"X refers to ..."` | `"Fine-tuning refers to..."` | `"The process of..."` |
| `"AWS X / Amazon X is ..."` | `"AWS Lambda is a serverless..."` | `"A serverless compute..."` |

### Definitions that are already clean

If a definition contains **no** form of the term in ANY sentence,
**leave it exactly as-is**. Do not rephrase or improve clean definitions.

---

## Naming Rules

### Prefix and abbreviation matching

| Pattern | Also match (case-insensitive) |
|---------|-------------------------------|
| `AWS Lambda` | `Lambda` |
| `Amazon S3` | `S3`, `Simple Storage Service` |
| `Amazon ECS (Elastic Container Service)` | `ECS`, `Elastic Container Service` |
| `Convolutional Neural Network (CNN)` | `CNN`, `CNNs` |
| `Stochastic Gradient Descent (SGD)` | `SGD` |
| `LoRA (Low-Rank Adaptation)` | `LoRA`, `LORA` |
| Any `Term (ABBREV)` | both the full name AND the abbreviation |

Rules:
- Match is **case-insensitive** everywhere.
- Strip `AWS ` or `Amazon ` prefix and match the remainder.
- Match plural/singular: `"deployment"` ↔ `"deployments"`.
- If the abbreviation appears alone in a later sentence (e.g., `SGD`, `ECS`),
  it must also be removed or substituted.

**Every variant must be REMOVED or SUBSTITUTED — none is acceptable to leave.**

### ⚠️ Strip the ENTIRE term, not just a prefix

- Term: `EC2 Auto Scaling`
- ❌ Wrong: strip `"EC2 "` → leave `"Auto Scaling adjusts..."` — `Auto Scaling` is still a match.
- ✓ Correct: strip `"EC2 Auto Scaling"` entirely → `"Adjusts capacity automatically..."` ✓
- ❌ Also wrong: strip `"Stochastic "` → leave `"Gradient Descent updates..."` — still a match.

### Do NOT remove related terms that merely share words

- Term `Gradient Descent`: `"compute the gradient"` uses `gradient` as a math concept — only remove the full phrase `gradient descent`.
- Term `EC2 Auto Scaling`: `"EC2 instances"` refers to a different service — do not remove `EC2`.
- Term `Neural Network`: a definition may legitimately mention `convolutional neural network` as an example sub-type — do not remove it.
- Term `Attention Mechanism`: occurrences of `multi-head attention` refer to a sub-concept — do not remove.

---

## Grammatical Requirements

- Every output definition must be grammatically complete and natural English.
- Sentences must start with a capital letter.
- Do not produce sentence fragments.
- Preserve all technical detail, specifics, formulas, numbers, and service names
  that are NOT the term being defined.

---

## Process — Follow These Steps Exactly

1. **Read** `/home/jimbob/Dev/AWS_Dev/data/python_domains/domain_12_packaging.json` using the Read tool.

2. **Work through all 7 terms** in order. For each term:
   a. Note `data.term`. Write out: full lowercase form, abbreviation (if any), plural forms.
   b. Read `data.definition`.
   c. **Pass 1:** Scan each sentence in order. Rewrite sentences that contain
      the term in any form; copy unchanged sentences that do not.
      When the term is a subject or modifier, substitute — do not just delete.
   d. **Pass 2:** Re-read the complete rewritten definition. If the term appears
      anywhere — in any form, any case — fix it now.
   e. If no occurrences found: leave `data.definition` exactly as-is.

3. **Keep a running count** of how many definitions you changed and how many
   you left unchanged.

4. **Do not modify any other field.** Only `data.definition` changes.

5. **Write** the complete modified JSON to
   `/home/jimbob/Dev/AWS_Dev/data/python_domains/domain_12_packaging_fix.json` using the Write tool.
   The output must be valid JSON. Write the entire file in one Write call.
   Copy `domain_index`, `domain_name`, and `term_count` through unchanged.

6. **Verify** by re-reading the output file with the Read tool and confirming
   it parses correctly (no truncation, no JSON syntax errors).

7. **Report**: state how many terms you inspected, how many definitions you
   changed, and how many you left unchanged. The total must equal 7.

---

## Quality Check — Do This Before Writing

Pick the **first 5 definitions you changed** and for each one confirm:

- [ ] Search the ENTIRE output definition — every sentence — for the term in
      all its forms (full name lowercase, abbreviation, plural). It must not appear anywhere.
- [ ] Where the term appeared as a subject or modifier, it was substituted
      (not deleted), and the result reads as natural English.
- [ ] The output definition is grammatically complete and natural English.
- [ ] The technical content is preserved — no facts were dropped or altered.
- [ ] No other field was changed.

If any check fails, fix that definition before writing the file.
