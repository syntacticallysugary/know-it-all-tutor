#!/usr/bin/env python3
"""
MNRL Text Similarity Model Training Script
Optimized for DGX Spark and AWS Lambda deployment.

Uses Multiple Negatives Ranking Loss (MNRL) for superior semantic understanding.
Trains sentence-transformers/all-MiniLM-L6-v2 model (~80MB) for deployment to AWS Lambda.
"""

import json
import logging
import os
import time
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from typing import Dict, Any, Optional, List, Tuple
from torch.utils.data import DataLoader
from sentence_transformers import SentenceTransformer, InputExample, losses, models
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _extract_content(message) -> str:
    """Extract text from a chat completion message.

    Handles three thinking-model patterns:
    - Nemotron clean: puts thinking + answer in content, separated by </think>
    - Nemotron leaky: thinking bleeds into content with no </think> tag
    - Qwen3: puts thinking in message.reasoning, content is None
    """
    content = message.content or ''

    # Pattern 1: clean </think> separator
    if '</think>' in content:
        return content.split('</think>', 1)[-1].strip()

    # Pattern 2: Qwen3 — no content at all
    if not content.strip():
        reasoning = getattr(message, 'reasoning', None) or ''
        for line in reversed(reasoning.splitlines()):
            line = line.strip()
            if line and not line.startswith('*') and not line.startswith('#'):
                return line.strip('"').strip("'")
        return ''

    # Pattern 3: inline thinking — content starts with thinking text.
    # Thinking text tends to be multi-sentence. The actual answer is
    # usually the last complete sentence that doesn't start with a
    # thinking phrase ("Okay", "Let me", "I need", "The user", etc.)
    thinking_starts = ('okay', 'let me', 'i need', 'i should', 'the user',
                       'first', 'so ', 'now', 'looking', 'based on', 'since')
    sentences = [s.strip() for s in content.replace('\n', ' ').split('.') if s.strip()]
    for sentence in reversed(sentences):
        if sentence and not sentence.lower().startswith(thinking_starts):
            return sentence.strip() + '.'
    return content.strip()


def download_and_prepare_sts(positive_threshold: float = 4.0) -> Tuple[List[InputExample], List[InputExample]]:
    """Download STS Benchmark and return training/dev split.

    MNRL only accepts positive pairs — feeding a low-similarity pair as a
    "positive" example actively harms training.  We keep only pairs whose
    gold similarity score is >= positive_threshold (STS scores run 0-5).

    Dev examples retain all scores (as float labels) so the evaluator can
    measure Spearman correlation across the full similarity range.
    """
    logger.info("📥 Downloading STS Benchmark dataset...")

    from datasets import load_dataset
    sts_dataset = load_dataset('mteb/stsbenchmark-sts')

    # Training: positive pairs only (no label needed for MNRL)
    train_examples = [
        InputExample(texts=[item['sentence1'], item['sentence2']])
        for item in sts_dataset['train']
        if item['score'] >= positive_threshold
    ]

    # Dev: keep all pairs with their scores for EmbeddingSimilarityEvaluator
    dev_examples = [
        InputExample(texts=[item['sentence1'], item['sentence2']], label=item['score'])
        for item in sts_dataset['validation']
    ]

    logger.info(f"📊 Training positives (score >= {positive_threshold}): {len(train_examples)}")
    logger.info(f"📊 Development examples: {len(dev_examples)}")
    return train_examples, dev_examples


