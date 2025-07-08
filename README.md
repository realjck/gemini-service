# gemini-service

This project provides a secure Python backend using Flask and Gunicorn to interact with the Google Gemini API. It's designed to be deployed as an API service, allowing your frontend applications to communicate with Gemini without directly exposing your API key.

## Installation

### Build image :

```bash
docker build -t gemini-service .
```


### Run container :

```bash
docker run -d --restart always -p 2222:5000 --name gemini-service-container \
  -e GOOGLE_API_KEY="YOUR-API-KEY" \
  -e GEMINI_MODEL_TYPE="gemini-2.5-flash-preview-04-17" \
  -e CORS_ORIGIN="https://your-domain.com" \
  gemini-service
```

- Personnalize with the GEMINI_MODEL_TYPE you want to use.
- CORS_ORIGIN is optional, if not specified it will allow all origins (*)

## API Routes Overview

### GET /

- Purpose: Health check endpoint.

- Description: Returns a simple JSON response indicating the backend service is running and healthy.

- Response: {"status": "healthy", "message": "Gemini API backend running"}

### POST /upload

- Purpose: Upload an image for multi-modal chat.

- Description: Receives an image file (PNG, JPG, JPEG) and stores it temporarily to be used in the subsequent /stream request with a text message.

- Request Body: multipart/form-data with a file field named file.

### POST /chat

- Purpose: Send a text message to the Gemini chat session.

- Description: Accepts a text message from the user and stores it temporarily. This message will then be processed by the /stream endpoint to get the Gemini response, maintaining conversation history.

- Request Body: application/json with a key message containing the user's text.

### GET /stream

- Purpose: Stream the Gemini API's response.

- Description: Initiates a Server-Sent Events (SSE) stream to provide real-time responses from the Gemini API. It uses the last text message from /chat and/or the last uploaded image from /upload. This endpoint maintains the chat session history.

### POST /generate_text

- Purpose: Generate a single, stateless text response.

- Description: Sends a prompt directly to the Gemini API to get a text response. This route does not use the ongoing chat session history maintained by /chat and /stream.

- Request Body: application/json with a key prompt containing the text query.