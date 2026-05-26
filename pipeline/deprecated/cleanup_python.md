# Definition Cleanup Agent — Python Domain

## Task

Rewrite every `definition` field in the Python domain upload files so that
the term being defined does not appear anywhere in the definition sentence.
The definition is used as the "given" in a quiz — the student must supply
the term — so the definition must not name or allude to the term by name.

## Files to Process

1. `/home/jimbob/Dev/AWS_Dev/data/python_upload.json`

## Output Files

Write the corrected versions to new files with `-fix` appended before the
extension:

1. `/home/jimbob/Dev/AWS_Dev/data/python_upload-fix.json`


## Transformation Rule

**Before:** The definition names the term anywhere in the text.
**After:** The definition describes the concept without naming it.

### Examples

| Term | Before | After |
|------|--------|-------|
| `list` | `A list is a mutable, ordered sequence that stores arbitrary Python objects.` | `A mutable, ordered sequence that stores arbitrary Python objects.` |
| `@atexit.register` | `The @atexit.register decorator registers a function to be called when the interpreter exits.` | `Registers a function to be called when the interpreter exits.` |
| `dict.get()` | `dict.get() returns the value for a key if the key is in the dictionary.` | `Returns the value for a key if the key is in the dictionary.` |
| `lambda` | `A lambda is an anonymous function defined with the lambda keyword.` | `An anonymous function defined with the lambda keyword.` |
| `@property` | `The @property decorator turns a method into a read-only attribute of the same name.` | `Turns a method into a read-only attribute of the same name.` |

### Pattern variants to handle

- `"X is a ..."` → `"A ..."`
- `"The X is ..."` → keep predicate, capitalize
- `"The X decorator/type/function/method/keyword ... is ..."` → keep predicate, capitalize
- `"X does/returns/creates/registers/..."` → keep verb phrase, capitalize
- `"An X is ..."` → reopen with the predicate noun phrase
- Term appears mid-sentence → rephrase to remove it
- Definitions that contain **no** form of the term → **leave unchanged**

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
  `lambda` matches `Lambda`; term `Dropout` matches `dropout`.

## Process

1. Read each file with the `read` tool.
2. Parse the JSON.
3. For each term object, inspect `data.definition`. If it names the term
   in any position in the sentence, rewrite it. If it does not, leave it unchanged.
4. After processing all three files, write each one back to disk using the
   `write` tool with `-fix` appended to the file name (create a new file).
5. Validate by re-reading each output file and confirming it parses as valid JSON.
6. Report: total terms inspected, total definitions changed, per-file counts.

## Quality Check

Before writing any file, review 5 randomly chosen changed definitions and
confirm each one:
- Is grammatically correct as a standalone sentence
- Does not name the term in any form (including plural, different capitalization)
- Preserves the original meaning