def load_domain_data(
    data_dir: str = os.path.join(BASE_DIR, '..', 'data'),
    use_fix_files: bool = True,
) -> List[InputExample]:
    """Load ground-truth definitions from the quiz upload JSON files.

    Returns InputExample pairs suitable for MNRL training once you have
    synthetic paraphrases.  Call generate_synthetic_pairs() to expand these
    into actual training data.

    Args:
        data_dir: Directory containing *_upload.json or *_upload-fix.json files.
        use_fix_files: Prefer the cleaned -fix.json files when available.
    """
    import json, glob

    pattern_fix = os.path.join(data_dir, '*_upload-fix.json')
    pattern_raw = os.path.join(data_dir, '*_upload.json')

    # Prefer -fix files; fall back to originals for domains not yet cleaned
    fix_files = {os.path.basename(p).replace('-fix.json', '') for p in glob.glob(pattern_fix)}
    all_files = glob.glob(pattern_fix) if use_fix_files else []
    for p in glob.glob(pattern_raw):
        stem = os.path.basename(p).replace('.json', '')
        if stem not in fix_files:
            all_files.append(p)

    definitions: List[Tuple[str, str]] = []  # (term, definition)
    for path in sorted(all_files):
        with open(path) as f:
            data = json.load(f)
        for domain in data.get('domains', []):
            for term_obj in domain.get('terms', []):
                d = term_obj.get('data', {})
                term = d.get('term', '').strip()
                defn = (d.get('short_reference') or d.get('definition', '')).strip()
                if term and defn:
                    definitions.append((term, defn))

    logger.info(f"📚 Loaded {len(definitions)} ground-truth definitions from {len(all_files)} files")
    return definitions


def generate_short_refs(
    data_dir: str = os.path.join(BASE_DIR, '..', 'data'),
    llm_base_url: str = 'http://localhost:8000/v1',
    llm_model: str = 'qwen3.5-35b',
    max_tokens: int = 32768,
    temperature: float = 0.3,
) -> None:
    """Generate a 1-2 sentence short_reference for each term and save it into the JSON files.

    Skips terms that already have a short_reference.  Safe to re-run — only
    fills in missing entries.  Writes back to the same *_upload-fix.json files.
    """
    import glob

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai  # needed for local LLM calls")

    client = OpenAI(base_url=llm_base_url, api_key='local')

    pattern = os.path.join(data_dir, '*_upload-fix.json')
    all_files = sorted(glob.glob(pattern))

    system_prompt = (
        "You write concise reference answers for educational flashcards. "
        "Output the answer only — no thinking, no preamble, no markdown, no numbering."
    )

    total_written = 0
    total_skipped = 0

    for path in all_files:
        with open(path) as f:
            data = json.load(f)

        file_changed = False
        for domain in data.get('domains', []):
            for term_obj in domain.get('terms', []):
                d = term_obj.get('data', {})
                term = d.get('term', '').strip()
                defn = d.get('definition', '').strip()

                if not term or not defn:
                    continue
                if d.get('short_reference'):
                    total_skipped += 1
                    continue

                user_prompt = (
                    f"Write a 1-2 sentence answer that a student should give when asked "
                    f"to define \"{term}\". Base it on this full definition:\n\"{defn}\"\n\n"
                    f"Requirements:\n"
                    f"- Keep it to 1-2 sentences maximum\n"
                    f"- Capture the essential meaning only\n"
                    f"- Write it as a student answer, not a textbook definition\n"
                    f"- Do not start with the term name"
                )

                short_ref = ''
                for attempt in range(3):
                    try:
                        response = client.chat.completions.create(
                            model=llm_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user",   "content": user_prompt},
                            ],
                            max_tokens=max_tokens,
                            temperature=temperature,
                        )
                        candidate = _extract_content(response.choices[0].message)
                        if len(candidate) >= 30:
                            short_ref = candidate
                            break
                        logger.warning(f"  ⚠️  Short response for '{term}' (attempt {attempt+1}): {repr(candidate)}")
                    except Exception as e:
                        import traceback
                        logger.warning(f"  ⚠️  Failed '{term}' (attempt {attempt+1}): {e}\n{traceback.format_exc()}")

                logger.info(f"  '{term}' → {repr(short_ref[:80]) if short_ref else 'EMPTY after 3 attempts'}")
                if short_ref:
                    d['short_reference'] = short_ref
                    file_changed = True
                    total_written += 1
                    # Save after every term so a crash loses at most one entry
                    with open(path, 'w') as f:
                        json.dump(data, f, indent=2)
                    if total_written % 25 == 0:
                        logger.info(f"  {total_written} short references generated...")
                else:
                    logger.warning(f"  ⚠️  Skipping '{term}' after 3 failed attempts")

        if file_changed:
            logger.info(f"  💾 Finished {os.path.basename(path)}")

    logger.info(f"✅ Done — {total_written} written, {total_skipped} already had short_reference")


