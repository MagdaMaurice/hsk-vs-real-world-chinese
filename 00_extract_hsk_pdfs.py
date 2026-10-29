"""
00_extract_hsk_pdfs.py

Extract the HSK 3.0 (July 2026 syllabus) vocabulary tables from the seven
MandarinBean level PDFs into one raw CSV (11,000 rows).

The PDFs are not redistributed in this repository. Download them from
https://mandarinbean.com/new-hsk-vocabulary/ and put them in one folder, named:
    New-HSK-Vocabulary-Level-1.pdf ... Level-6.pdf, New-HSK-Vocabulary-Level-7-9.pdf

Usage:
    pip install pdfplumber
    python 00_extract_hsk_pdfs.py --pdf-dir path/to/pdfs --out hsk_vocabulary_raw_uncleaned.csv

Why coordinates instead of plain text: entries that wrap onto a second line
(words with several parts of speech) scramble when read line by line. Each
word's x-position is used to assign it to the right column instead.

The output is deliberately RAW. Known issues that the cleaning notebook fixes:
  * look-alike Kangxi-radical characters (e.g. 八 stored as the radical form)
  * 口 stored as the radical form of 又
  * part-of-speech field still in the PDF's 、-separated form
  * Levels 7-9 have no English column in the source
"""
import argparse
import csv
import os

import pdfplumber

LEVELS = ["1", "2", "3", "4", "5", "6", "7-9"]
FOOTER_TOKENS = {"MandarinBean.com", "Page", "NEW", "HSK", "VOCABULARY", "ENTRIES", ">>"}
HEADER_TOKENS = {"NO.", "WORD", "PINYIN", "PART", "OF", "SPEECH", "TRANSLATION", "Level"}
FIELDS = ["hsk_level", "no_in_level", "word", "pinyin", "part_of_speech", "english"]


def get_columns(page):
    """Find the x-positions of the header row (NO. / WORD / PINYIN / PART OF SPEECH / TRANSLATION)."""
    cols = {}
    for w in page.extract_words():
        t = w["text"]
        if t == "NO.":
            cols["no"] = w["x0"]
        elif t == "WORD":
            cols["word"] = w["x0"]
        elif t == "PINYIN":
            cols["pinyin"] = w["x0"]
        elif t == "PART":
            cols["pos"] = w["x0"]
        elif t == "TRANSLATION":
            cols["english"] = w["x0"]
    return cols if "no" in cols and "word" in cols else None


def assign_column(x0, bounds):
    best = bounds[0][1]
    for thresh, name in bounds:
        if x0 >= thresh - 5:
            best = name
    return best


def parse_pdf(path):
    entries, current, bounds = [], None, None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            if bounds is None:
                cols = get_columns(page)
                if not cols:
                    continue  # cover page
                bounds = sorted((v, k) for k, v in cols.items())

            words = page.extract_words()
            # The title block ("ENTRIES <n>") sits above the header row on the first data page.
            has_title_block = any(w["text"] == "ENTRIES" for w in words)
            # Drop the whole footer line: the bare page/level numbers on it share x-positions
            # with real data columns and would otherwise leak into the nearest entry.
            footer_tops = {w["top"] for w in words if w["text"] == "MandarinBean.com"}
            words = [w for w in words if not any(abs(w["top"] - ft) < 3 for ft in footer_tops)]
            words = [w for w in words if w["text"] not in FOOTER_TOKENS | HEADER_TOKENS]
            if has_title_block:
                words = [w for w in words if w["top"] >= 100]
            if not words:
                continue

            words.sort(key=lambda w: (w["top"], w["x0"]))
            lines, line = [], [words[0]]
            for w in words[1:]:
                if abs(w["top"] - line[-1]["top"]) < 3:
                    line.append(w)
                else:
                    lines.append(line)
                    line = [w]
            lines.append(line)

            for line in lines:
                no_word = next(
                    (w["text"] for w in line
                     if assign_column(w["x0"], bounds) == "no" and w["text"].isdigit()),
                    None,
                )
                if no_word is not None:
                    if current:
                        entries.append(current)
                    current = {"no": no_word, "word": "", "pinyin": "", "pos": "", "english": ""}
                    line_words = [w for w in line if w["text"] != no_word]
                else:
                    if current is None:
                        continue
                    line_words = line  # wrapped continuation of the previous entry

                buckets = {}
                for w in sorted(line_words, key=lambda w: w["x0"]):
                    col = assign_column(w["x0"], bounds)
                    if col != "no":
                        buckets.setdefault(col, []).append(w["text"])
                for col in ("word", "pinyin", "pos", "english"):
                    if col in buckets:
                        text = " ".join(buckets[col])
                        current[col] = (current[col] + " " + text) if current[col] else text
    if current:
        entries.append(current)
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf-dir", default=".", help="folder containing the seven level PDFs")
    ap.add_argument("--out", default="hsk_vocabulary_raw_uncleaned.csv")
    args = ap.parse_args()

    rows = []
    for level in LEVELS:
        path = os.path.join(args.pdf_dir, f"New-HSK-Vocabulary-Level-{level}.pdf")
        entries = parse_pdf(path)
        print(f"Level {level}: {len(entries)} entries")
        rows += [
            {"hsk_level": level, "no_in_level": e["no"], "word": e["word"], "pinyin": e["pinyin"],
             "part_of_speech": e["pos"], "english": e["english"]}
            for e in entries
        ]

    # utf-8-sig so Excel on Windows opens the Chinese text correctly
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Total rows: {len(rows)} (expected 11,000) -> {args.out}")


if __name__ == "__main__":
    main()
