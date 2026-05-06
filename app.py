import os
import io
import csv
import tempfile
from collections import defaultdict
from datetime import date
from flask import Flask, request, jsonify, Response, render_template
from flashcard_generator import PDFReader, AIExtractor, deduplicate

app = Flask(__name__)

DAILY_LIMIT = 3
_usage = defaultdict(dict)
MIN_TEXT_LENGTH = 80


def _today():
    return str(date.today())


def _get_count(ip):
    return _usage[ip].get(_today(), 0)


def _increment(ip):
    today = _today()
    _usage[ip][today] = _usage[ip].get(today, 0) + 1


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/remaining")
def remaining():
    count = _get_count(request.remote_addr)
    return jsonify({"remaining": DAILY_LIMIT - count, "limit": DAILY_LIMIT})


@app.route("/generate", methods=["POST"])
def generate():
    ip = request.remote_addr
    if _get_count(ip) >= DAILY_LIMIT:
        return jsonify({"error": "You've reached the limit of 3 PDFs per day. Come back tomorrow!"}), 429

    topic = request.form.get("topic", "")
    pdf_file = request.files.get("pdf")

    if not pdf_file:
        return jsonify({"error": "PDF file required"}), 400

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw_text = PDFReader(tmp_path).extract_text()
        clean_text = PDFReader.clean(raw_text)
        if len(clean_text.strip()) < MIN_TEXT_LENGTH:
            if not PDFReader.ocr_available():
                return jsonify({
                    "error": (
                        "This PDF does not appear to contain enough selectable text. "
                        "It may be image-based, and OCR is not installed in the current environment."
                    )
                }), 422
            return jsonify({
                "error": (
                    "I could not extract enough readable text from this PDF. "
                    "Try a clearer PDF or one with selectable text."
                )
            }), 422

        cards = deduplicate(AIExtractor(topic).extract(clean_text))
        if not cards:
            return jsonify({
                "error": (
                    "The PDF text was read, but no strong flashcards were generated. "
                    "Try a more specific topic or a PDF with clearer text."
                )
            }), 422

        _increment(ip)
        return jsonify([{"front": c.front, "back": c.back} for c in cards])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp_path)


@app.route("/export", methods=["POST"])
def export():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array of flashcards"}), 400

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["front", "back"])
    for card in data:
        writer.writerow([card.get("front", ""), card.get("back", "")])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=flashcards.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=8080)