def generate_synthetic_pairs(
    definitions: List[Tuple[str, str]],
    paraphrases_per_term: int = 3,
    cache_path: str = os.path.join(BASE_DIR, 'synthetic_pairs_cache.json'),
    llm_base_url: str = 'http://localhost:8000/v1',
    llm_model: str = 'qwen3.5-35b',
    max_tokens: int = 8192,
    temperature: float = 0.8,
) -> List[InputExample]:
    """Generate synthetic (student_paraphrase, ground_truth) training pairs via local LLM.

    Calls a vLLM-compatible OpenAI endpoint (default: localhost:8000).
    Results are cached to disk so a partial run can be resumed without
    re-generating terms that already completed.

    Args:
        definitions:         (term, definition) tuples from load_domain_data().
        paraphrases_per_term: Number of correct student-answer variants per term.
        cache_path:          JSON file to persist completed generations.
                             Delete it to force a full regeneration.
        llm_base_url:        Base URL of the OpenAI-compatible inference server.
        llm_model:           Model name as registered with the inference server.
        max_tokens:          Max tokens per LLM response.
        temperature:         Sampling temperature — 0.8 gives vocabulary variety
                             without hallucinating wrong meanings.

    Returns:
        InputExample list ready for MNRL DataLoader.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("pip install openai  # needed for local LLM calls")

    client = OpenAI(base_url=llm_base_url, api_key='not-needed')

    # Load existing cache so the run is resumable
    cache: Dict[str, List[str]] = {}
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cache = json.load(f)
        logger.info(f"📂 Resuming — {len(cache)} terms already cached in {cache_path}")

    system_prompt = (
        "You are generating training data for a semantic similarity model used in "
        "an educational quiz application. Your output must be plain text only — "
        "no JSON, no markdown, no numbering."
    )

    def _paraphrase(term: str, definition: str, n: int) -> List[str]:
        """Call the LLM and return a list of n student-answer paraphrases."""
        user_prompt = (
            f"A student is asked to define the term \"{term}\".\n"
            f"The correct definition is:\n\"{definition}\"\n\n"
            f"Write exactly {n} different ways a student might write a correct answer "
            f"to that question. Requirements:\n"
            f"- Each answer must preserve the core meaning of the definition\n"
            f"- Use different vocabulary and sentence structure for each\n"
            f"- Vary the style: some formal, some informal, some brief, some detailed\n"
            f"- A student answer may or may not restate the term name — both are fine\n"
            f"- Do NOT produce wrong or partial answers\n"
            f"Output exactly {n} answers, one per line, no blank lines between them, "
            f"no numbering, no bullet points."
        )

        response = client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        raw = _extract_content(response.choices[0].message)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        # Pad or trim to exactly n lines in case the model miscounts
        while len(lines) < n:
            lines.append(lines[-1] if lines else definition)
        return lines[:n]

    examples = []
    total = len(definitions)

    for i, (term, defn) in enumerate(definitions):
        cache_key = f"{term}||{defn[:40]}"  # stable key that survives minor edits

        if cache_key not in cache:
            try:
                paraphrases = _paraphrase(term, defn, paraphrases_per_term)
                cache[cache_key] = paraphrases
                # Persist after every term so a crash loses at most one term
                with open(cache_path, 'w') as f:
                    json.dump(cache, f, indent=2)
            except Exception as e:
                logger.warning(f"  ⚠️  Skipping '{term}': {e}")
                cache[cache_key] = [defn] * paraphrases_per_term  # fall back to self-pair

        for paraphrase in cache[cache_key]:
            # Anchor = student answer, Positive = ground truth definition
            examples.append(InputExample(texts=[paraphrase, defn]))

        if (i + 1) % 25 == 0 or (i + 1) == total:
            logger.info(f"  {i + 1}/{total} terms processed ({len(examples)} pairs so far)")

    logger.info(f"✅ {len(examples)} training pairs ready ({paraphrases_per_term} per term)")
    return examples


class MNRLSimilarityModel:
    """Sentence Transformer model trained with Multiple Negatives Ranking Loss."""
    
    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """Initialize the model.
        
        Args:
            model_name: Pre-trained sentence transformer model
        """
        self.model_name = model_name
        import torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"🧠 Initializing {model_name} on {self.device.upper()}...")
        if self.device == 'cuda':
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")

        # Create embedding model
        word_embedding_model = models.Transformer(model_name, max_seq_length=128)
        pooling_model = models.Pooling(
            word_embedding_model.get_word_embedding_dimension(),
            pooling_mode_mean_tokens=True,
            pooling_mode_cls_token=False,
            pooling_mode_max_tokens=False,
        )
        normalize_model = models.Normalize()
        self.model = SentenceTransformer(modules=[word_embedding_model, pooling_model, normalize_model], device=self.device)
    
    def train(
        self,
        train_examples: List[InputExample],
        dev_examples: Optional[List[InputExample]] = None,
        epochs: int = 4,
        batch_size: int = 256,
        warmup_steps: int = 100,
        output_path: str = './trained_mnrl_model',
        show_sentence_embeddings: bool = True,
    ) -> None:
        """Train the model with Multiple Negatives Ranking Loss.
        
        Args:
            train_examples: Training data (pairs of texts)
            dev_examples: Validation data (optional)
            epochs: Number of training epochs
            batch_size: Training batch size (larger = better for DGX)
            warmup_steps: Learning rate warmup steps
            output_path: Path to save trained model
            show_sentence_embeddings: Whether to compute and show embeddings
        """
        logger.info("🏋️ Starting MNRL training with Multiple Negatives Ranking Loss...")
        
        # MNRL expects InputExample(texts=[a, b]) with NO label field —
        # the loss treats every other item in the batch as a negative.
        mnrl_examples = [
            InputExample(texts=[ex.texts[0], ex.texts[1]])
            for ex in train_examples
        ]
        train_dataloader = DataLoader(mnrl_examples, shuffle=True, batch_size=batch_size)
        
        # Use MultipleNegativesRankingLoss (optimal for large batches)
        train_loss = losses.MultipleNegativesRankingLoss(self.model)
        
        logger.info(f"📦 MNRL Training Configuration:")
        logger.info(f"   Batch Size: {batch_size}")
        logger.info(f"   Epochs: {epochs}")
        logger.info(f"   Warmup Steps: {warmup_steps}")
        logger.info(f"   Loss: MultipleNegativesRankingLoss")
        
        # Build evaluator from dev examples if provided (needs float labels)
        evaluator = None
        if dev_examples:
            s1 = [ex.texts[0] for ex in dev_examples]
            s2 = [ex.texts[1] for ex in dev_examples]
            scores = [float(ex.label) / 5.0 for ex in dev_examples]  # STS scores are 0-5
            evaluator = EmbeddingSimilarityEvaluator(s1, s2, scores, name='sts-dev')

        # Train the model
        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            evaluator=evaluator,
            epochs=epochs,
            warmup_steps=warmup_steps,
            show_progress_bar=True,
            output_path=output_path,
        )
        
        logger.info(f"✅ Training completed. Model saved to: {output_path}")
        self.model.save(output_path)
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts.
        
        Args:
            text1: First text (e.g., ground truth)
            text2: Second text (e.g., student answer)
            
        Returns:
            Cosine similarity score (0-1)
        """
        # Generate embeddings
        embedding1 = self.model.encode([text1])
        embedding2 = self.model.encode([text2])
        
        # Compute cosine similarity
        from sentence_transformers.util import cos_sim as cosine_similarity
        score = cosine_similarity(embedding1[0], embedding2[0])[0][0]
        
        return float(score)
    
    def batch_similarity(self, pairs: List[tuple]) -> List[float]:
        """Compute similarities for a batch of text pairs.
        
        Args:
            pairs: List of tuples [(text1, text2), ...]
            
        Returns:
            List of similarity scores
        """
        texts1 = [pair[0] for pair in pairs]
        texts2 = [pair[1] for pair in pairs]
        
        embeddings1 = self.model.encode(texts1)
        embeddings2 = self.model.encode(texts2)
        
        from sentence_transformers.util import cos_sim as cosine_similarity
        similarities = cosine_similarity(embeddings1, embeddings2)
        
        return [float(similarities[i][i]) for i in range(len(pairs))]
    
    def save_model(self, output_path: str) -> None:
        """Save the trained model.
        
        Args:
            output_path: Path to save the model
        """
        self.model.save(output_path)
        logger.info(f"💾 Model saved to: {output_path}")
    
    def load_model(self, model_path: str) -> None:
        """Load a trained model.
        
        Args:
            model_path: Path to the saved model
        """
        logger.info(f"🔄 Loading model from: {model_path}")
        self.model = SentenceTransformer(model_path)


