# Definition Cleanup QA Agent — C++ Domain

## Role

Audit the cleaned C++ definition file against the original. For every term,
verify that the cleanup was done correctly. Report all failures — do not stop
at the first one.

## Files to Compare

| Role | Path |
|------|------|
| Original | `/home/jimbob/Dev/AWS_Dev/data/cpp_upload.json` |
| Fixed | `/home/jimbob/Dev/AWS_Dev/data/cpp_upload-fix.json` |

## Output Files

Write the report of all issue found to the base file name with`-issues` 
appended before the extension:

1. `/home/jimbob/Dev/AWS_Dev/data/cpp_upload-issues.json`

## Checks to Run

Run all three checks on every term entry. A term may fail more than one.

### Check 1 — Term Still Present

C++ terms have several naming forms — all count as matches:
- The full term string (case-insensitive), e.g., `std::unique_ptr`
- The short name without namespace prefix, e.g., `unique_ptr`
- Any acronym found in a parenthetical in the term string,
  e.g., `RAII (Resource Acquisition Is Initialization)` → also match `RAII`
- The term with template parameters stripped,
  e.g., `std::vector<T>` → also match `std::vector`, `vector`
- The plural form of any of the above

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

Print a summary report:

```
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

If all terms pass, print:

```
All N terms passed QA.
```

## Process

1. Read both files with the `read` tool.
2. Parse both as JSON.
3. Build a lookup map from the original keyed by `data.term`.
4. For each entry in the fix file, run all three checks.
5. Collect all failures.
6. Print the report.
