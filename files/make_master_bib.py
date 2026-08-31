#!/usr/bin/env python3
"""
Create jdc_master.bib from the bibliography files used by jdc_cv.tex.

The source bibliography files are not modified.
"""

from pathlib import Path
from urllib.request import urlopen
import re
import sys


BASE_URL = (
    "https://raw.githubusercontent.com/"
    "PrincetonUniversity/jdc-pni/main/files/"
)

FILES = [
    ("jdc_refs.bib", ["article"]),
    ("jdc_reviews_commentary_etc.bib", ["review"]),
    ("jdc_books.bib", ["book"]),
    ("jdc_published_abstracts.bib", ["abstract"]),
    ("jdc-under-review-in-prep.bib", ["preprint"]),
]

OUTPUT = Path("jdc_master.bib")


def download_file(filename):
    """Download a bibliography file from GitHub."""
    url = BASE_URL + filename

    print(f"Downloading {filename} ...")

    with urlopen(url) as response:
        return response.read().decode("utf-8")


def remove_markdown_fences(text):
    """Remove Markdown code fences if present."""
    lines = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == "```bibtex":
            continue

        if stripped == "```":
            continue

        lines.append(line)

    return "\n".join(lines)


def split_entries(text):
    """Split a BibTeX file into individual entries."""
    entries = []

    i = 0
    n = len(text)

    while i < n:
        # Find the next BibTeX entry.
        match = re.search(r"@[A-Za-z]+\s*\{", text[i:])

        if not match:
            break

        start = i + match.start()
        brace_start = text.find("{", start)

        if brace_start == -1:
            raise ValueError(
                f"Could not find opening brace for entry near "
                f"character {start}"
            )

        depth = 0
        j = brace_start

        while j < n:
            char = text[j]

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:
                    entries.append(
                        text[start:j + 1].strip()
                    )
                    i = j + 1
                    break

            j += 1

        else:
            raise ValueError(
                f"Unbalanced braces in BibTeX entry beginning near "
                f"character {start}"
            )

    return entries


def get_key(entry):
    """Extract the BibTeX citation key."""
    match = re.match(
        r"@\w+\s*\{\s*([^,\s]+)\s*,",
        entry,
        flags=re.IGNORECASE
    )

    if not match:
        raise ValueError(
            "Could not determine BibTeX key from entry:\n\n"
            + entry[:500]
        )

    return match.group(1)