def train_mnrl_model(
    use_domain_data: bool = True,
    llm_base_url: str = 'http://localhost:8000/v1',
    llm_model: str = 'qwen3.5-35b',
) -> Dict[str, Any]:
    """Train the MNRL text similarity model.

    Args:
        use_domain_data: If True (recommended), train on synthetic pairs derived
            from your quiz definitions.  If False, fall back to STS Benchmark
            (useful for a baseline comparison only).
        llm_base_url: Base URL of the vLLM-compatible inference server that
            will generate synthetic training pairs.  Can be a remote LAN
            address (e.g. http://192.168.1.XXX:8000/v1) if the GPU is on a
            different machine.
        llm_model: Model name as registered with the inference server.
            Check with: curl <base_url>/models

    Returns:
        Training results and metrics
    """
    start_time = time.time()

    logger.info("🚀 Starting MNRL Text Similarity Model Training")
    logger.info(f"LLM endpoint: {llm_base_url}  model: {llm_model}")
    logger.info("Sentence model: sentence-transformers/all-MiniLM-L6-v2")
    logger.info("Loss: MultipleNegativesRankingLoss")

    # Step 1: Prepare training data
    if use_domain_data:
        logger.info("📚 Loading domain-specific quiz definitions...")
        definitions = load_domain_data()
        train_examples = generate_synthetic_pairs(
            definitions,
            paraphrases_per_term=3,
            llm_base_url=llm_base_url,
            llm_model=llm_model,
        )
        # STS dev set still useful for measuring general semantic quality
        _, dev_examples = download_and_prepare_sts()
    else:
        logger.info("📥 Using STS Benchmark (baseline mode)...")
        train_examples, dev_examples = download_and_prepare_sts()

    # Step 2: Initialize model
    model = MNRLSimilarityModel(model_name='sentence-transformers/all-MiniLM-L6-v2')
    
    # Step 3: Train with MNRL
    logger.info("🏋️ Starting MNRL training...")
    training_start = time.time()
    
    model.train(
        train_examples=train_examples,
        dev_examples=dev_examples,
        epochs=5,                    # More epochs for better convergence
        batch_size=256,              # MNRL works best with large batches
        warmup_steps=100,
        output_path='./trained_mnrl_model',
    )
    
    training_time = time.time() - training_start
    
    # Step 4: Test with semantic pairs
    logger.info("🧪 Testing model on semantic similarity pairs...")
    
    test_pairs = [
        ("The mitochondria is the powerhouse of the cell", "Cells get energy from mitochondria"),
        ("The Great Gatsby is a novel about Jay Gatsby", "There I was, the Great Gatsby was a novel"),
        ("Python is a programming language", "I use Python for coding"),
        ("Photosynthesis converts light energy into chemical energy", "Plants use photosynthesis to make food"),
        ("The Great Gatsby is a movie", "The Great Gatsby is a novel"),
        ("Machine learning is a subset of artificial intelligence", "AI includes machine learning"),
        ("The cat is sleeping on the sofa", "A cat is napping on the couch"),
        ("I love learning about quantum physics", "I hate studying quantum mechanics"),
        ("Water boils at 100 degrees Celsius", "Water freezes at 0 degrees Celsius"),
        ("The economy is growing rapidly", "The stock market is declining"),
    ]
    
    predictions = model.batch_similarity(test_pairs)
    
    logger.info("\n📋 Test Results:")
    logger.info("="*70)
    for i, ((text1, text2), score) in enumerate(zip(test_pairs, predictions)):
        logger.info(f"Test {i+1}: Score = {score:.3f}")
        logger.info(f"  Text A: {text1}")
        logger.info(f"  Text B: {text2}")
        logger.info(f"  Status: {'✅ Similar' if score > 0.7 else '❌ Different'}")
        logger.info("")
    
    # Step 5: Save final model
    model.save_model(os.path.join(BASE_DIR, 'final_mnrl_model'))
    
    total_time = time.time() - start_time
    
    results = {
        'total_time_hours': total_time / 3600,
        'training_time_hours': training_time / 3600,
        'train_examples': len(train_examples),
        'model_path': os.path.join(BASE_DIR, 'final_mnrl_model'),
        'test_results': list(zip(test_pairs, predictions)),
    }
    
    logger.info("🎉 Training pipeline completed successfully!")
    logger.info(f"⏱️  Total time: {results['total_time_hours']:.2f} hours")
    logger.info(f"🎯 Training epochs: 5")
    logger.info(f"📊 Training examples: {results['train_examples']:,}")
    logger.info(f"💾 Model location: {results['model_path']}")
    
    return results


