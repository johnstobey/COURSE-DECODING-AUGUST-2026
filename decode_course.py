#!/usr/bin/env python3
"""
decode_course.py — Text-structure and content decoder for
Carl Payne Tobey's "Correspondence Course in Astrology" (1957).

WHAT THIS DOES
    Splits the course into its 24 lessons and reports, per lesson and
    for the course as a whole: word/sentence/paragraph counts, the
    highest-frequency content words, and literal occurrence counts of
    astrological terms (planets, signs, houses, aspects) that appear
    in the text.

WHAT THIS DELIBERATELY DOES NOT DO
    It does not compute birth-chart "harmonic locks," probabilities,
    ciphers, or pass/fail "verification" status. Those numbers cannot
    be derived from a text file, and the previous script
    ("SCRIPT TO DECODE") produced them as hardcoded constants dressed
    up as computed results — see CANONICAL_LOCKS / CANONICAL_BIRTH_DATA
    / _calculate_joint_probability in that file, none of which read
    anything from the actual course text. This script only reports
    numbers it actually counted.

Usage:
    python3 decode_course.py --input tobey_clean_copy.txt
    python3 decode_course.py --input tobey_clean_copy.txt --format json --output report.json
"""

import argparse
import json
import re
from collections import Counter
from typing import Dict, List, Optional

LESSON_HEADER_RE = re.compile(r'^Lesson #(\d+)\s*$', re.MULTILINE)

# Website chrome carried over from the source page (hosted/maintained by
# Bonnie Lee Hill) that shows up verbatim at the end of every lesson in the
# PDF export. It's not part of Tobey's text and pollutes every count below
# if left in -- strip it before any analysis runs.
BOILERPLATE_LINES = [
    r'^Return to Index\s*$',
    r'^Return to Top\s*$',
    r'^Go to Next Lesson\s*$',
    r"^Bonnie's Links\s*$",
    r'^created by Bonnie Lee Hill,\s*$',
    r'^bonniehill@verizon\.net\s*$',
    r'^last modified on .*\d{4}\s*$',
]
BOILERPLATE_RE = re.compile('|'.join(BOILERPLATE_LINES), re.MULTILINE)


def strip_boilerplate(text: str) -> str:
    lines = [ln for ln in text.split('\n') if not BOILERPLATE_RE.match(ln.strip())]
    return '\n'.join(lines)

PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
           "Saturn", "Uranus", "Neptune", "Pluto"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ASPECTS = ["conjunction", "opposition", "square", "trine", "sextile",
           "semi-square", "sesquiquadrate"]

STOPWORDS = set("""
a an the of to and in is it that this for on with as are was be by at
or from he she they we you i his her its their our your not but if
then than so such which who whom what when where how all any each
have has had do does did will would could should can may might must
been being into out up down over under again further more most other
some no nor only own same too very s t just don now there their theirs
them these those here about were because man many one much also
""".split())


def split_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def split_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]


def term_counts(text: str, terms: List[str]) -> Dict[str, int]:
    lower = text.lower()
    return {t: len(re.findall(r'\b' + re.escape(t.lower()) + r'\b', lower)) for t in terms}


def top_keywords(text: str, n: int = 15) -> List[Dict]:
    words = [w for w in split_words(text) if w not in STOPWORDS and len(w) > 2]
    counts = Counter(words)
    return [{"word": w, "count": c} for w, c in counts.most_common(n)]


def analyze_segment(text: str) -> Dict:
    words = split_words(text)
    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)
    return {
        "characters": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "avg_words_per_sentence": round(len(words) / len(sentences), 2) if sentences else 0,
        "top_keywords": top_keywords(text),
        "planet_mentions": term_counts(text, PLANETS),
        "sign_mentions": term_counts(text, SIGNS),
        "aspect_mentions": term_counts(text, ASPECTS),
        "house_mentions": len(re.findall(r'\bhouses?\b', text.lower())),
    }


