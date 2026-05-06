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

Install once:
  pip install pdfplumber
"""

import re
import csv
import pdfplumber
from groq import Groq  #  We will be conenecting to Groq's API
import os
import json
import io
import shutil
from dataclasses import dataclass
from collections import defaultdict

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    from PIL import Image
except ImportError:
    Image = None


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
            for page_num, page in enumerate(file.pages):
                # Some PDF pages may fail to extract text cleanly, so we skip blanks.
                text = page.extract_text()
                # If a page has little or no selectable text, try OCR to read
                # words that may only exist inside an image.
                if self._needs_ocr(text):
                    text = self.ocr_page(page_num) or text
                if text is None:
                    continue
                my_text.append(text)

        return "\n".join(my_text)

    def extract_pages(self) -> list[str]:
        """Return a list of strings, one per page."""
        with pdfplumber.open(self.filepath) as file:
            my_text = []
            for page in file.pages:
                # Keep each page separate in case we want page-by-page processing later.
                text = page.extract_text()
                if text is None:
                    continue
                my_text.append(text)
        return my_text

    @staticmethod
    def _needs_ocr(text: str | None) -> bool:
        """Return True when extracted text is missing or too small to be useful."""
        return not text or len(text.strip()) < 20

    @staticmethod
    def ocr_available() -> bool:
        """Return True if the OCR libraries and Tesseract binary are available."""
        return (
            fitz is not None
            and pytesseract is not None
            and Image is not None
            and shutil.which("tesseract") is not None
        )

    def ocr_page(self, page_num: int) -> str:
        """Render one PDF page as an image and read it with OCR."""
        if not self.ocr_available():
            return ""

        doc = fitz.open(self.filepath)
        try:
            page = doc.load_page(page_num)
            # Render at a higher resolution so OCR can read slide text more reliably.
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_bytes = pixmap.tobytes("png")
        finally:
            doc.close()

        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)

    @staticmethod
    def clean(text: str) -> str:
        """Remove extra whitespace, page numbers, and junk characters."""
        # Collapse newlines/tabs/multiple spaces into single spaces so the AI
        # sees one cleaner block of lecture text.
        remove_newlines = re.sub(r"\s+" , " ", text)
        strip_whitespace = remove_newlines.strip()
        # Remove standalone numbers that are likely page numbers.
        page_numbers = re.sub(r"\b\d{1,3}\b", "", strip_whitespace)
        return page_numbers


class AIExtractor:
    """Uses the Groq API to turn lecture text into study flashcards."""

    def __init__(self, topic: str):
        self.topic = topic

    def extract(self, text: str) -> list[Flashcard]:
        # The prompt asks the model to return structured JSON so we can parse it
        # directly into Flashcard objects.
        prompt = f"""Given the following lecture text about {self.topic}, extract all key concepts that are important for studying and comprehension. For each concept, provide:

        - A clear, concise term (the concept name)
        - A precise definition written in your own words

        Return ONLY a JSON object in this format, no other text:
        {{
            "flashcards": [
                {{
                    "term": "Concept name",
                    "definition": "Clear and concise explanation of the concept"
                }}
            ]
        }}

        Guidelines:
        - Only include meaningful, non-trivial concepts
        - Ensure definitions are specific to the lecture context
        - Avoid duplicate or overlapping concepts
        - Keep definitions concise but informative (1-3 sentences)

        Lecture text:
        {text}"""

        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt[:40000]}],
            max_tokens=4096,
        )

        # Models sometimes wrap JSON in extra text, so we grab only the JSON
        # object between the first "{" and the last "}".
        text = response.choices[0].message.content
        text = text[text.find("{"):text.rfind("}") + 1]
        data = json.loads(text)["flashcards"]
        my_flashcards = []
        for flashcard in data:
            my_flashcards.append(Flashcard(flashcard["term"], flashcard["definition"]))
        # Filter out incomplete or too-short cards before exporting.
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
        # Group cards by lowercase front so "DNA" and "dna" count as duplicates.
        group_cards[card.front.lower()].append(card)
    for c in group_cards:
        # If duplicates exist, keep the version with the most detailed answer.
        winner = max(group_cards[c], key=lambda x: len(x.back))
        deduplicated.append(winner)

    return deduplicated


class CSVExporter:
    """Writes flashcards to a .csv file ready for Anki or Quizlet import."""

    def __init__(self, output_path: str):
        self.output_path = output_path

    def export(self, cards: list[Flashcard]) -> None:
        """Write each card as a row: front, back"""
        # csv.writer handles commas/quotes safely for Anki and Quizlet imports.
        with open(self.output_path, "w") as f:
            writer = csv.writer(f)
            writer.writerow(["front", "back"])
            for c in cards:
                writer.writerow([c.front, c.back])
            
        print(f"Exported {len(cards)} cards to {self.output_path}")


class FlashcardGenerator:
    """Wires all the pieces together."""

    def __init__(self, pdf_path: str, output_path: str = "flashcards.csv", topic: str = ""):
        self.pdf_path = pdf_path
        self.output_path = output_path
        self.topic = topic


    def run(self) -> None:
        print(f"\nReading: {self.pdf_path}")

        # 1. Read the PDF and flatten it into raw text.
        reader = PDFReader(self.pdf_path)
        raw_text = reader.extract_text()

        # 2. Clean the text before sending it to the AI model.
        clean_text = PDFReader.clean(raw_text)
        print(clean_text[:500])

        # 3. Ask the model to turn the lecture into flashcards.
        ai_cards = AIExtractor(self.topic).extract(clean_text)

        # 4. Remove repeated concepts so the export stays clean.
        deduplicated = deduplicate(ai_cards)
        print(len(deduplicated))

        # 5. Export the final cards to CSV.
        CSVExporter(self.output_path).export(deduplicated)

        print(f"\nDone! Open '{self.output_path}' and import into Anki or Quizlet.")


def main() -> None:
    # Collect the minimum input needed to run the generator from the terminal.
    pdf_path = input("Enter path to your lecture PDF: ").strip().strip("'\"")

    topic = input("What is this lecture about? (e.g. 'binary search', 'photosynthesis'): ").strip()

    output = input("Output filename? [default: flashcards.csv]: ").strip()
    if not output:
        output = "flashcards.csv"

    try:
        if not PDFReader.ocr_available():
            print("Note: OCR fallback is unavailable. Image-only PDF pages may not extract well.")
        generator = FlashcardGenerator(pdf_path, output, topic)
        generator.run()
    except FileNotFoundError:
        print(f"Error: '{pdf_path}' not found.")
    except Exception as e:
        # Catch-all so the script fails gracefully instead of crashing with a traceback.
        print(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