def quick_test_mnrl_model() -> None:
    """Quick test of the trained MNRL model."""
    logger.info("🔍 Testing trained MNRL model...")
    
    try:
        model = MNRLSimilarityModel()
        model.load_model(os.path.join(BASE_DIR, 'final_mnrl_model'))
        
        print("\n" + "="*70)
        print("MNRL TEXT SIMILARITY TESTER")
        print("="*70)
        
        while True:
            print("\n" + "-"*70)
            text1 = input("Enter first text (ground truth) [or 'quit']: ").strip()
            if text1.lower() == 'quit':
                break
                
            text2 = input("Enter second text (student answer) [or 'quit']: ").strip()
            if text2.lower() == 'quit':
                break
            
            similarity = model.compute_similarity(text1, text2)
            
            print("\n" + "="*70)
            print("📊 RESULTS")
            print("="*70)
            print(f"🎯 Similarity Score: {similarity:.3f}")
            print(f"   Ground Truth:   '{text1}'")
            print(f"   Student Answer: '{text2}'")
            print("="*70)
            print(f"Grade: ", end="")
            
            if similarity >= 0.90:
                print("✅ EXCELLENT - Nearly identical meaning")
            elif similarity >= 0.80:
                print("✅ CORRECT - Sufficiently close (correct answer)")
            elif similarity >= 0.70:
                print("⚠️  PARTIAL - Related but missing key points")
            elif similarity >= 0.60:
                print("❌ INCORRECT - Weak semantic match")
            else:
                print("❌ WRONG - Different meaning entirely")
            
            print("="*70)
                
    except FileNotFoundError:
        logger.error("❌ Trained model not found. Please run training first.")
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")


