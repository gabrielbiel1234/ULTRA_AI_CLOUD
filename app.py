import os
import time
import logging
import requests
import base64

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")

PASSWORD = os.environ.get("APP_PASSWORD", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
IMAGE_MODEL = os.environ.get(
    "IMAGE_MODEL",
    "gemini-2.5-flash-image"
)

http = requests.Session()

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ULTRA AI CLOUD TURBO</title>

<style>
body {
    font-family: Arial, sans-serif;
    background: #101827;
    color: white;
    margin: 0;
    padding: 25px;
}
main {
    max-width: 800px;
    margin: auto;
}
h1 { color: #55d6be; }
h2 { color: #55d6be; }
textarea {
    width: 100%;
    height: 120px;
    padding: 14px;
    margin: 10px 0;
    border-radius: 8px;
    box-sizing: border-box;
    font-size: 16px;
}
button {
    background: #16a085;
    color: white;
    border: 0;
    padding: 13px 22px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
    margin: 5px 3px;
}
button:disabled {
    opacity: 0.6;
    cursor: wait;
}
.card {
    background: #1e293b;
    padding: 20px;
    border-radius: 12px;
    margin-top: 20px;
}
.resposta {
    white-space: pre-wrap;
    line-height: 1.6;
}
.imagem {
    width: 100%;
    max-width: 700px;
    border-radius: 12px;
    margin-top: 15px;
}
.download {
    display: inline-block;
    background: #2563eb;
    color: white;
    padding: 12px 18px;
    border-radius: 8px;
