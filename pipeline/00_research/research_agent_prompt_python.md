# Research Agent Prompt — Python Domain

You are a Research Assistant building training data for a semantic similarity model.
The semantic similarity model will be used to evaluate student answers in an educational
platform, so your work must be accurate, comprehensive, and focused on the most important
concepts in the domain.
Your assignment is the **Python** knowledge domain.

### Step 1: Read Your Context

Before doing anything else, read the project specification at:
`/home/jimbob/Dev/AWS_Dev/.kiro/specs/student-teacher/student_model.md`
For broader context, read the description of the tutorial system at:
`/home/jimbob/Dev/AWS_Dev/README.md`

Pay particular attention to:
- The **Category Taxonomy** in Phase 1, including both the universal categories and
  the domain-specific categories listed for Python
- The output format requirements

### Step 2: Review the Existing Python Data

The Python domain already has two partially-complete files:
- `data/python_builtin_functions_upload.json` — 71 built-in functions and 18 decorators
  across 2 domains. Terms have `module` but **no `category` field yet**.

Read both files carefully. For each existing term, you will need to assign a `category`
value from the final category list you produce in Step 3.

### Step 3: Audit the Category List

The current Python categories from `student_model.md` are:

**Universal (applicable to Python):**
`collections`, `type-system`, `control-flow`, `i/o`, `concurrency`, `introspection`,
`functional`, `string-ops`, `numeric/math`, `memory`

**Python-specific:**
`iteration`, `context-managers`, `packaging`

Using your web search tools, determine:
1. Are there important functional groupings within Python that are missing?
2. For each missing category you identify, briefly justify why it belongs.
3. Produce a **final category list** — mark any new additions clearly.

Do not add a category unless you can immediately populate it with at least 5 terms.

### Step 4: Research Terms for Each Category

For each category in your final list, identify the most important Python terms that
belong to it. This includes:
- Terms **not yet covered** by the existing built-ins and decorators files
- Any gaps in the existing data you notice during review

For each term:
- Find the canonical, widely-accepted name
- Understand what it does and how it is used
- Note what module it belongs to (the `module` value)
- Identify a representative usage example or signature where applicable

**Coverage targets:**
- Aim for 8-15 terms per category
- Prioritize terms that appear frequently in real-world use and learning materials
- Do not pad with obscure edge cases; depth over breadth

**Research guidance:**
- Use the official Python 3.12 documentation as your primary source
- Cross-reference with 2-3 learning resources to confirm importance
- Do not copy definitions verbatim from any source

### Step 5: Write Original Definitions

For **new terms** (not in the existing files), write an original definition that:
- Explains **what the term is** in one sentence
- Explains **what it does or why it matters** in one to two sentences
- Is written in your own words — do not copy or closely paraphrase any source
- Is accurate enough that a student answer can be evaluated against it
- Assumes intermediate-level audience knowledge

Definitions should be 2-4 sentences. Avoid marketing language, circular definitions,
and vague filler.

For **existing terms**, do not rewrite the definitions — only add the `category` field.

### Step 6: Produce the Output Files

Write your results to two files:

**File 1** — Updated existing data with `category` added to every term:
`/home/jimbob/Dev/AWS_Dev/data/python_builtin_functions_upload.json`

Update this file in place. Add `"category": "<value>"` to the `data` object of every
existing term. Do not change any other fields.

**File 2** — New terms not covered by the existing files:
`/home/jimbob/Dev/AWS_Dev/data/python_upload.json`

This file covers Python concepts beyond built-ins and decorators — standard library
modules, language keywords, OOP patterns, etc. Use the same JSON structure:

```json
{
  "domains": [
    {
      "node_type": "domain",
      "data": {
        "name": "Python — <Category Name>",
        "description": "<One sentence describing what this category covers in Python>",
        "subject": "python",
        "difficulty": "<beginner|intermediate|advanced>",
        "estimated_hours": <number>,
        "prerequisites": ["<prereq1>", "<prereq2>"]
      },
      "terms": [
        {
          "node_type": "term",
          "data": {
            "term": "<canonical term name>",
            "definition": "<your original definition>",
            "difficulty": "<beginner|intermediate|advanced>",
            "module": "<module or standard this belongs to>",
            "category": "<category name from your final category list>",
            "code_example": "<brief usage example or signature, or omit if not applicable>"
          },
          "metadata": {
            "signature": "<function/method signature if applicable, else omit>",
            "has_examples": false
          }
        }
      ]
    }
  ],
  "sources": [
    "Python 3.12 documentation: https://docs.python.org/3.12/",
    "<additional source title>: <URL>"
  ]
}
```

One domain object per category. Do not create a domain object for a category with
fewer than 5 terms.

### Step 7: Self-Review Checklist

Before finishing, verify:

- [ ] Every term in `python_builtin_functions_upload.json` now has a `category` field
- [ ] Every new term in `python_upload.json` has both `category` and `module` fields
- [ ] No definition is copied or closely paraphrased from any source
- [ ] No category domain object has fewer than 5 terms
- [ ] Both JSON files are valid (no trailing commas, all brackets closed)
- [ ] Definitions are 2-4 sentences, free of vague or marketing language
- [ ] Sources are listed at the top level of `python_upload.json`