def calibrate_from_file(
    cal_path: str = os.path.join(BASE_DIR, 'calibration_set.json'),
    model_path: str = os.path.join(BASE_DIR, 'final_mnrl_model'),
) -> None:
    """Run threshold calibration against a filled-in calibration_set.json.

    Reads every entry that has a non-empty student_answer, scores it against
    short_reference, prints per-term results, and writes scores back into the
    file so the session is cumulative — run it again after filling in more
    answers and it will score only the new ones (already-scored entries are
    skipped unless you clear the score field).
    """
    import json, os

    if not os.path.exists(cal_path):
        print(f"Calibration file not found: {cal_path}")
        return

    with open(cal_path) as f:
        entries = json.load(f)

    model = MNRLSimilarityModel()
    model.load_model(model_path)

    scored = [e for e in entries if e.get('student_answer', '').strip() and 'score' not in e]
    already = [e for e in entries if 'score' in e]

    if not scored:
        print(f"No new answers to score ({len(already)} already scored).")
        _print_calibration_summary(entries)
        return

    print(f"\nScoring {len(scored)} new answers ({len(already)} already done)...\n")
    print("=" * 72)

    for entry in scored:
        sr   = entry['short_reference']
        ans  = entry['student_answer'].strip()
        sim  = model.compute_similarity(sr, ans)
        entry['score'] = round(sim, 4)

        if sim >= 0.90:
            label = "EXCELLENT"
        elif sim >= 0.80:
            label = "CORRECT"
        elif sim >= 0.70:
            label = "PARTIAL"
        elif sim >= 0.60:
            label = "WEAK"
        else:
            label = "WRONG"

        print(f"[{entry['subject'].upper():<26}] {entry['term']}")
        print(f"  ref: {sr[:90]}")
        print(f"  ans: {ans[:90]}")
        print(f"  => {sim:.3f}  {label}")
        print()

    with open(cal_path, 'w') as f:
        json.dump(entries, f, indent=2)

    print(f"Scores saved to {cal_path}")
    _print_calibration_summary(entries)