def get_year_value(entry):
    """Extract the year field."""
    match = re.search(
        r"\byear\s*=\s*\{([^{}]*)\}",
        entry,
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    return match.group(1).strip().lower()


def get_existing_keywords(entry):
    """Return existing keywords as a list."""
    match = re.search(
        r"(\bkeywords\s*=\s*\{)([^{}]*)(\})",
        entry,
        flags=re.IGNORECASE
    )

    if not match:
        return []

    return [
        keyword.strip()
        for keyword in match.group(2).split(",")
        if keyword.strip()
    ]


def add_keywords(entry, new_keywords):
    """Add new keywords while preserving existing ones."""
    existing = get_existing_keywords(entry)

    combined = []

    for keyword in existing + new_keywords:
        keyword = keyword.strip()

        if keyword and keyword.lower() not in [
            x.lower() for x in combined
        ]:
            combined.append(keyword)

    keyword_string = ", ".join(combined)

    keyword_match = re.search(
        r"\bkeywords\s*=\s*\{[^{}]*\}\s*,?",
        entry,
        flags=re.IGNORECASE
    )

    if keyword_match:
        replacement = f"keywords = {{{keyword_string}}},"

        return (
            entry[:keyword_match.start()]
            + replacement
            + entry[keyword_match.end():]
        )

    position = entry.rfind("}")

    if position == -1:
        raise ValueError(
            "Could not find closing brace in entry."
        )

    insertion = f"\n  keywords = {{{keyword_string}}},"

    return (
        entry[:position]
        + insertion
        + "\n"
        + entry[position:]
    )


def add_sortyear(entry):
    """Add a numeric sortyear for chronological sorting."""
    year = get_year_value(entry)

    match = re.search(r"\b(19|20)\d{2}\b", year)

    if match:
        sortyear = match.group(0)
    else:
        sortyear = "0000"

    pattern = re.compile(
        r"\bsortyear\s*=\s*\{[^{}]*\}\s*,?",
        flags=re.IGNORECASE
    )

    replacement = f"  sortyear = {{{sortyear}}},"

    if pattern.search(entry):
        return pattern.sub(
            replacement,
            entry,
            count=1
        )

    position = entry.rfind("}")

    if position == -1:
        raise ValueError(
            "Could not find closing brace in entry."
        )

    return (
        entry[:position]
        + "\n"
        + replacement
        + "\n"
        + entry[position:]
    )


def classify_entry(filename, entry):
    """Determine the publication type and status tags."""
    for source_file, category_keywords in FILES:
        if filename != source_file:
            continue

        keywords = list(category_keywords)

        if filename == "jdc-under-review-in-prep.bib":
            year = get_year_value(entry)

            if "under review" in year:
                keywords.append("under-review")

            elif "in prep" in year or "in preparation" in year:
                keywords.append("in-preparation")

        return keywords

    raise ValueError(
        f"Unknown source bibliography: {filename}"
    )


def normalize_entry(entry):
    """Normalize whitespace for duplicate checking."""
    return re.sub(
        r"\s+",
        " ",
        entry.strip()
    )


def main():
    print()
    print("Creating jdc_master.bib")
    print("=" * 60)
    print()

    all_entries = []
    keys = {}
    duplicate_count = 0

    # Read each source bibliography.
    for filename, _ in FILES:
        text = download_file(filename)
        text = remove_markdown_fences(text)
        entries = split_entries(text)

        print(
            f"  Found {len(entries):4d} entries in {filename}"
        )

        for entry in entries:
            key = get_key(entry)
            normalized = normalize_entry(entry)

            if key in keys:
                previous_file, previous_entry = keys[key]

                if normalized == previous_entry:
                    duplicate_count += 1
                    print(
                        f"  Duplicate identical entry ignored: {key}"
                    )
                    continue

                print()
                print("ERROR: Conflicting BibTeX key found!")
                print()
                print(f"  Key:        {key}")
                print(f"  First file: {previous_file}")
                print(f"  Also in:    {filename}")
                print()
                print(
                    "The entries have the same key but different "
                    "contents."
                )
                print()

                sys.exit(1)

            keywords = classify_entry(filename, entry)
            entry = add_keywords(entry, keywords)
            entry = add_sortyear(entry)

            keys[key] = (
                filename,
                normalized
            )

            all_entries.append(
                (filename, key, entry)
            )

    # Write the master bibliography.
    with OUTPUT.open("w", encoding="utf-8") as f:
        f.write(
            "% ======================================================\n"
            "% jdc_master.bib\n"
            "%\n"
            "% Master publication database for Jonathan D. Cohen.\n"
            "% Generated from the bibliography files used by jdc_cv.tex.\n"
            "%\n"
            "% Tags:\n"
            "%   article, review, book, abstract, preprint\n"
            "%   under-review, in-preparation\n"
            "% ======================================================\n\n"
        )

        current_source = None

        for source_file, key, entry in all_entries:
            if source_file != current_source:
                if current_source is not None:
                    f.write("\n")

                f.write(
                    "% --------------------------------------------------\n"
                )
                f.write(
                    f"% Source: {source_file}\n"
                )
                f.write(
                    "% --------------------------------------------------\n\n"
                )

                current_source = source_file

            f.write(entry)
            f.write("\n\n")

    print()
    print("=" * 60)
    print(f"Successfully created: {OUTPUT}")
    print(f"Total entries: {len(all_entries)}")
    print(f"Duplicate entries ignored: {duplicate_count}")
    print("=" * 60)
    print()

    counts = {}

    for source_file, _, _ in all_entries:
        counts[source_file] = counts.get(source_file, 0) + 1

    print("Entries by source:")

    for source_file, count in counts.items():
        print(f"  {source_file:40s} {count:4d}")

    print()


if __name__ == "__main__":
    main()
