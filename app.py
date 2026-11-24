
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

HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ULTRA AI CLOUD</title>
<style>
body {
    font-family: Arial;
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
</style>
</head>
<body>
<main>
<h1>ULTRA AI CLOUD</h1>
<p>Seu assistente de inteligência artificial</p>

<div class="card">
<form method="post" action="/perguntar">
<textarea name="pergunta"
placeholder="Digite o que deseja fazer..."
required></textarea>
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
        <input type="password" name="senha"
        placeholder="Senha de acesso">
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

    # Até 3 tentativas para erros temporários
    max_tentativas = 3
    codigos_temporarios = (429, 500, 502, 503, 504)

    for tentativa in range(max_tentativas):
        try:
            resultado = requests.post(
                url,
                params={"key": GEMINI_KEY},
                json=dados_envio,
                timeout=60
            )

        except requests.exceptions.RequestException:
            logging.exception(
                "Falha de conexão na tentativa %s",
                tentativa + 1
            )

            if tentativa < max_tentativas - 1:
                espera = 2 ** (tentativa + 1)
                logging.info("Nova tentativa em %s segundos", espera)
                time.sleep(espera)
                continue

            return render_template_string(
                HTML,
                erro=(
                    "Não foi possível conectar ao Gemini após "
                    "3 tentativas. Tente novamente mais tarde."
                )
            )

        if resultado.status_code in codigos_temporarios:
            logging.warning(
                "Gemini HTTP %s na tentativa %s de %s",
                resultado.status_code,
                tentativa + 1,
                max_tentativas
            )

            if tentativa < max_tentativas - 1:
                espera = 2 ** (tentativa + 1)
                logging.info("Aguardando %s segundos", espera)
                time.sleep(espera)
                continue

            logging.error(
                "Gemini indisponível após 3 tentativas: %s",
                resultado.text[:1500]
            )

            return render_template_string(
                HTML,
                erro=(
                    "O Gemini está temporariamente sobrecarregado. "
                    "Tentamos 3 vezes, mas não houve resposta. "
                    "Aguarde um pouco e tente novamente."
                )
            )

        if not resultado.ok:
            logging.error(
                "Erro Gemini HTTP %s: %s",
                resultado.status_code,
                resultado.text[:1500]
            )

            return render_template_string(
                HTML,
                erro=(
                    "Erro do Gemini: HTTP "
                    + str(resultado.status_code)
                    + ". Consulte os Logs do Render."
                )
            )

        # Resposta recebida com sucesso
        break

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

    except Exception:
        logging.exception("Falha ao processar resposta Gemini")

        return render_template_string(
            HTML,
            erro="Falha ao processar a resposta do Gemini."
        )


@app.route("/health")
def health():
    return {
        "status": "online",
        "app": "ULTRA AI CLOUD"
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
