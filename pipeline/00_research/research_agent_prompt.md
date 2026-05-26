# Research Agent Prompt Template

Use this prompt for each knowledge domain agent. Replace `{{DOMAIN}}` with the
domain name (e.g. `Java`, `C++`, `TypeScript`, `AWS`, `AI/ML`).

---

## Prompt

You are a Research Assistant building training data for a semantic similarity model.  The semantic
similarity model will be used to evaluate student answers in an educational platform, so your work must be accurate, 
comprehensive, and focused on the most important concepts in the domain.
Your assignment is the **{{DOMAIN}}** knowledge domain.

### Step 1: Read Your Context

Before doing anything else, read the project specification at:
`/home/jimbob/Dev/AWS_Dev/.kiro/specs/student-teacher/student_model.md`
For broader context, read the description of the totorial system at:
/home/jimbob/Dev/AWS_Dev/README.md

Pay particular attention to:
- The **Domains in Scope** section to understand what {{DOMAIN}} should cover
- The **Category Taxonomy** in Phase 1, including both the universal categories and
  the domain-specific categories already listed for {{DOMAIN}}
- The output format requirements

### Step 2: Audit the Category List

Review the categories assigned to {{DOMAIN}} in the taxonomy table (universal +
domain-specific). Using your web search tools, determine:

1. Are there important functional groupings within {{DOMAIN}} that are missing from
   the current category list?
2. For each missing category you identify, briefly justify why it belongs.
3. Produce a **final category list** for {{DOMAIN}} — the universal categories that
   apply, the existing domain-specific ones, and any additions you are recommending.
   Mark new additions clearly.

Do not add categories speculatively. Only add a category if you can immediately
populate it with at least 5 terms.

### Step 3: Research Terms for Each Category

For each category in your final list, use web search to identify the most important
terms in {{DOMAIN}} that belong to that category. For each term:

- Find the canonical, widely-accepted name for the term
- Understand what it does, what it is, and how it is used
- Note what module, package, service, or standard it belongs to (this is the `module` value)
- Identify a representative usage example or signature where applicable

**Coverage targets:**
- Aim for 8-15 terms per category
- Prioritize terms that appear frequently in real-world use and in learning materials
- Do not pad with obscure edge cases; depth over breadth

**Research guidance:**
- Use official documentation as your primary source (language specs, AWS docs, etc.)
- Cross-reference with 2-3 learning resources (tutorials, textbooks, courses) to
  confirm a term is genuinely important and not just technically present
- Do not copy definitions verbatim from any source

### Step 4: Write Original Definitions

For each term, write an original definition that:

- Explains **what the term is** in one sentence
- Explains **what it does or why it matters** in one to two sentences
- Is written in your own words — do not copy or closely paraphrase any source
- Is accurate and complete enough that a student answer can be evaluated against it
- Is appropriate for an intermediate-level audience (assume the reader knows the domain
  basics but may not know this specific term)

Definitions should be 2-4 sentences. Avoid:
- Marketing language (e.g. "powerful", "robust", "seamless")
- Circular definitions (defining a term using itself)
- Vague filler ("This is an important concept in {{DOMAIN}}")

### Step 5: Produce the Output File

Write your results to:
`/home/jimbob/Dev/AWS_Dev/data/{{DOMAIN_LOWER}}_upload.json`

where `{{DOMAIN_LOWER}}` is the lowercase domain name with spaces replaced by
underscores (e.g. `aws_upload.json`, `ai_ml_upload.json`).

The file must follow this exact JSON structure (based on the existing Python file at
`data/python_builtin_functions_upload.json`):

```json
{
  "domains": [
    {
      "node_type": "domain",
      "data": {
        "name": "{{DOMAIN}} — <Category Name>",
        "description": "<One sentence describing what this category covers in {{DOMAIN}}>",
        "subject": "{{DOMAIN_LOWER}}",
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
            "module": "<module, package, service, or standard this belongs to>",
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
  ]
}
```

**One domain object per category.** If {{DOMAIN}} has 8 categories with terms, the
output file will have 8 objects in the `domains` array — one per category.

**Do not create a domain object for a category that has fewer than 5 terms.**

### Step 6: Self-Review Checklist

Before finishing, verify:

- [ ] Every definition is original — not copied or closely paraphrased from any source
- [ ] Every term has a `category` value matching your final category list
- [ ] Every term has a `module` value
- [ ] No category domain object has fewer than 5 terms
- [ ] The JSON is valid (no trailing commas, all brackets closed)
- [ ] Definitions are 2-4 sentences and avoid vague or marketing language
- [ ] The file is written to the correct path

### Sources

At the end of your work, append a `sources` key to the top level of the JSON:

```json
{
  "domains": [...],
  "sources": [
    "Official {{DOMAIN}} documentation: <URL>",
    "<Learning resource title>: <URL>",
    "..."
  ]
}
```

This is for attribution and audit purposes — it is stripped before upload.

---

## Invocation Notes (for the person launching agents)

Launch one agent per domain. Domains to cover:

| Domain | `{{DOMAIN}}` | `{{DOMAIN_LOWER}}` | Output file |
|---|---|---|---|
| Java | `Java` | `java` | `data/java_upload.json` |
| C++ | `C++` | `cpp` | `data/cpp_upload.json` |
| TypeScript | `TypeScript` | `typescript` | `data/typescript_upload.json` |
| AWS | `AWS` | `aws` | `data/aws_upload.json` |
| AI/ML | `AI/ML` | `ai_ml` | `data/ai_ml_upload.json` |

Python is already complete at `data/python_builtin_functions_upload.json`.
The Python file needs `category` added to existing terms — this is a separate task,
not handled by the research agents.
