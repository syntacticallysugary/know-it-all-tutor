#!/usr/bin/env python3
"""
Semantic similarity harness: tests short_reference (def string) vs student-answer
paraphrase pairs against the deployed ONNX cross-encoder.

This mirrors the actual production usage: the model compares what a student typed
against the short_reference field, not the full definition.
"""
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_DIR = '/home/jimbob/Dev/AWS_Dev/lambda/answer-evaluator/model'

_session = None
_tokenizer = None


def _load():
    global _session, _tokenizer
    if _session is None:
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        _session = ort.InferenceSession(f'{MODEL_DIR}/model.onnx', sess_options=opts)
        tok = Tokenizer.from_file(f'{MODEL_DIR}/tokenizer.json')
        tok.enable_padding()
        tok.enable_truncation(max_length=512)
        _tokenizer = tok


def similarity(a: str, b: str) -> float:
    _load()
    encoded = _tokenizer.encode(a, b)
    enc = {
        'input_ids': np.array([encoded.ids], dtype=np.int64),
        'attention_mask': np.array([encoded.attention_mask], dtype=np.int64),
    }
    logits = _session.run(None, enc)[0][0]
    sig = float(1.0 / (1.0 + np.exp(-logits[0])))
    return float(np.clip((sig - 0.0347) / (0.1689 - 0.0347), 0.0, 1.0))


# ---------------------------------------------------------------------------
# Pairs: def_string = actual short_reference from data/*_upload-clean.json
#        student_string = paraphrase in student-answer voice
# ---------------------------------------------------------------------------
PAIRS = [
    {
        'label': '[Python] raise',
        'def_string': "It triggers an error to stop the current code and pass the error up to higher levels. If used without arguments in an except block, it reuses the same error.",
        'student_string': "It throws an exception that halts the program and sends the error up to whatever called the current function. When used alone inside except, it re-raises the same exception.",
    },
    {
        'label': '[Python] list.append()',
        'def_string': "Adds an item to the end of a list and changes the original list directly, without making a new one. It's fast and only takes one item as input.",
        'student_string': "Puts a single element onto the end of a list, modifying it in place rather than creating a copy. It runs in constant time and accepts exactly one argument.",
    },
    {
        'label': '[Python] dict.get()',
        'def_string': "It retrieves a value for a key in a dictionary, or gives a default (like None) if the key isn't there, without throwing an error.",
        'student_string': "Looks up a key and returns its value, or returns a fallback value if the key doesn't exist — no exception is raised either way.",
    },
    {
        'label': '[Python] with statement',
        'def_string': "It's a way to automatically handle setup and cleanup of resources like files or connections, even if an error happens during use.",
        'student_string': "Ensures a resource like a file or database connection is properly opened and closed, even when an exception occurs inside the block.",
    },
    {
        'label': '[Python] yield',
        'def_string': "It's a keyword that lets functions act as generators, pausing and returning values each time they're called, so you can work with data one piece at a time instead of all at once.",
        'student_string': "Turns a function into a generator that produces one value at a time, pausing execution until the next value is requested rather than returning everything at once.",
    },
    {
        'label': '[Python] try/except/else/finally',
        'def_string': "The try block runs code that might cause an error, except handles specific errors, else runs if there's no error, and finally always executes no matter what.",
        'student_string': "try contains the risky code, except catches specific errors if they occur, else runs only when no exception was raised, and finally runs regardless of what happened.",
    },
    {
        'label': '[Python] list comprehension',
        'def_string': "It's a shorthand way to build a new list by processing each item in another list or sequence, maybe with a condition, and it's faster than loops because Python handles the looping efficiently under the hood.",
        'student_string': "A compact syntax for creating a list by transforming or filtering elements from an iterable, often faster than writing an equivalent for loop.",
    },
    {
        'label': '[Python] dict.items()',
        'def_string': "It returns key-value pairs as tuples that update if the dictionary changes, letting you loop through both keys and values together.",
        'student_string': "Gives you a live view of the dictionary as key-value tuples, which you can iterate over to access both the key and value at the same time.",
    },
    {
        'label': '[Python] collections.deque',
        'def_string': "It's a double-ended queue from Python's collections module that lets you add or remove items quickly from both ends, ideal for tasks like queues or sliding window algorithms.",
        'student_string': "A data structure that supports fast inserts and removals at both the front and back, making it better than a list when you need to work with both ends.",
    },
    {
        'label': '[Python] typing.Callable',
        'def_string': "It's a type used to describe functions or variables that take specific arguments and return a certain type, like telling Python what inputs and output a callable has.",
        'student_string': "Used to annotate a variable or parameter that holds a function, specifying what argument types it accepts and what type it returns.",
    },
    {
        'label': '[Python] typing.Optional',
        'def_string': "It's a type that can be either a specific type or None, used when a value might be missing. It's like saying the value could be X or nothing at all.",
        'student_string': "Marks a value as either a given type or None, for cases where the value may not exist. Equivalent to writing X | None.",
    },
    {
        'label': '[Python] dict comprehension',
        'def_string': "It's a shorthand way to create a dictionary using curly braces with key-value expressions, like a faster alternative to using dict() with transformed tuples.",
        'student_string': "A concise way to build a dictionary inline using {key: value} syntax, instead of constructing it with a loop or the dict() constructor.",
    },
    {
        'label': '[Python] dict.setdefault()',
        'def_string': "It checks if a key exists in a dictionary and returns its value, or adds the key with a default value if it doesn't. This helps set up things like lists in a dictionary without replacing what's already there.",
        'student_string': "Returns the value for a key if it's present; otherwise inserts that key with the given default and returns the default. Useful for initializing mutable defaults without overwriting existing entries.",
    },
    {
        'label': '[Python] list.pop()',
        'def_string': "It removes and returns an element from the list, using the last one if no index is given. It changes the list directly and can cause an error if the list is empty or the index is wrong.",
        'student_string': "Removes an element at a given position and returns it, defaulting to the last element. Raises an IndexError if the list is empty or the index is out of range.",
    },
    {
        'label': '[Python] list.extend()',
        'def_string': "It adds all items from an iterable to the list without nesting them, similar to using +=.",
        'student_string': "Appends every element from another iterable directly into the list, flattening them rather than adding the iterable as a single nested item.",
    },
    {
        'label': '[Python] collections.Counter',
        'def_string': "It's a dictionary-like tool that counts how often each item appears and lets you add or combine counts easily.",
        'student_string': "A subclass of dict that tallies occurrences of each element and supports arithmetic operations to merge or subtract counts.",
    },
    {
        'label': '[Python] typing.TypedDict',
        'def_string': "It's a tool to define dictionaries with specific string keys and their value types, helping type checkers validate the structure.",
        'student_string': "Lets you declare a dictionary type with named keys and specific value types so static analysis tools can verify that the dictionary's shape is correct.",
    },
    {
        'label': '[Python] ABC',
        'def_string': "An ABC is a class you can't create directly that forces subclasses to define specific methods, throwing an error if they don't. It's like a blueprint that makes sure subclasses follow certain rules by requiring them to fill in missing pieces.",
        'student_string': "An abstract base class that cannot be instantiated and requires subclasses to implement its abstract methods. Attempting to skip them raises a TypeError.",
    },
    {
        'label': '[Python] Enum',
        'def_string': "It's a class that creates named values instead of using raw strings or numbers, with each name linked to a unique value. Members can be iterated and compared by identity, and subclasses let them act like regular integers or strings.",
        'student_string': "Defines a set of named constants, each bound to a unique value. Members are compared by identity, can be iterated, and subclasses like IntEnum allow them to behave as plain integers.",
    },
    {
        'label': '[Python] typing.Union',
        'def_string': "It allows a value to be one of multiple types, like saying it could be X or Y, and in newer Python versions you can write X | Y instead of using Union.",
        'student_string': "Indicates a value may be one of several types. In Python 3.10+ the pipe syntax X | Y replaces the need for Union explicitly.",
    },
    {
        'label': '[Python] set comprehension',
        'def_string': "It's a shorthand to create a set with curly braces, letting you transform and filter items while automatically removing duplicates.",
        'student_string': "A concise syntax for building a set from an iterable, applying an expression and optional filter, with duplicate values automatically discarded.",
    },
]


