
import os
import time
import logging
import requests

from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template_string
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "troque-esta-chave-antes-de-publicar"
)

PASSWORD = os.environ.get("APP_PASSWORD", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Reutiliza conexões HTTP
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
textarea {
    width: 100%;
    height: 130px;
    padding: 14px;
    margin: 10px 0;
    border-radius: 8px;
    box-sizing: border-box;
}
button {
    background: #16a085;
    color: white;
    border: 0;
    padding: 13px 22px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
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
#status {
    color: #55d6be;
    margin-top: 12px;
}
</style>
</head>
<body>
<main>
<h1>ULTRA AI CLOUD TURBO</h1>
<p>Seu assistente de inteligência artificial</p>

<div class="card">
<form id="pergunta-form" method="post" action="/perguntar">
<textarea name="pergunta"
placeholder="Digite o que deseja fazer..."
required></textarea>
<button id="enviar" type="submit">Perguntar à IA</button>
<p id="status"></p>
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

<script>
document.getElementById("pergunta-form").addEventListener(
    "submit",
    function() {
        const botao = document.getElementById("enviar");
        botao.disabled = true;
        botao.textContent = "Consultando...";
        document.getElementById("status").textContent =
            "A IA está preparando sua resposta. Aguarde...";
    }
);
</script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def inicio():
    if PASSWORD and not session.get("autorizado"):
        return """
        <h2>ULTRA AI CLOUD</h2>
        <form method="post" action="/entrar">
        <input type="password" name="senha"
        placeholder="Senha de acesso" required>
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
            HTML,
            erro="Configure GEMINI_API_KEY no Render."
        )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + MODEL
        + ":generateContent"
    )

    dados_envio = {
        "contents": [
            {
                "parts": [
                    {"text": pergunta}
                ]
            }
        ]
    }

    resultado = None

    # Uma nova tentativa apenas para falhas temporárias
    for tentativa in range(2):
        try:
            resultado = http.post(
                url,
                params={"key": GEMINI_KEY},
                json=dados_envio,
                timeout=(10, 45)
            )

        except requests.exceptions.RequestException:
            logging.exception(
                "Falha de conexão com Gemini, tentativa %s",
                tentativa + 1
            )

            if tentativa == 0:
                time.sleep(1)
                continue

            return render_template_string(
                HTML,
                erro="Falha de conexão. Tente novamente."
            )

        if resultado.status_code in (429, 500, 502, 503, 504):
            logging.warning(
                "Gemini HTTP %s, tentativa %s",
                resultado.status_code,
                tentativa + 1
            )

            if tentativa == 0:
                time.sleep(1)
                continue

        break

    if resultado is None:
        return render_template_string(
            HTML,
            erro="Não foi possível consultar a IA."
        )

    if not resultado.ok:
        logging.error(
            "Erro Gemini HTTP %s: %s",
            resultado.status_code,
            resultado.text[:1500]
        )

        if resultado.status_code == 503:
            mensagem = (
                "O Gemini está sobrecarregado. "
                "Tente novamente em alguns instantes."
            )
        elif resultado.status_code == 429:
            mensagem = (
                "Limite de solicitações atingido. "
                "Aguarde um pouco e tente novamente."
            )
        else:
            mensagem = (
                "Erro do Gemini: HTTP "
                + str(resultado.status_code)
                + ". Consulte os Logs do Render."
            )

        return render_template_string(HTML, erro=mensagem)

    try:
        dados = resultado.json()
        candidatos = dados.get("candidates", [])

        if not candidatos:
            logging.error(
                "Gemini sem candidatos: %s",
                str(dados)[:1500]
            )

            return render_template_string(
                HTML,
                erro="O Gemini não retornou uma resposta."
            )

        partes = candidatos[0].get(
            "content", {}
        ).get("parts", [])

        resposta = "\n".join(
            parte["text"]
            for parte in partes
            if "text" in parte
        )

        if not resposta:
            return render_template_string(
                HTML,
                erro="O Gemini não retornou texto."
            )

        return render_template_string(
            HTML,
            resposta=resposta
        )

    except (ValueError, TypeError, KeyError):
        logging.exception("Erro ao interpretar resposta do Gemini")

        return render_template_string(
            HTML,
            erro="Não foi possível interpretar a resposta da IA."
        )


@app.route("/health")
def health():
    return {
        "status": "online",
        "app": "ULTRA AI CLOUD TURBO"
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