def split_lessons(text: str) -> List[Dict]:
    """Split the course into lessons using the literal 'Lesson #N' headers."""
    matches = list(LESSON_HEADER_RE.finditer(text))
    lessons = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # First non-empty line after the header is typically the lesson title.
        title_match = re.search(r'\S.*', body)
        title = title_match.group(0).strip() if title_match else ""
        lessons.append({"lesson": num, "title": title, "body": body})
    return lessons


def decode_course(text: str) -> Dict:
    lessons_raw = split_lessons(text)
    lessons_out = []
    for lesson in lessons_raw:
        analysis = analyze_segment(lesson["body"])
        analysis["lesson"] = lesson["lesson"]
        analysis["title"] = lesson["title"]
        lessons_out.append(analysis)

    overall = analyze_segment(text)

    return {
        "source": {
            "title": "Correspondence Course in Astrology",
            "author": "Carl Payne Tobey",
            "lessons_detected": len(lessons_out),
        },
        "overall": overall,
        "lessons": lessons_out,
    }


def format_report(result: Dict) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("TOBEY CORRESPONDENCE COURSE — TEXT DECODE REPORT")
    lines.append("=" * 80)
    lines.append("")
    src = result["source"]
    lines.append(f"Source: {src['title']} by {src['author']}")
    lines.append(f"Lessons detected: {src['lessons_detected']}")
    lines.append("")

    lines.append("# OVERALL METRICS")
    lines.append("-" * 40)
    o = result["overall"]
    for k in ["characters", "words", "sentences", "paragraphs", "avg_words_per_sentence", "house_mentions"]:
        lines.append(f"{k}: {o[k]}")
    lines.append("")
    lines.append("Top keywords (whole course):")
    for kw in o["top_keywords"]:
        lines.append(f"  {kw['word']}: {kw['count']}")
    lines.append("")
    lines.append("Planet mentions (whole course):")
    for planet, count in sorted(o["planet_mentions"].items(), key=lambda x: -x[1]):
        lines.append(f"  {planet}: {count}")
    lines.append("")
    lines.append("Sign mentions (whole course):")
    for sign, count in sorted(o["sign_mentions"].items(), key=lambda x: -x[1]):
        lines.append(f"  {sign}: {count}")
    lines.append("")
    lines.append("Aspect mentions (whole course):")
    for aspect, count in sorted(o["aspect_mentions"].items(), key=lambda x: -x[1]):
        lines.append(f"  {aspect}: {count}")
    lines.append("")

    lines.append("# PER-LESSON BREAKDOWN")
    lines.append("-" * 40)
    for lesson in result["lessons"]:
        lines.append(f"Lesson #{lesson['lesson']}: {lesson['title']}")
        lines.append(f"  words: {lesson['words']}  sentences: {lesson['sentences']}  paragraphs: {lesson['paragraphs']}")
        top3 = ", ".join(f"{kw['word']}({kw['count']})" for kw in lesson["top_keywords"][:5])
        lines.append(f"  top keywords: {top3}")
        top_planets = sorted(lesson["planet_mentions"].items(), key=lambda x: -x[1])[:3]
        top_planets = [f"{p}({c})" for p, c in top_planets if c > 0]
        if top_planets:
            lines.append(f"  top planet mentions: {', '.join(top_planets)}")
        lines.append("")

    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Decode the Tobey Correspondence Course (real text analysis, no invented statistics).")
    parser.add_argument("--input", "-i", required=True, help="Path to the course text file")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text")
    parser.add_argument("--output", "-o", help="Output file path (defaults to stdout)")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        text = f.read()

    text = strip_boilerplate(text)

    result = decode_course(text)

    if args.format == "json":
        output = json.dumps(result, indent=2)
    else:
        output = format_report(result)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Decode complete. {result['source']['lessons_detected']} lessons analyzed. Output written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