def main():
    print(f'Loading model from {MODEL_DIR}...')
    _load()
    print(f'Running {len(PAIRS)} pairs (def_string vs student_string)...\n')

    results = []
    for p in PAIRS:
        score = similarity(p['def_string'], p['student_string'])
        results.append({**p, 'score': score})
        bar = '█' * int(score * 30)
        print(f'{score:.3f} {bar:<30} {p["label"]}')

    results.sort(key=lambda x: x['score'], reverse=True)

    above_75 = [r for r in results if r['score'] >= 0.75]
    above_50 = [r for r in results if r['score'] >= 0.50]
    print(f'\n{len(above_75)}/{len(PAIRS)} pairs scored ≥0.75')
    print(f'{len(above_50)}/{len(PAIRS)} pairs scored ≥0.50 (pass threshold)\n')

    print('=' * 70)
    print('TOP 5 PAIRS')
    print('=' * 70)
    for r in results[:5]:
        print(f'\n  Score: {r["score"]:.3f}  |  {r["label"]}')
        print(f'  Def:     {r["def_string"][:100]}')
        print(f'  Student: {r["student_string"][:100]}')

    print('\n' + '=' * 70)
    print('ALL RESULTS (sorted)')
    print('=' * 70)
    for r in results:
        flag = ' ✓' if r['score'] >= 0.75 else (' ~' if r['score'] >= 0.50 else '')
        print(f'  {r["score"]:.3f}{flag}  {r["label"]}')


if __name__ == '__main__':
    main()
