"""
GEMINI-SERVICE
Backend to interact with the Google Gemini API

jck 2025
"""


from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
import io
from dotenv import load_dotenv
import os

import google.generativeai as genai


load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_TYPE"))
chat_session = model.start_chat()

app = Flask(__name__, static_folder='static', template_folder='templates')

cors_origin_env = os.getenv("CORS_ORIGIN")

if cors_origin_env:
    print(f"CORS enabled for origin: {cors_origin_env}")
    CORS(app, resources={r"/*": {"origins": [cors_origin_env]}})
else:
    print("CORS enabled for all origins (CORS_ORIGIN not defined)")
    CORS(app)


next_message = ""
next_image = ""


def allowed_file(filename):
    _, ext = os.path.splitext(filename)
    return ext.lstrip('.').lower() in ALLOWED_EXTENSIONS


@app.route("/upload", methods=["POST"])
def upload_file():

    global next_image

    if "file" not in request.files:
        return jsonify(success=False, message="No file part")

    file = request.files["file"]

    if file.filename == "":
        return jsonify(success=False, message="No selected file")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        file_stream = io.BytesIO(file.read())
        file_stream.seek(0)
        next_image = Image.open(file_stream)

        return jsonify(
            success=True,
            message="File uploaded successfully and added to the conversation",
            filename=filename,
        )
    return jsonify(success=False, message="File type not allowed")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "healthy", "message": "Gemini API backend running"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    global next_message
    next_message = request.json["message"]
    print(chat_session.get_history())

    return jsonify(success=True)


@app.route("/stream", methods=["GET"])
def stream():
    def generate():
        global next_message
        global next_image

        parts = []
        if next_image != "":
            parts.append(next_image)
            next_image = ""
        if next_message != "":
            parts.append(next_message)
            next_message = ""

        if not parts:
            yield "data: No message or image to process.\n\n"
            return
            
        response_stream = chat_session.send_message(parts, stream=True)

        for chunk in response_stream:
            if hasattr(chunk, 'text'):
                yield f"data: {chunk.text}\n\n"
            # else:
            #     print(f"Chunk without text: {chunk}") # for debug

    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream")
                    
                    
@app.route('/generate_text', methods=['POST'])
def generate_text_api():
    try:
        data = request.get_json()
        prompt_message = data.get('prompt')

        if not prompt_message:
            return jsonify({"error": "No prompt provided"}), 400
        
        response = model.generate_content(
            [prompt_message],
            generation_config={"response_mime_type": "application/json"}
        )
        return jsonify({"generated_text": response.text})
    except Exception as e:
        print(f"Error during generate_text_api: {e}")
        return jsonify({"error": str(e)}), 500
        
        
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)