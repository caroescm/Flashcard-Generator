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
import anthropic
import os
import json
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
        with open(self.output_path, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["front", "back"])
            for c in cards:
                writer.writerow([c.front, c.back])
            
        print(f"Exported {len(cards)} cards to {self.output_path}")


class FlashcardGenerator:
    """Wires all the pieces together."""

    def __init__(self, pdf_path: str, output_path: str = "flashcards.csv"):
        self.pdf_path    = pdf_path
        self.output_path = output_path

    def run(self) -> None:
        print(f"\nReading: {self.pdf_path}")

        reader = PDFReader(self.pdf_path)
        raw_text = reader.extract_text()
        clean_text = PDFReader.clean(raw_text)
        print(clean_text[:500])

        deduplicated = deduplicate(ai_cards)
        print(len(deduplicated))

        # Step 4: export
        CSVExporter(self.output_path).export(deduplicated)

        print(f"\nDone! Open '{self.output_path}' and import into Anki or Quizlet.")


def main() -> None:
    pdf_path = input("Enter path to your lecture PDF: ").strip().strip("'\"")

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
