"""
GEMINI-SERVICE
Backend to interact with the Google Gemini API

jck 2025
"""

from flask import (
    Flask,
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

from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = os.getenv("GEMINI_MODEL_TYPE", "gemini-1.5-flash-latest")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

chat_session = client.chats.create(model=MODEL_NAME)

app = Flask(__name__, static_folder='static', template_folder='templates')

cors_origin_env = os.getenv("CORS_ORIGIN")

if cors_origin_env:
    print(f"CORS enabled for origin: {cors_origin_env}")
    CORS(app, resources={r"/*": {"origins": [cors_origin_env]}})
else:
    print("CORS enabled for all origins (CORS_ORIGIN not defined)")
    CORS(app)

next_message = ""
next_image = None

def allowed_file(filename):
    _, ext = os.path.splitext(filename)
    return ext.lstrip('.').lower() in ALLOWED_EXTENSIONS
    

@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Receives an image file (PNG, JPG, JPEG)
    and stores it temporarily to be used
    in the subsequent /stream request with a text message.
    """
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
    """
    Returns a simple JSON response indicating
    the backend service is running and healthy.
    """
    return jsonify({"status": "healthy", "message": "Gemini API backend running"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    """
    Accepts a text message from the user and stores it temporarily.
    This message will then be processed by the /stream endpoint
    to get the Gemini response, maintaining conversation history.
    """
    global next_message
    next_message = request.json["message"]
    return jsonify(success=True)


@app.route("/stream", methods=["GET"])
def stream():
    """
    Initiates a Server-Sent Events (SSE) stream
    to provide real-time responses from the Gemini API.
    It uses the last text message from /chat
    and/or the last uploaded image from /upload.
    This endpoint maintains the chat session history.
    """
    def generate():
        global next_message
        global next_image

        parts = []
        if next_image is not None:
            img_byte_arr = io.BytesIO()
            next_image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            parts.append(types.Part.from_bytes(data=img_byte_arr, mime_type='image/png'))
            next_image = None
        
        if next_message:
            parts.append(next_message)
            next_message = ""

        if not parts:
            yield "data: No message or image to process.\n\n"
            return
            
        response_stream = chat_session.send_message_stream(parts)

        for chunk in response_stream:
            if hasattr(chunk, 'text'):
                yield f"data: {chunk.text}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


@app.route('/generate_text', methods=['POST'])
def generate_text_api():
    """
    Sends a prompt directly to the Gemini API to get a text response.
    This route does not use the ongoing chat session history
    maintained by /chat and /stream.
    """
    try:
        data = request.get_json()
        prompt_message = data.get('prompt')

        if not prompt_message:
            return jsonify({"error": "No prompt provided"}), 400
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt_message],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return jsonify({"generated_text": response.text})
    except Exception as e:
        print(f"Error during generate_text_api: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)