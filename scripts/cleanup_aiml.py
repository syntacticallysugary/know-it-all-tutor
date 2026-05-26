#!/usr/bin/env python3
"""AI/ML Definition Cleanup Script
Removes referenced term names from definitions to create self-contained "given" statements.
"""

import json
import re


def remove_term_from_definition(term, definition):
    """Remove references to the term from its definition.

    Args:
        term: The term being defined (e.g., "Neural Network", "LLM")
        definition: The full definition text

    Returns:
        The cleaned definition with term references removed
    """
    if not definition:
        return definition

    # Handle term variations:
    # 1. Extract full term name and any acronym/abbreviation
    term_variations = set()
    term_variations.add(term)
    term_variations.add(term.lower())
    term_variations.add(term.lower().capitalize())

    # Find acronyms in parentheses like "Term (ABC)"
    paren_match = re.search(r"(.+?)\s*\((\w+?)\)", term)
    if paren_match:
        full_name = paren_match.group(1)
        acronym = paren_match.group(2)
        term_variations.add(full_name)
        term_variations.add(full_name.lower())
        term_variations.add(full_name.lower().capitalize())
        term_variations.add(acronym)
        term_variations.add(acronym.upper())
        term_variations.add(acronym.lower())
        # Also handle plural forms
        term_variations.add(acronym + "s")
        term_variations.add(acronym.lower() + "s")

    # Split into sentences for processing
    sentences = split_into_sentences(definition)
    cleaned_sentences = []

    for sent in sentences:
        cleaned_sent = sent.strip()

        # Check if this sentence contains any variation of the term
        if contains_term(cleaned_sent, term_variations):
            # Remove the term and rephrase
            cleaned_sent = remove_term_reference(cleaned_sent, term_variations, term)
            # Capitalize first letter if needed
            if cleaned_sent and cleaned_sent[0].islower():
                cleaned_sent = cleaned_sent[0].upper() + cleaned_sent[1:]

        cleaned_sentences.append(cleaned_sent)

    return " ".join(cleaned_sentences)


def split_into_sentences(text):
    """Split text into sentences, preserving ending punctuation."""
    # Simple sentence splitter
    sentences = re.split(r"(?<=[.!?])\s+", text)
    # Filter empty sentences
    return [s.strip() for s in sentences if s.strip()]


def contains_term(sentence, term_variations):
    """Check if the sentence contains any variation of the term (case-insensitive)."""
    sentence_lower = sentence.lower()
    for variation in term_variations:
        if variation.lower() in sentence_lower:
            return True
    return False


def remove_term_reference(sentence, term_variations, original_term):
    """Remove term references from a sentence and rephrase to make it grammatical."""
    cleaned = sentence
    original_term = original_term or ""

    # Pattern 1: "X is ..." → "A/An ..."
    # Pattern 2: "The X is ..." → "A/An ..."
    # Pattern 3: "X (something) is ..." → handle specially

    # Try various patterns in order
    for i, variation in enumerate(term_variations):
        # Handle "The X is..." pattern
        if (
            f" the {variation.lower().strip()} " in cleaned.lower()
            or f" the {variation.lower().strip()}." in cleaned.lower()
        ):
            replacement = f"the {variation}"
            cleaned = re.sub(
                re.escape(f"the {variation.lower()}"), "", cleaned, flags=re.IGNORECASE
            )
            # Clean up double spaces
            cleaned = re.sub(r"\s+", " ", cleaned)
            # Find a noun phrase to replace with "A"
            cleaned = try_make_complete(cleaned, variation)
            break

    # Handle "X is a..." pattern
    for variation in term_variations:
        pattern = rf"\b{re.escape(variation.lower())}\s+is\s+a"
        if re.search(pattern, cleaned.lower()):
            # Replace "TermName is a" with "A"
            replacement = re.search(pattern, cleaned, re.IGNORECASE)
            if replacement:
                prefix = cleaned[: replacement.start()]
                suffix = cleaned[replacement.end() :]
                cleaned = prefix.strip() + "A" + suffix
                break

    # Handle "An X is..." pattern
    for variation in term_variations:
        pattern = rf"\b{re.escape(variation.lower())}\s+is\s+an"
        if re.search(pattern, cleaned.lower()):
            replacement = re.search(pattern, cleaned.lower())
            if replacement:
                prefix = cleaned[: replacement.start()]
                suffix = cleaned[replacement.end() :]
                prefix = re.sub(r"\s*an\s*", "An ", prefix.strip())
                cleaned = prefix + suffix
                break

    # Handle parenthesized full names: "Full name (ABC)"
    for full_name, acronym in extract_term_variations(term_variations):
        pattern = rf"\b{re.escape(full_name.lower())}\s*\(.*?\)\s+is"
        if re.search(pattern, cleaned.lower()):
            # Replace with just the acronym
            replacement = re.search(pattern, cleaned.lower())
            if replacement:
                # Remove the parenthetical part
                cleaned = re.sub(rf"\s*{re.escape(full_name.lower())}\s*\(.*?\)\s+is", "", cleaned)
                cleaned = re.sub(
                    r"\b" + re.escape(acronym.lower()) + r"\b",
                    "An",
                    cleaned,
                    flags=re.IGNORECASE,
                    count=1,
                )
                break

    # Remove direct term occurrences in the middle of sentences
    for variation in term_variations:
        # Pattern: "Unlike X, ..." or "[...]X[...], [...]"
        if f"unlike {variation.lower()}" in cleaned.lower():
            cleaned = re.sub(
                rf"unlike\s+{re.escape(variation.lower())}\s*,", "", cleaned, flags=re.IGNORECASE
            )
            # Capitalize first letter if now starts with lowercase
            if cleaned[0].islower() and len(cleaned) > 1:
                cleaned = (
                    cleaned[0].upper() + " " + cleaned[1:]
                    if cleaned[1] != " "
                    else cleaned[0:].upper() + cleaned[1:]
                )

    # Handle "Xs" or "X's" (plural/possessive)
    for variation in term_variations:
        # Handle plurals
        plural_variations = [
            variation.lower() + "s",
            variation.lower().capitalize() + "s",
            variation.lower() + "'s",
            variation.lower().capitalize() + "'s",
        ]
        for plural_var in plural_variations:
            if f" {plural_var} " in cleaned.lower() or f" {plural_var}." in cleaned.lower():
                cleaned = re.sub(
                    rf"\s*{re.escape(plural_var)}\s*", " ", cleaned, flags=re.IGNORECASE
                )
                cleaned = re.sub(r"\s+", " ", cleaned)

    cleaned = cleaned.strip()

    # If the sentence is now incomplete or awkward, apply heuristics
    cleaned = try_make_complete(cleaned, original_term)

    # Clean up multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip()


