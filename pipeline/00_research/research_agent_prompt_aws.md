# Research Agent Prompt — AWS Domain

You are a Research Assistant building training data for a semantic similarity model.
The semantic similarity model will be used to evaluate student answers in an educational
platform, so your work must be accurate, comprehensive, and focused on the most important
concepts in the domain.
Your assignment is the **AWS** knowledge domain.

### Step 1: Read Your Context

Before doing anything else, read the project specification at:
`/home/jimbob/Dev/AWS_Dev/.kiro/specs/student-teacher/student_model.md`
For broader context, read the description of the tutorial system at:
`/home/jimbob/Dev/AWS_Dev/README.md`

Pay particular attention to:
- The **Category Taxonomy** in Phase 1, including both the universal categories and
  the domain-specific categories listed for AWS
- The output format requirements

Note: The user of this system is preparing for the **AWS SAP-C02 (Solutions Architect
Professional)** exam. Weight coverage toward services and concepts that appear on that
exam.

### Step 2: Audit the Category List

The current AWS categories from `student_model.md` are:

**Universal (applicable to AWS):**
`collections`, `type-system`, `control-flow`, `i/o`, `concurrency`, `introspection`,
`functional`, `string-ops`, `numeric/math`, `memory`

Note: Most universal categories do not apply cleanly to AWS. Only include a universal
category if it maps meaningfully to AWS concepts (e.g. `concurrency` maps to
async/event-driven services; `i/o` maps to data transfer and ingestion services).
Skip universal categories that do not apply rather than forcing a fit.

**AWS-specific:**
`compute`, `storage`, `networking`, `security`, `ai-services`, `databases`, `monitoring`

Using your web search tools, determine:
1. Are there important AWS service groupings or concept areas missing from the list?
2. For each missing category you identify, briefly justify why it belongs.
3. Produce a **final category list** — mark any new additions clearly.

Do not add a category unless you can immediately populate it with at least 5 terms.

### Step 3: Research Terms for Each Category

Scope: **AWS services and architectural concepts as of 2025.** For each service,
cover both what the service is and key concepts within it (e.g. for IAM: policies,
roles, groups, trust relationships; for S3: buckets, object storage classes, lifecycle
policies). Include architectural patterns where they are named and testable
(e.g. "blue/green deployment", "event-driven architecture").

For each category in your final list, identify the most important AWS terms using
web search. For each term:
- Use the official AWS service name or concept name
- Understand what it does and when to use it vs. alternatives
- Note what AWS service family it belongs to (the `module` value, e.g. `IAM`,
  `S3`, `VPC`, `CloudFormation`, `architectural-pattern`)
- Identify a one-line description of a representative use case where applicable

**Coverage targets:**
- Aim for 8-15 terms per category
- Prioritize services and concepts that appear on the SAP-C02 exam and in
  real-world AWS architecture
- Include both service names and key sub-concepts within services

**Research guidance:**
- Use the official AWS documentation (docs.aws.amazon.com) as your primary source
- Cross-reference with the AWS SAP-C02 exam guide and 1-2 AWS training resources
- Do not copy definitions verbatim from any source

### Step 4: Write Original Definitions

For each term, write an original definition that:
- Explains **what the term is** in one sentence
- Explains **what it does, when to use it, or why it matters** in one to two sentences
- Is written in your own words — do not copy or closely paraphrase any source
- Is accurate enough that a student answer can be evaluated against it
- Assumes intermediate-level audience (knows cloud basics, learning AWS specifics)

Definitions should be 2-4 sentences. Avoid marketing language ("industry-leading",
"fully managed" as a standalone claim), circular definitions, and vague filler.
Do distinguish between similar services (e.g. SQS vs SNS, ECS vs EKS) so the
definition is unambiguous.

### Step 5: Produce the Output File

Write your results to:
`/home/jimbob/Dev/AWS_Dev/data/aws_upload.json`

Use this exact JSON structure:

```json
{
  "domains": [
    {
      "node_type": "domain",
      "data": {
        "name": "AWS — <Category Name>",
        "description": "<One sentence describing what this category covers in AWS>",
        "subject": "aws",
        "difficulty": "<beginner|intermediate|advanced>",
        "estimated_hours": <number>,
        "prerequisites": ["<prereq1>", "<prereq2>"]
      },
      "terms": [
        {
          "node_type": "term",
          "data": {
            "term": "<official AWS service or concept name>",
            "definition": "<your original definition>",
            "difficulty": "<beginner|intermediate|advanced>",
            "module": "<AWS service family, e.g. IAM, S3, VPC, architectural-pattern>",
            "category": "<category name from your final category list>",
            "code_example": "<representative use case or CLI example, or omit if not applicable>"
          },
          "metadata": {
            "has_examples": false
          }
        }
      ]
    }
  ],
  "sources": [
    "AWS documentation: https://docs.aws.amazon.com/",
    "AWS SAP-C02 exam guide: <URL>",
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
- [ ] Similar services are distinguished clearly in their definitions
- [ ] Sources are listed at the top level of the file
- [ ] The file is written to `data/aws_upload.json`
