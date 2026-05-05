"""
Flashcard Generator from PDFs
==============================
Feed it a lecture PDF → exports a .csv you can import into Anki or Quizlet.

How Anki import works:
  1. Run this script → get flashcards.csv
  2. Open Anki → File → Import → select flashcards.csv
  3. Set separator to comma, map Field 1 = Front, Field 2 = Back → done!

How Quizlet import works:
  1. Run this script → get flashcards.csv
  2. Quizlet → Create → Import → paste contents of flashcards.csv
  3. Set "Between term and definition" = comma, "Between rows" = newline → done!

Concepts practiced:
  - OOP (classes, __init__, methods)
  - Regex (re module) — for finding definitions and key terms
  - File I/O — reading PDFs, writing CSV
  - List comprehensions + filter/map
  - defaultdict
  - Error handling (try/except)
  - String methods

Install once:
  pip install pdfplumber
"""

import re
import csv
import pdfplumber
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Flashcard:
    """One flashcard: a front (term) and a back (definition)."""
    front: str
    back: str

    def is_valid(self) -> bool:
        """Return True if both sides are non-empty and back has >= 4 words."""
        return self.front and self.back and len(self.back.split()) >= 4


class PDFReader:
    """Extracts and cleans text from a PDF file."""

    def __init__(self, filepath: str):
        self.filepath = filepath

    def extract_text(self) -> str:
        """Return all text from the PDF as one big string."""
        with pdfplumber.open(self.filepath) as file:
            my_text = []
            for page in file.pages:
                text = page.extract_text()
                if text is None:
                    continue
                my_text.append(text)
        
        return "\n".join(my_text)

    def extract_pages(self) -> list[str]:
        """Return a list of strings, one per page."""
        with pdfplumber.open(self.filepath) as file:
            my_text = []
            for page in file.pages:
                text = page.extract_text()
                if text is None:
                    continue
                my_text.append(text)
        return my_text

    @staticmethod
    def clean(text: str) -> str:
        """Remove extra whitespace, page numbers, and junk characters."""
        remove_newlines = re.sub(r"\s+" , " ", text)
        strip_whitespace = remove_newlines.strip()
        page_numbers = re.sub(r"\b\d{1,3}\b", "", strip_whitespace)
        return page_numbers

class DefinitionExtractor:
    """
    Strategy A: regex that catches sentences like:
      "Recursion is a function that calls itself."
      "A lambda is an anonymous function."
      "Polymorphism refers to the ability to..."
    """

    # Regex pattern — finds: <Term> <is/are/means/refers to> <definition>
    PATTERN = re.compile(
        r"([A-Z][a-zA-Z\s]{1,40}?)"          # Term: starts with capital, 2-40 chars
        r"\s+(?:is|are|means|refers to|"       # linking verb
        r"is defined as|is called|stands for)" #   (more variants)
        r"\s+(.{15,200}?)"                     # Definition: 15-200 chars
        r"(?:[.!?]|$)",                        # ends at punctuation or line end
        re.MULTILINE
    )

    def extract(self, text: str) -> list[Flashcard]:
        """Run the regex on text and return a list of Flashcard objects."""
        def_tuples = self.PATTERN.findall(text)
        my_flashcards = []
        for item, definition in def_tuples:
            clean_concept = item.strip()
            clean_def= definition.strip()
            my_flashcards.append(Flashcard(clean_concept, clean_def))
        clean_ver = list(filter(lambda x: x.is_valid(), my_flashcards))
        return clean_ver


class BulletExtractor:
    """
    Strategy B: finds patterns like:
      "Term: some explanation here"
      "- Term — some explanation here"
      "Term → some explanation here"
    """

    PATTERN = re.compile(
        r"^[\-\•\*]?\s*"              # optional bullet character
        r"([A-Z][a-zA-Z\s()]{1,40}?)" # Term
        r"\s*(?::|\—|→|–)\s*"         # separator  : — → –
        r"(.{15,300})",                # Definition
        re.MULTILINE
    )

    def extract(self, text: str) -> list[Flashcard]:
        """Run the regex and return valid Flashcard objects."""
        # TODO: same approach as DefinitionExtractor.extract()
        #       use self.PATTERN.findall(text)
        #       wrap each match in a Flashcard, filter with is_valid()
        def_tuples = self.PATTERN.findall(text)
        my_flashcards = []
        for item, definition in def_tuples:
            clean_concept = item.strip()
            clean_def= definition.strip()
            my_flashcards.append(Flashcard(clean_concept, clean_def))
        clean_ver = list(filter(lambda x: x.is_valid(), my_flashcards)) 
        
        return clean_ver

def deduplicate(cards: list[Flashcard]) -> list[Flashcard]:
    """
    Remove duplicate flashcards.
    Two cards are duplicates if their fronts are the same (case-insensitive).
    When duplicates exist, keep the one with the longer back (more info).
    """
    group_cards = defaultdict(list)
    deduplicated = []
    for card in cards:
        group_cards[card.front.lower()].append(card)
    for c in group_cards:
        winner = max(group_cards[c], key=lambda x: len(x.back))
        deduplicated.append(winner)

    return deduplicated


class CSVExporter:
    """Writes flashcards to a .csv file ready for Anki or Quizlet import."""

    def __init__(self, output_path: str):
        self.output_path = output_path

    def export(self, cards: list[Flashcard]) -> None:
        """Write each card as a row: front, back"""
        # TODO: open self.output_path for writing with csv.writer
        #       write a header row: ["front", "back"]
        #       loop through cards and write each as [card.front, card.back]
        #       print how many cards were exported when done
        pass


# ─────────────────────────────────────────────────────────────────────────────
# PART 6 — Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class FlashcardGenerator:
    """Wires all the pieces together."""

    def __init__(self, pdf_path: str, output_path: str = "flashcards.csv"):
        self.pdf_path    = pdf_path
        self.output_path = output_path

    def run(self) -> None:
        print(f"\nReading: {self.pdf_path}")

        # Step 1: extract text
        reader = PDFReader(self.pdf_path)
        # TODO: call reader.extract_text() and store in raw_text
        # TODO: call PDFReader.clean() on raw_text and store in clean_text

        # Step 2: run both extractors
        def_cards    = DefinitionExtractor().extract(clean_text)
        bullet_cards = BulletExtractor().extract(clean_text)

        print(f"  Definition pattern matched : {len(def_cards)} cards")
        print(f"  Bullet/colon pattern matched: {len(bullet_cards)} cards")

        # Step 3: combine + deduplicate
        # TODO: combine def_cards and bullet_cards into one list
        # TODO: call deduplicate() on the combined list
        # TODO: print how many unique cards remain

        # Step 4: export
        # TODO: create a CSVExporter and call .export() with the deduplicated cards

        print(f"\nDone! Open '{self.output_path}' and import into Anki or Quizlet.")


# ─────────────────────────────────────────────────────────────────────────────
# PART 7 — Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    pdf_path = input("Enter path to your lecture PDF: ").strip()

    output = input("Output filename? [default: flashcards.csv]: ").strip()
    if not output:
        output = "flashcards.csv"

    try:
        generator = FlashcardGenerator(pdf_path, output)
        generator.run()
    except FileNotFoundError:
        print(f"Error: '{pdf_path}' not found.")
    except Exception as e:
        print(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
