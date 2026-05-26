# Definition Cleanup Agent — Java Domain

## Task

Rewrite every `definition` field in the Java domain upload file so that
the term being defined does not appear anywhere in the definition sentence.
The definition is used as the "given" in a quiz — the student must supply
the term — so the definition must not name or allude to the term by name.

## Files to Process

1. `/home/jimbob/Dev/AWS_Dev/data/java_upload.json`

## Output Files

Write the corrected version to a new file with `-fix` appended before the
extension:

1. `/home/jimbob/Dev/AWS_Dev/data/java_upload-fix.json`

## Transformation Rule

**Before:** The definition names the term anywhere in the text.
**After:** The definition describes the concept without naming it.

### Examples

| Term | Before | After |
|------|--------|-------|
| `HashMap` | `HashMap is an implementation of the Map interface that stores key-value pairs in a hash table for O(1) average lookup.` | `An implementation of the Map interface that stores key-value pairs in a hash table for O(1) average lookup.` |
| `CompletableFuture` | `CompletableFuture is an implementation of Future that supports chaining asynchronous operations and combining multiple futures.` | `An implementation of Future that supports chaining asynchronous operations and combining multiple futures.` |
| `record` | `A record is a concise class declaration that automatically generates a constructor, accessors, equals, hashCode, and toString.` | `A concise class declaration that automatically generates a constructor, accessors, equals, hashCode, and toString.` |
| `Stream.filter` | `Stream.filter returns a new stream containing only the elements that match the given predicate.` | `Returns a new stream containing only the elements that match the given predicate.` |
| `@Override` | `The @Override annotation tells the compiler that a method is intended to override a method in a superclass or implement an interface method.` | `Tells the compiler that a method is intended to override a method in a superclass or implement an interface method.` |

### Pattern variants to handle

- `"X is a ..."` → `"A ..."`
- `"The X annotation/keyword/class/interface ... is ..."` → keep predicate, capitalize
- `"X returns/creates/tells/..."` → keep verb phrase, capitalize
- `"An X is ..."` → reopen with the predicate noun phrase
- Term appears mid-sentence → rephrase to remove it
- Definitions that contain **no** form of the term → **leave unchanged**

### Special Java naming considerations

- Java terms may include package prefixes (`java.util.`, `java.lang.`, etc.).
  Match both the fully qualified name and the simple class name.
  For example, for term `java.util.Optional`, also match `Optional` appearing
  as a subject.
- Annotation terms start with `@` (e.g., `@Override`). Match both `@Override`
  and `Override` (without the `@`) in the definition text.
- Interface and class names used as subjects in the definition should be
  matched against the term (e.g., term `Comparator`, definition starts
  "The Comparator interface...").

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
  `ArrayList` matches `arraylist` or `Arraylist`; term `Dropout` matches `dropout`.

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
- Does not name the term in any form (fully qualified, simple name, annotation
  form, plural, or different capitalization)
- Preserves the original meaning
