import os
import io
import csv
import tempfile
from flask import Flask, request, jsonify, Response, render_template
from flashcard_generator import PDFReader, AIExtractor, deduplicate

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    api_key = request.form.get("api_key")
    topic = request.form.get("topic", "")
    pdf_file = request.files.get("pdf")

    if not api_key:
        return jsonify({"error": "Gemini API key required"}), 400
    if not pdf_file:
        return jsonify({"error": "PDF file required"}), 400

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        raw_text = PDFReader(tmp_path).extract_text()
        clean_text = PDFReader.clean(raw_text)
        cards = deduplicate(AIExtractor(topic, api_key=api_key).extract(clean_text))
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