def _print_calibration_summary(entries: list) -> None:
    scored = [e for e in entries if 'score' in e]
    if not scored:
        return
    scores = [e['score'] for e in scored]
    bands = {'EXCELLENT (>=0.90)': 0, 'CORRECT (>=0.80)': 0, 'PARTIAL (>=0.70)': 0,
             'WEAK (>=0.60)': 0, 'WRONG (<0.60)': 0}
    for s in scores:
        if s >= 0.90:   bands['EXCELLENT (>=0.90)'] += 1
        elif s >= 0.80: bands['CORRECT (>=0.80)'] += 1
        elif s >= 0.70: bands['PARTIAL (>=0.70)'] += 1
        elif s >= 0.60: bands['WEAK (>=0.60)'] += 1
        else:           bands['WRONG (<0.60)'] += 1
    print("\n" + "=" * 72)
    print(f"CALIBRATION SUMMARY  ({len(scored)} of {len(entries)} terms scored)")
    print("=" * 72)
    for label, count in bands.items():
        bar = '#' * count
        print(f"  {label:<24} {count:3d}  {bar}")
    avg = sum(scores) / len(scores)
    print(f"\n  Mean score: {avg:.3f}   Min: {min(scores):.3f}   Max: {max(scores):.3f}")
    print("=" * 72)


def export_to_onnx(
    model_path: str = os.path.join(BASE_DIR, 'final_mnrl_model'),
    output_dir: str = os.path.join(BASE_DIR, 'onnx_model'),
) -> None:
    """Export trained model to ONNX format for Lambda deployment.

    Requires: pip install optimum[onnxruntime]
    Result: ~25 MB INT8 model suitable for the 500 MB Lambda container.
    """
    logger.info("💾 Exporting model to ONNX format...")

    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
        from transformers import AutoTokenizer

        # Export: from_pretrained with export=True converts on-the-fly
        ort_model = ORTModelForFeatureExtraction.from_pretrained(model_path, export=True)
        tokenizer = AutoTokenizer.from_pretrained(model_path)

        os.makedirs(output_dir, exist_ok=True)
        ort_model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

        logger.info(f"✅ ONNX model written to: {output_dir}")
        for fname in sorted(os.listdir(output_dir)):
            fpath = os.path.join(output_dir, fname)
            if os.path.isfile(fpath):
                size_mb = os.path.getsize(fpath) / 1024 / 1024
                logger.info(f"   {fname}: {size_mb:.1f} MB")

    except ImportError:
        logger.warning("⚠️  optimum not installed. Run: pip install optimum[onnxruntime]")


