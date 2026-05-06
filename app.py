import os
import io
import csv
import tempfile
from flask import Flask, request, jsonify, Response, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flashcard_generator import PDFReader, AIExtractor, deduplicate

app = Flask(__name__)

limiter = Limiter(get_remote_address, app=app, default_limits=[])

@app.errorhandler(429)
def rate_limit_exceeded(e):
    return jsonify({"error": "You've reached the limit of 3 PDFs per day. Come back tomorrow!"}), 429


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
@limiter.limit("3 per day")
def generate():
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
        cards = deduplicate(AIExtractor(topic).extract(clean_text))
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
