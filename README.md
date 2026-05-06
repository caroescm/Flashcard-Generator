# Flashcard Generator

Upload a lecture PDF and instantly get AI-generated flashcards. Edit them, download as CSV for Anki or Quizlet, or practice directly in the browser.

## Features

- AI-powered flashcard generation from any lecture PDF
- Inline editing — add, delete, or tweak cards before exporting
- Download as CSV (compatible with Anki and Quizlet)
- Built-in flip-card practice mode
- Free to use — powered by Groq

## Live Demo

[flashcard-generator.onrender.com](https://flashcard-generator-xu18.onrender.com/)

## How to Use

1. Upload your lecture PDF
2. Enter the topic (e.g. "binary search", "photosynthesis")
3. Click **Generate Flashcards**
4. Edit the cards as needed
5. Download CSV or practice in the browser

### Importing to Anki
1. Download the CSV
2. Open Anki → File → Import → select the file
3. Set separator to comma, map Field 1 = Front, Field 2 = Back

### Importing to Quizlet
1. Download the CSV
2. Quizlet → Create → Import
3. Set "Between term and definition" = comma, "Between rows" = newline

## Running Locally

```bash
git clone https://github.com/caroescm/Flashcard-Generator.git
cd Flashcard-Generator
pip3 install -r requirements.txt
export GROQ_API_KEY="your-key-here"
python3 app.py
```

Then open `http://localhost:8080`.

Get a free Groq API key at [console.groq.com/keys](https://console.groq.com/keys).

### OCR support for image-based slides

If a PDF page has little or no selectable text, the app can fall back to OCR to
read text from slide images or scanned pages.

Install the Python packages from `requirements.txt`, then make sure the
`tesseract` command is also installed on your system. If Tesseract is missing,
the app still works for normal text-based PDFs, but OCR fallback will be skipped.

## Deploying to Render

1. Fork this repo
2. Create a new Web Service on [render.com](https://render.com) and connect your fork
3. Add `GROQ_API_KEY` as an environment variable in the Render dashboard
4. Deploy

## Tech Stack

- Python, Flask
- Groq API (Llama 3.3 70B)
- pdfplumber
- Vanilla HTML/CSS/JS

## License

MIT
