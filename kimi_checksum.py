#!/usr/bin/env python3
"""
kimi_checksum.py — deterministic implementation of the "Kimi decode
methodology" (12-fold scaffolding / checksum / matrix mapping / fractal
decoding), fixing the specific defect found in SCRIPT TO DECODE.

WHAT WAS BROKEN
    SCRIPT TO DECODE's Step 4 ("Derive the Checksum") scored each word's
    "semantic" value as `hash(word) % 100`. Python's built-in hash() for
    strings is randomized per process by default (PEP 456 -- a security
    feature, unrelated to text analysis) -- so the same file produced a
    different "checksum" every run: 14104, then 14870, then 14740, three
    runs in a row, zero text changes. That's not a property of the course.
    It's a property of Python process startup.

WHAT THIS SCRIPT DOES INSTEAD
    - Syntactic axis:  words per sentence.               (unchanged, was already stable)
    - Numerical axis:  sum(ord(c) for c in sentence) % 1000. (unchanged, was already stable --
                        ord() is a fixed codepoint table, not a hash)
    - Semantic axis:   REPLACED. Each word's Shannon information content
                        within this corpus, -log2(P(word)), where P(word)
                        is the word's empirical frequency in the text.
                        This is a real, well-defined, reproducible quantity
                        (how statistically surprising a word is in this
                        text) -- not a measurement of "meaning," and it's
                        labeled here as exactly what it is: a frequency
                        statistic, nothing more.
    - Fractal layers:  capped at 6 explicit layers (matching the
                        methodology's own "6 layers"), with a real stop
                        condition: each layer's input is the outlier
                        sentences (by word-frequency deviation) found in
                        the layer above -- a strictly shrinking subset --
                        so the loop terminates when the outlier set stops
                        shrinking, empties out, or layer 6 is reached.
                        No open-ended "refine forever."
    - Celestial timing (original Step 5: "may require ... astronomical
      data for optimal decoding moment") is NOT implemented. A
      deterministic text tool cannot honestly make its answer depend on
      the Moon's position when you happen to run it -- that would make
      the checksum a function of the clock, not of the course. Omitted
      rather than faked.

Usage:
    python3 kimi_checksum.py --input tobey_clean_copy.txt
"""

import argparse
import math
import re
from collections import Counter


def split_sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def split_words(text):
    return re.findall(r"[A-Za-z']+", text.lower())


def build_frequency_table(all_words):
    counts = Counter(all_words)
    total = sum(counts.values())
    return counts, total


def semantic_score(word, counts, total):
    """Shannon information content of a word in this corpus: -log2(P(word))."""
    freq = counts.get(word, 1)
    p = freq / total
    return -math.log2(p)


def matrix_row(sentence, counts, total):
    words = split_words(sentence)
    syntactic = len(words)
    semantic = sum(semantic_score(w, counts, total) for w in words)
    numerical = sum(ord(c) for c in sentence) % 1000
    return {"syntactic": syntactic, "semantic": round(semantic, 4), "numerical": numerical}


def compute_checksum(sentences, counts, total):
    rows = [matrix_row(s, counts, total) for s in sentences]
    checksum = sum(r["syntactic"] + r["semantic"] + r["numerical"] for r in rows)
    return round(checksum, 4), rows


def find_outliers(sentences, counts, total):
    """Sentences containing at least one word whose frequency is a strong
    outlier (>2x or <0.5x the corpus average) -- the 'variant checksum
    candidates' from Step 2, computed the same way each time."""
    avg_freq = total / max(len(counts), 1)
    outlier_words = {w for w, c in counts.items() if c > avg_freq * 2 or c < avg_freq * 0.5}
    return [s for s in sentences if any(w in outlier_words for w in split_words(s))]


def fractal_decode(all_sentences, counts, total, max_layers=6):
    layers = []
    current = all_sentences
    seen_sizes = set()

    for layer_num in range(1, max_layers + 1):
        if not current:
            break
        checksum, _ = compute_checksum(current, counts, total)
        layers.append({
            "layer": layer_num,
            "sentence_count": len(current),
            "checksum": checksum,
        })
        next_set = find_outliers(current, counts, total)
        # Stop condition: outlier set stopped shrinking (fixed point) or emptied.
        if len(next_set) >= len(current) or len(next_set) in seen_sizes:
            break
        seen_sizes.add(len(next_set))
        current = next_set

    return layers


def main():
    parser = argparse.ArgumentParser(description="Deterministic Kimi-methodology checksum for the course text.")
    parser.add_argument("--input", "-i", required=True)
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    sentences = split_sentences(text)
    all_words = split_words(text)
    counts, total = build_frequency_table(all_words)

    print("=" * 80)
    print("KIMI DECODE — DETERMINISTIC CHECKSUM")
    print("=" * 80)
    print()
    print(f"Sentences: {len(sentences)}   Unique words: {len(counts)}   Total words: {total}")
    print()

    top_checksum, _ = compute_checksum(sentences, counts, total)
    print(f"Whole-course checksum (syntactic + semantic + numerical, summed over all {len(sentences)} sentences):")
    print(f"  {top_checksum}")
    print()

    layers = fractal_decode(sentences, counts, total)
    print("Fractal layers (each layer = outlier sentences from the layer above):")
    for l in layers:
        print(f"  Layer {l['layer']}: {l['sentence_count']} sentences, checksum = {l['checksum']}")
    print()
    print(f"Stopped after {len(layers)} layer(s): "
          f"{'reached the 6-layer cap' if len(layers) == 6 else 'outlier set stopped shrinking (fixed point reached)'}.")
    print()
    print("Re-run this on the same file as many times as you like -- the checksum")
    print("above will be identical every time. That reproducibility is the fix.")
    print("=" * 80)


if __name__ == "__main__":
    main()
