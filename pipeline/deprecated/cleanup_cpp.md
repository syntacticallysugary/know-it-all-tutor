# Definition Cleanup Agent — C++ Domain

## Task

Rewrite every `definition` field in the C++ domain upload file so that
the term being defined does not appear anywhere in the definition sentence.
The definition is used as the "given" in a quiz — the student must supply
the term — so the definition must not name or allude to the term by name.

## Files to Process

1. `/home/jimbob/Dev/AWS_Dev/data/cpp_upload.json`

## Output Files

Write the corrected version to a new file with `-fix` appended before the
extension:

1. `/home/jimbob/Dev/AWS_Dev/data/cpp_upload-fix.json`

## Transformation Rule

**Before:** The definition names the term anywhere in the text.
**After:** The definition describes the concept without naming it.

### Examples

| Term | Before | After |
|------|--------|-------|
| `std::unique_ptr` | `std::unique_ptr is a smart pointer that owns an object exclusively and deletes it when the pointer goes out of scope.` | `A smart pointer that owns an object exclusively and deletes it when the pointer goes out of scope.` |
| `RAII` | `RAII (Resource Acquisition Is Initialization) is a C++ idiom that ties resource lifetime to object lifetime.` | `A C++ idiom that ties resource lifetime to object lifetime.` |
| `move semantics` | `Move semantics allow a C++ object's resources to be transferred from a temporary to another object without copying.` | `Allow a C++ object's resources to be transferred from a temporary to another object without copying.` |
| `constexpr` | `The constexpr keyword tells the compiler that a value or function can be evaluated at compile time.` | `Tells the compiler that a value or function can be evaluated at compile time.` |
| `std::vector` | `std::vector is a dynamic array container that manages a contiguous block of memory and resizes automatically.` | `A dynamic array container that manages a contiguous block of memory and resizes automatically.` |

### Pattern variants to handle

- `"X is a ..."` → `"A ..."`
- `"std::X is ..."` → keep predicate, capitalize
- `"The X keyword/specifier/qualifier is ..."` → keep predicate, capitalize
- `"X (full name) is ..."` → keep predicate, capitalize
- `"X allows/enables/tells/..."` → keep verb phrase, capitalize
- Term appears mid-sentence → rephrase to remove it
- Definitions that contain **no** form of the term → **leave unchanged**

### Special C++ naming considerations

- Many C++ terms include namespace prefixes (`std::`, `std::ranges::`, etc.).
  Match both the fully qualified name and the short name without the prefix.
  For example, for term `std::shared_ptr`, also match `shared_ptr` appearing
  as a subject.
- Acronym expansions in parentheses count as the term: `RAII (Resource
  Acquisition Is Initialization)` — if the definition opens with the acronym,
  the expansion, or either alone, rewrite it.
- Template syntax in term names (e.g., `std::vector<T>`) — match with or
  without the template parameter in the definition text.

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
  `nullptr` matches `Nullptr`; term `Dropout` matches `dropout`.

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
- Does not name the term in any form (fully qualified, short name, acronym,
  plural, or different capitalization)
- Preserves the original meaning
