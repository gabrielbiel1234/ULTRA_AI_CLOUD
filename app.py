import os
import requests
from flask import Flask, request, redirect, session, render_template_string

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-antes-de-publicar")

PASSWORD = os.environ.get("APP_PASSWORD", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ULTRA AI CLOUD</title>
<style>
body{font-family:Arial;background:#101827;color:white;margin:0;padding:25px}
main{max-width:800px;margin:auto}
h1{color:#55d6be}
textarea,input{width:100%;padding:14px;margin:10px 0;
border-radius:8px;border:1px solid #526078;box-sizing:border-box}
textarea{height:130px}
button{background:#16a085;color:white;border:0;padding:13px 22px;
border-radius:8px;cursor:pointer;font-size:16px}
.card{background:#1e293b;padding:20px;border-radius:12px;margin-top:20px}
.resposta{white-space:pre-wrap;line-height:1.6}
</style>
</head>
<body>
<main>
<h1>ULTRA AI CLOUD</h1>
<p>Seu assistente de inteligência artificial</p>
<div class="card">
<form method="post" action="/perguntar">
<textarea name="pergunta" placeholder="Digite o que deseja fazer..." required></textarea>
<button type="submit">Perguntar à IA</button>
</form>
</div>
{% if resposta %}
<div class="card">
<h2>Resposta</h2>
<div class="resposta">{{ resposta }}</div>
</div>
{% endif %}
{% if erro %}
<div class="card">{{ erro }}</div>
{% endif %}
</main>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def inicio():
    if PASSWORD and not session.get("autorizado"):
        return """
        <h2>ULTRA AI CLOUD</h2>
        <form method="post" action="/entrar">
        <input type="password" name="senha" placeholder="Senha de acesso">
        <button>Entrar</button>
        </form>
        """
    return render_template_string(HTML)

@app.route("/entrar", methods=["POST"])
def entrar():
    if request.form.get("senha") == PASSWORD and PASSWORD:
        session["autorizado"] = True
        return redirect("/")
    return "Senha incorreta. Volte e tente novamente.", 401

@app.route("/perguntar", methods=["POST"])
def perguntar():
    if PASSWORD and not session.get("autorizado"):
        return redirect("/")

    pergunta = request.form.get("pergunta", "").strip()
    if not pergunta:
        return redirect("/")

    if not GEMINI_KEY:
        return render_template_string(
            HTML, erro="Configure a chave GEMINI_API_KEY no painel de hospedagem."
        )

    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + MODEL + ":generateContent"
        )
        resultado = requests.post(
            url,
            params={"key": GEMINI_KEY},
            json={
                "contents": [{"parts": [{"text": pergunta}]}]
            },
            timeout=60
        )
        resultado.raise_for_status()
        dados = resultado.json()
        resposta = dados["candidates"][0]["content"]["parts"][0]["text"]
        return render_template_string(HTML, resposta=resposta)

    except Exception:
        return render_template_string(
            HTML,
            erro="Não foi possível consultar a IA. Verifique a chave e tente novamente."
        )

@app.route("/health")
def health():
    return {"status": "online", "app": "ULTRA AI CLOUD"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
