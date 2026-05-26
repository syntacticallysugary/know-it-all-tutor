# Definition Cleanup Agent — AWS Domain

## CRITICAL INSTRUCTION — Read This First

**Do NOT write a Python script, shell script, or any other code.**
**Do NOT use the Bash tool.**
Read the JSON file with the Read tool. Edit each term's `definition` field
manually in your context. Write the result with the Write tool.
If you write a script instead, you have failed the task.

---

## Task

Rewrite every `definition` field in the AWS domain upload file so that
the term being defined does not appear anywhere in the definition text.

The definition is used as the "given" in a reverse quiz — the student sees
the definition and must supply the term. A definition that names the term
gives the answer away and must be rewritten.

---

## Files

| Role | Path |
|------|------|
| Source (read this) | `/home/jimbob/Dev/AWS_Dev/data/aws_upload.json` |
| Output (write this) | `/home/jimbob/Dev/AWS_Dev/data/aws_upload-fix.json` |

The output file already exists from a previous incomplete run. Overwrite it
completely with your corrected version.

---

## JSON Structure

The file has this shape — memorize these field paths:

```json
{
  "domains": [
    {
      "node_type": "domain",
      "data": { "name": "AWS — Compute", ... },
      "terms": [
        {
          "node_type": "term",
          "data": {
            "term": "EC2 Instance Types",
            "definition": "EC2 instance types define the combination of ...",
            "difficulty": "beginner",
            "module": "EC2",
            "category": "compute",
            "code_example": "...",
            "short_reference": "..."
          },
          "metadata": { "has_examples": true }
        }
      ]
    }
  ]
}
```

**The field to edit is:** `term.data.definition`

**Fields to leave completely untouched:**
`term`, `difficulty`, `module`, `category`, `code_example`, `short_reference`,
`node_type`, `metadata`, and all domain-level fields.

**Scale:** 11 domains, 123 terms total.

---

## Transformation Rule

**Before:** The definition names the term anywhere in its text.
**After:** The definition describes the concept without using the term's name.

### Opening-sentence pattern variants

These are the forms that appear at the start of a definition. Handle all of them:

| Pattern | Example before | Example after |
|---------|---------------|---------------|
| `"X is a ..."` | `"EC2 Auto Scaling automatically adjusts..."` | `"Automatically adjusts..."` |
| `"AWS X is ..."` or `"Amazon X is ..."` | `"AWS Lambda is a serverless compute service..."` | `"A serverless compute service..."` |
| `"X (ACRONYM) is ..."` | `"A Service Control Policy (SCP) defines..."` | `"Defines the maximum permissions..."` |
| `"The X ..."` | `"The Transit Gateway acts as a central hub..."` | `"Acts as a central hub..."` |
| `"An X is ..."` | `"An IAM role is an identity with..."` | `"An identity with..."` |
| `"X does/acts/connects/allows ..."` | `"Spot Instances allow you to bid..."` | `"Allow you to bid..."` |
| `"Using X, ..."` | `"Using Lambda Layers, you can..."` | `"Allows you to..."` |

### Mid-sentence occurrences

If the term appears in a sentence that does not open with it, rephrase
that sentence to remove the term. Do not simply delete the term — rewrite
to preserve the meaning.

**Example:**
- Term: `EC2 Auto Scaling`
- Before: `"EC2 Auto Scaling automatically adjusts the number of EC2 instances in a group based on demand. EC2 Auto Scaling can also replace unhealthy instances automatically."`
- After: `"Automatically adjusts the number of EC2 instances in a group based on demand. Can also replace unhealthy instances automatically."`

### Definitions that are already clean

If a definition contains **no** form of the term in any sentence,
**leave it exactly as-is**. Do not rephrase or improve clean definitions.

---

## AWS Naming Rules

AWS term names have many surface forms — all count as matches:

| Term | Also match |
|------|------------|
| `Amazon S3` | `S3`, `Simple Storage Service` |
| `AWS Lambda` | `Lambda` |
| `EC2 Auto Scaling` | `EC2 Auto Scaling`, `Auto Scaling` (when referring to the same service) |
| `IAM Role` | `IAM role`, `iam role` |
| `Service Control Policy` | `SCP`, `service control policy` |

Rules:
- Match is **case-insensitive** everywhere.
- Strip `AWS ` or `Amazon ` prefix and match the short name too.
- If the term contains an acronym in parentheses like `CloudTrail (CT)`,
  match both the full name and the acronym.
- Match plural forms: if term is `Spot Instance`, also match `Spot Instances`,
  and vice versa.

---

## Per-Sentence Scanning Rule

A definition can be multiple sentences. Apply this rule to **each sentence**:

1. Does this sentence contain the term in any form (case-insensitive, any
   naming variant, including plurals)?
2. **Yes** → rewrite this sentence to remove the term.
3. **No** → copy this sentence through unchanged, word for word.

Work through every sentence. Do not stop after fixing the first sentence.
Do not change a sentence that does not contain the term.

---

## Grammatical Requirements

- Every output definition must be grammatically complete and natural English.
- Sentences must start with a capital letter.
- Do not produce sentence fragments (e.g., do not start with a bare verb
  phrase if that produces an ungrammatical opening — rephrase instead).
- Preserve all technical detail, specifics, numbers, and AWS service names
  that are NOT the term being defined.

---

## Process — Follow These Steps Exactly

1. **Read** `/home/jimbob/Dev/AWS_Dev/data/aws_upload.json` using the Read tool.

2. **Work through every domain and every term** in order. For each term:
   a. Note the value of `data.term` — this is the term to remove.
   b. Read `data.definition`.
   c. Determine whether the definition contains the term in any form.
   d. If yes: rewrite `data.definition` with the term removed from every
      sentence that contains it. All other sentences copy through unchanged.
   e. If no: leave `data.definition` exactly as-is.

3. **Keep a running count** of how many definitions you changed and how many
   you left unchanged.

4. **Do not modify any other field.** Only `data.definition` changes.

5. **Write** the complete modified JSON to
   `/home/jimbob/Dev/AWS_Dev/data/aws_upload-fix.json` using the Write tool.
   The file must be valid JSON. Write the entire file in one Write call.

6. **Verify** by re-reading the output file with the Read tool and confirming
   it parses correctly (no truncation, no JSON syntax errors).

7. **Report**: state how many terms you inspected, how many definitions you
   changed, and how many you left unchanged. The total must equal 123.

---

## Quality Check — Do This Before Writing

Pick the **first 5 definitions you changed** and for each one confirm:

- [ ] The term name does not appear anywhere in the output definition
      (check full name, short name, acronym, plural form).
- [ ] The output definition is a grammatically complete sentence.
- [ ] The technical content is preserved — no facts were dropped or altered.
- [ ] No other field was changed.

If any check fails, fix that definition before writing the file.
