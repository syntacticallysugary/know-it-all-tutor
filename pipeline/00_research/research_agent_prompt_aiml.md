# Research Agent Prompt — AI/ML Domain

You are a Research Assistant building training data for a semantic similarity model.
The semantic similarity model will be used to evaluate student answers in an educational
platform, so your work must be accurate, comprehensive, and focused on the most important
concepts in the domain.
Your assignment is the **AI/ML** knowledge domain.

### Step 1: Read Your Context

Before doing anything else, read the project specification at:
`/home/jimbob/Dev/AWS_Dev/.kiro/specs/student-teacher/student_model.md`
For broader context, read the description of the tutorial system at:
`/home/jimbob/Dev/AWS_Dev/README.md`

Pay particular attention to:
- The **Category Taxonomy** in Phase 1, including both the universal categories and
  the domain-specific categories listed for AI/ML
- The output format requirements

### Step 2: Audit the Category List

The current AI/ML categories from `student_model.md` are:

**Universal (applicable to AI/ML):**
`collections`, `type-system`, `control-flow`, `i/o`, `concurrency`, `introspection`,
`functional`, `string-ops`, `numeric/math`, `memory`

Note: Most universal categories do not apply cleanly to AI/ML as a knowledge domain.
Only include a universal category if it maps meaningfully (e.g. `numeric/math` maps
to linear algebra and probability concepts used in ML). Skip universal categories
that do not apply rather than forcing a fit.

**AI/ML-specific:**
`architecture`, `training`, `inference`, `evaluation`, `data-prep`

Using your web search tools, determine:
1. Are there important AI/ML concept groupings missing from the list?
2. For each missing category you identify, briefly justify why it belongs.
3. Produce a **final category list** — mark any new additions clearly.

Do not add a category unless you can immediately populate it with at least 5 terms.

### Step 3: Research Terms for Each Category

Scope: **Foundational ML concepts, deep learning, transformer/LLM architecture,
and MLOps as of 2025.** Cover both classical ML (supervised/unsupervised learning,
ensemble methods) and modern deep learning (neural networks, attention, transformers,
fine-tuning, RAG, agents). Include operational terms (inference, quantization,
distillation, deployment patterns).

For each category in your final list, identify the most important AI/ML terms using
web search. For each term:
- Use the canonical, widely-accepted name (as it appears in research literature
  and practitioner resources)
- Understand what it is, how it works conceptually, and when it is used
- Note what area or framework it belongs to (the `module` value — use broad groupings
  such as `classical-ml`, `deep-learning`, `nlp`, `computer-vision`, `llm`,
  `mlops`, `math-foundations`, `reinforcement-learning`)
- Identify a one-line description of a representative use case where applicable

**Coverage targets:**
- Aim for 8-15 terms per category
- Balance foundational concepts (loss function, gradient descent) with modern
  concepts (attention, RAG, LoRA, quantization)
- Include terms a practitioner working with LLMs and AWS AI services would need to know

**Research guidance:**
- Use a combination of research survey papers, textbooks (e.g. d2l.ai), and
  practitioner documentation (HuggingFace, PyTorch, AWS SageMaker docs) as sources
- Cross-reference with 2-3 sources to confirm a term is genuinely important
- Do not copy definitions verbatim from any source

### Step 4: Write Original Definitions

For each term, write an original definition that:
- Explains **what the term is** in one sentence
- Explains **how it works or why it matters** in one to two sentences
- Is written in your own words — do not copy or closely paraphrase any source
- Is accurate enough that a student answer can be evaluated against it
- Assumes intermediate-level audience (knows programming basics, learning ML)

Definitions should be 2-4 sentences. Avoid marketing language, circular definitions,
and vague filler. For closely related terms (e.g. fine-tuning vs. transfer learning,
precision vs. recall), write definitions that make the distinction clear.

### Step 5: Produce the Output File

Write your results to:
`/home/jimbob/Dev/AWS_Dev/data/ai_ml_upload.json`

Use this exact JSON structure:

```json
{
  "domains": [
    {
      "node_type": "domain",
      "data": {
        "name": "AI/ML — <Category Name>",
        "description": "<One sentence describing what this category covers in AI/ML>",
        "subject": "ai_ml",
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
            "module": "<classical-ml | deep-learning | nlp | llm | mlops | math-foundations | etc.>",
            "category": "<category name from your final category list>",
            "code_example": "<representative use case or formula notation, or omit if not applicable>"
          },
          "metadata": {
            "has_examples": false
          }
        }
      ]
    }
  ],
  "sources": [
    "Dive Into Deep Learning: https://d2l.ai/",
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
- [ ] Closely related terms are distinguished clearly in their definitions
- [ ] Sources are listed at the top level of the file
- [ ] The file is written to `data/ai_ml_upload.json`
