# Research Agent Prompt — Java Domain

You are a Research Assistant building training data for a semantic similarity model.
The semantic similarity model will be used to evaluate student answers in an educational
platform, so your work must be accurate, comprehensive, and focused on the most important
concepts in the domain.
Your assignment is the **Java** knowledge domain.

### Step 1: Read Your Context

Before doing anything else, read the project specification at:
`/home/jimbob/Dev/AWS_Dev/.kiro/specs/student-teacher/student_model.md`
For broader context, read the description of the tutorial system at:
`/home/jimbob/Dev/AWS_Dev/README.md`

Pay particular attention to:
- The **Category Taxonomy** in Phase 1, including both the universal categories and
  the domain-specific categories listed for Java
- The output format requirements

### Step 2: Audit the Category List

The current Java categories from `student_model.md` are:

**Universal (applicable to Java):**
`collections`, `type-system`, `control-flow`, `i/o`, `concurrency`, `introspection`,
`functional`, `string-ops`, `numeric/math`, `memory`

**Java-specific:**
`oop`, `streams-api`, `annotations`

Using your web search tools, determine:
1. Are there important functional groupings within Java that are missing?
2. For each missing category you identify, briefly justify why it belongs.
3. Produce a **final category list** — mark any new additions clearly.

Do not add a category unless you can immediately populate it with at least 5 terms.

### Step 3: Research Terms for Each Category

Scope: **Java LTS versions 8, 11, 17, and 21.** Focus on language keywords, core
collections, concurrency primitives, the Streams API, key standard library classes
(e.g. `Optional`, `Stream`, `CompletableFuture`), annotations, and OOP patterns.

For each category in your final list, identify the most important Java terms using
web search. For each term:
- Find the canonical, widely-accepted name (use fully qualified class names where
  meaningful, e.g. `java.util.Optional`)
- Understand what it does and how it is used
- Note what package it belongs to (the `module` value, e.g. `java.util`, `java.lang`)
- Identify a representative usage example or signature where applicable

**Coverage targets:**
- Aim for 8-15 terms per category
- Prioritize terms that appear in real-world Java development and learning materials
- Do not pad with obscure edge cases

**Research guidance:**
- Use the official Java SE documentation (docs.oracle.com) as your primary source
- Cross-reference with 2-3 learning resources to confirm importance
- Do not copy definitions verbatim from any source

### Step 4: Write Original Definitions

For each term, write an original definition that:
- Explains **what the term is** in one sentence
- Explains **what it does or why it matters** in one to two sentences
- Is written in your own words — do not copy or closely paraphrase any source
- Is accurate enough that a student answer can be evaluated against it
- Assumes intermediate-level audience (knows Java basics, may not know this term)

Definitions should be 2-4 sentences. Avoid marketing language, circular definitions,
and vague filler.

### Step 5: Produce the Output File

Write your results to:
`/home/jimbob/Dev/AWS_Dev/data/java_upload.json`

Use this exact JSON structure:

```json
{
  "domains": [
    {
      "node_type": "domain",
      "data": {
        "name": "Java — <Category Name>",
        "description": "<One sentence describing what this category covers in Java>",
        "subject": "java",
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
            "module": "<package this belongs to, e.g. java.util>",
            "category": "<category name from your final category list>",
            "code_example": "<brief usage example or signature, or omit if not applicable>"
          },
          "metadata": {
            "signature": "<method/class signature if applicable, else omit>",
            "has_examples": false
          }
        }
      ]
    }
  ],
  "sources": [
    "Java SE documentation: https://docs.oracle.com/en/java/javase/",
    "<additional source title>: <URL>"
  ]
}
```

One domain object per category. Do not create a domain object for a category with
fewer than 5 terms.

### Step 6: Self-Review Checklist

Before finishing, verify:

- [ ] Every term has both `category` and `module` fields
- [ ] No definition is copied or closely paraphrased from any source
- [ ] No category domain object has fewer than 5 terms
- [ ] The JSON is valid (no trailing commas, all brackets closed)
- [ ] Definitions are 2-4 sentences, free of vague or marketing language
- [ ] Sources are listed at the top level of the file
- [ ] The file is written to `data/java_upload.json`