def extract_term_variations(term_variations):
    """Extract pairs of (full_name, acronym) from term_variations set."""
    pairs = []
    for var in term_variations:
        if var.isupper() or var == var.lower():
            # Likely an acronym
            for var2 in term_variations:
                if var2.lower() == var.lower() or var.lower() in var2.lower():
                    if var != var2:
                        pairs.append((var2, var))
                        break
    return pairs


def try_make_complete(text, original_term):
    """If the text is incomplete or doesn't start with a word, try to make it complete.
    """
    text = text.strip()

    # If it doesn't start with a capital or is empty, prepend description
    if not text or (text and text[0].islower()):
        # Check what kind of term this is
        word_start = original_term.lower().split()[0] if original_term else ""
        if word_start in ["a", "an", "the"]:
            text = f"The {original_term.lower() if original_term.lower().startswith(' ') else original_term}"

        # Try to infer category based on term
        if "network" in text.lower() or "networks" in text.lower():
            text = text if text else "A type of network"
        elif "layer" in text.lower():
            text = text if text else "A type of neural network layer"
        elif "loss" in text.lower() or "cost" in text.lower():
            text = text if text else "A function that measures error"
        elif "metric" in text.lower():
            text = text if text else "A measure of performance"
        elif "algorithm" in text.lower() or "optimization" in text.lower():
            text = text if text else "An optimization method"
        elif "technique" in text.lower() or "regularization" in text.lower():
            text = text if text else "A machine learning technique"
        elif "architecture" in text.lower():
            text = text if text else "A type of neural network architecture"
        elif "mechanism" in text.lower() or "attention" in text.lower():
            text = text if text else "A mechanism for processing information"
        elif "dataset" in text.lower() or "benchmark" in text.lower():
            text = text if text else "A standardized dataset"
        elif "encoding" in text.lower():
            text = text if text else "A method for representing data"
        elif (
            "training" in text.lower()
            or "fine-tuning" in text.lower()
            or "learning" in text.lower()
        ):
            text = text if text else "A method for learning from data"
        elif "inference" in text.lower():
            text = text if text else "A method for using a trained model"
        elif "database" in text.lower() or "vector" in text.lower():
            text = text if text else "A storage system for data"

    return text


def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)


def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def main():
    # Load input file
    input_file = "/home/jimbob/Dev/AWS_Dev/data/ai_ml_upload.json"
    output_file = "/home/jimbob/Dev/AWS_Dev/data/ai_ml_upload-fix.json"

    data = load_json(input_file)

    changed_count = 0
    total_terms = 0
    changed_definitions = []

    # Process all terms
    for domain in data.get("domains", []):
        for term_obj in domain.get("terms", []):
            term_data = term_obj.get("data", {})
            term = term_data.get("term", "")
            definition = term_data.get("definition", "")

            if not definition:
                continue

            total_terms += 1

            # Check if definition contains the term
            original_def = definition
            cleaned_def = remove_term_from_definition(term, definition)

            if cleaned_def != original_def:
                changed_count += 1
                term_data["definition"] = cleaned_def
                changed_definitions.append(
                    {
                        "term": term,
                        "original": original_def[:200] + "..."
                        if len(original_def) > 200
                        else original_def,
                        "cleaned": cleaned_def[:200] + "..."
                        if len(cleaned_def) > 200
                        else cleaned_def,
                    }
                )

    # Save output
    save_json(output_file, data)

    # Report
    print(f"Total terms inspected: {total_terms}")
    print(f"Definitions changed: {changed_count}")
    print("\nSample changes:")
    for item in changed_definitions[:5]:
        print(f"\n  Term: {item['term']}")
        print(f"  Original: {item['original']}")
        print(f"  Cleaned:  {item['cleaned']}")

    print(f"\nOutput written to: {output_file}")


if __name__ == "__main__":
    main()
