"""Pydantic models for the domain generation pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Subdomain(BaseModel):
    """One subdomain returned by Prompt 1."""

    name: str
    description: str
    authoritative_sources: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


class DomainDecomposition(BaseModel):
    """Full Prompt 1 response — a domain split into subdomains."""

    domain: str
    subdomains: list[Subdomain]


class Term(BaseModel):
    """One term emitted by the Prompt 2 agent loop."""

    term: str
    definition: str
    short_reference: str
    difficulty: str
    category: str
    example: str | None = None
    source: str | None = None


def terms_to_upload_json(
    decomposition: DomainDecomposition,
    subdomain_terms: dict[str, list[Term]],
) -> dict:
    """Convert pipeline output to the standard upload JSON format.

    Args:
        decomposition: Parsed Prompt 1 output.
        subdomain_terms: Map of subdomain name → list of emitted Terms.

    Returns:
        Dict matching the existing upload JSON schema.
    """
    domains = []
    all_sources: set[str] = set()

    for subdomain in decomposition.subdomains:
        terms = subdomain_terms.get(subdomain.name, [])
        if not terms:
            continue

        for term in terms:
            if term.source:
                all_sources.add(term.source)

        domains.append({
            "node_type": "domain",
            "data": {
                "name": f"{decomposition.domain} — {subdomain.name}",
                "description": subdomain.description,
                "subject": decomposition.domain.lower().replace(" ", "_"),
                "difficulty": _majority_difficulty(terms),
                "estimated_hours": max(1, len(terms) // 5),
                "prerequisites": [],
            },
            "terms": [_term_to_node(t) for t in terms],
        })

    return {
        "domains": domains,
        "sources": sorted(all_sources),
    }


def _majority_difficulty(terms: list[Term]) -> str:
    counts: dict[str, int] = {}
    for t in terms:
        counts[t.difficulty] = counts.get(t.difficulty, 0) + 1
    return max(counts, key=lambda k: counts[k])


def _term_to_node(t: Term) -> dict:
    data: dict = {
        "term": t.term,
        "definition": t.definition,
        "short_reference": t.short_reference,
        "difficulty": t.difficulty,
        "category": t.category,
    }
    if t.example:
        data["example"] = t.example
    if t.source:
        data["source"] = t.source

    return {
        "node_type": "term",
        "data": data,
        "metadata": {"has_examples": bool(t.example)},
    }