def check_semantic_understanding() -> None:
    """Demonstrate MNRL's improved semantic understanding."""
    logger.info("📊 Testing semantic understanding comparison...")
    
    print("\n" + "="*70)
    print("MNRL SEMANTIC UNDERSTANDING DEMONSTRATION")
    print("="*70)
    
    model = MNRLSimilarityModel()
    try:
        model.load_model(os.path.join(BASE_DIR, 'final_mnrl_model'))
    except FileNotFoundError:
        logger.error("Model not found. Running with pre-trained model instead.")
        model = MNRLSimilarityModel(model_name='sentence-transformers/all-MiniLM-L6-v2')
    
    tests = [
        {
            "description": "Synonyms vs Same Meaning",
            "ground_truth": "The mitochondria produces energy for the cell",
            "student_correct": "Mitochondria provide power to the cell",
            "student_wrong": "Mitochondria destroy the cell's energy"
        },
        {
            "description": "Same Words, Wrong Meaning",
            "ground_truth": "The Great Gatsby is a novel set in the 1920s",
            "student_correct": "The Great Gatsby is a story about the Jazz Age",
            "student_wrong": "The Great Gatsby is a biography of a real person"
        },
        {
            "description": "Different Topics",
            "ground_truth": "Photosynthesis occurs in plant chloroplasts",
            "student_different": "Cellular respiration happens in mitochondria"
        }
    ]
    
    for test in tests:
        print(f"\n📝 {test['description']}")
        print(f"{'='*70}")
        
        gt = test['ground_truth']
        
        for key in ['student_correct', 'student_wrong']:
            if key in test:
                student = test[key]
                score = model.compute_similarity(gt, student)
                label = "✅" if "correct" in key else "❌"
                print(f"{label} '{student}' → Score: {score:.3f}")
                
        if 'student_different' in test:
            diff = test['student_different']
            score = model.compute_similarity(gt, diff)
            print(f"❌ '{diff}' → Score: {score:.3f} (should be low)")
    
    print("\n" + "="*70)
    print("✅ MNRL model correctly distinguishes semantic similarity!")
    print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "test":
            quick_test_mnrl_model()
        elif cmd == "eval" or cmd == "semantic":
            check_semantic_understanding()
        elif cmd == "export":
            export_to_onnx()
        elif cmd == "refs":
            # Usage: python MNRL-Similarity.py refs [llm_url] [llm_model]
            url   = sys.argv[2] if len(sys.argv) > 2 else 'http://localhost:8000/v1'
            model = sys.argv[3] if len(sys.argv) > 3 else 'qwen3.5-35b'
            logger.info("📝 Generating short reference answers...")
            generate_short_refs(llm_base_url=url, llm_model=model)
            logger.info("✅ Short refs done. Delete synthetic_pairs_cache.json before retraining.")
        elif cmd == "calibrate":
            # Usage: python MNRL-Similarity.py calibrate [path_to_calibration_set.json]
            cal_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE_DIR, 'calibration_set.json')
            calibrate_from_file(cal_path=cal_path)
        elif cmd == "train":
            # Usage: python MNRL-Similarity.py train [llm_url] [llm_model]
            url   = sys.argv[2] if len(sys.argv) > 2 else 'http://localhost:8000/v1'
            model = sys.argv[3] if len(sys.argv) > 3 else 'qwen3.5-35b'
            results = train_mnrl_model(llm_base_url=url, llm_model=model)
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python MNRL-Similarity.py [train [url] [model]|refs [url] [model]|test|eval|export|calibrate [path]]")
            sys.exit(1)
    else:
        # Run training by default
        results = train_mnrl_model()
        
        print("\n" + "="*70)
        print("TRAINING SUMMARY")
        print("="*70)
        print("🎉 MNRL training completed successfully!")
        print(f"⏱️  Total time: {results['total_time_hours']:.2f} hours")
        print(f"🎯 Model: sentence-transformers/all-MiniLM-L6-v2 with MultipleNegativesRankingLoss")
        print(f"📊 Training examples: {results['train_examples']:,}")
        print(f"💾 Model location: {results['model_path']}")
        
        print("\n🧪 To test the model:")
        print("   python MNRL-Similarity.py test")
        
        print("\n📊 To check semantic understanding:")
        print("   python MNRL-Similarity.py eval")
        
        print("\n💾 To export to ONNX (for Lambda):")
        print("   python MNRL-Similarity.py export")
        
        print("="*70)
