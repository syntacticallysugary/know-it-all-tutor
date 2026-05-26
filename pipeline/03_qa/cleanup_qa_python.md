# Definition Cleanup QA Agent — Python Domain

## Role

Audit the cleaned Python definition files against the originals. For every
term, verify that the cleanup was done correctly. Report all failures — do not
stop at the first one.

## Files to Compare

| Role | Original | Fixed |
|------|----------|-------|
| Python core | `/home/jimbob/Dev/AWS_Dev/data/python_upload.json` | `/home/jimbob/Dev/AWS_Dev/data/python_upload-fix.json` |
| Built-ins | `/home/jimbob/Dev/AWS_Dev/data/python_builtin_functions_upload.json` | `/home/jimbob/Dev/AWS_Dev/data/python_builtin_functions_upload-fix.json` |
| Decorators | `/home/jimbob/Dev/AWS_Dev/data/python_decorators_upload.json` | `/home/jimbob/Dev/AWS_Dev/data/python_decorators_upload-fix.json` |

Process each file pair independently and report results per file.

## Output Files

Write the report of all issue found to the base file name with`-issues` 
appended before the extension:

1. `/home/jimbob/Dev/AWS_Dev/data/python_upload-issues.json`
2. `/home/jimbob/Dev/AWS_Dev/data/python_builtin_functions_upload-issues.json`
3. `/home/jimbob/Dev/AWS_Dev/data/python_decorators_upload-issues.json`

## Checks to Run

Run all three checks on every term entry. A term may fail more than one.

### Check 1 — Term Still Present

For each term, collect the full match set:
- The term string itself (case-insensitive)
- The plural form (append or strip `s`/`es` as appropriate)
- Any acronym found in a parenthetical in the term string
- For method/function terms like `dict.get()`, also match the short form
  without the object prefix (e.g., `get()`)

Search every sentence of `data.definition` in the fix file for any member of
the match set. Flag the entry if any sentence still contains the term in any form.

### Check 2 — Grammatical Completeness

Flag the definition if any of the following are true:
- Starts with a leading space or whitespace character
- First non-space character is lowercase
- Starts with a fragment opener: `to `, `which `, `that `, `and `, `but `,
  `or `, `by `, `with `, `for `, `of `, `in `
- Ends without terminal punctuation (`.`, `?`, `!`)

### Check 3 — Field Integrity

For each term (matched by `data.term`), compare every field between the
original and fixed versions. Flag the entry if any field other than
`data.definition` differs.

Fields to check: `term`, `category`, `module`, `difficulty`, `code_example`,
`node_type`, `metadata`.

## Output Format

Print a summary report per file:

```
File: python_upload-fix.json
Total terms inspected: N
Terms with failures:   N

FAILURES
--------
[term name]
  Check 1 FAIL — term found in sentence: "<offending sentence>"
  Check 2 FAIL — definition starts with fragment / lowercase / leading space
  Check 3 FAIL — field `<field>` changed unexpectedly

...

Terms passing all checks: N
```

If all terms pass in a file, print:

```
All N terms passed QA.
```

After all three files, print a combined total.

## Process

1. Read all six files with the `read` tool.
2. Parse each as JSON.
3. For each file pair, build a lookup map from the original keyed by `data.term`.
4. For each entry in the fix file, run all three checks.
5. Collect all failures per file.
6. Print the per-file report, then the combined total.
