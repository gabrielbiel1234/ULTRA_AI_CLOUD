```python
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
    text-decoration: none;
    margin-top: 12px;
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
<h2>INTELIGÊNCIA ARTIFICIAL</h2>

<form id="pergunta-form" method="post" action="/perguntar">

<textarea name="pergunta"
placeholder="Digite sua pergunta..."
required></textarea>

<button id="enviar" type="submit">
Perguntar à IA
</button>

</form>
</div>

<div class="card">
<h2>CRIADOR DE IMAGENS AI</h2>

<p>Descreva a imagem que você deseja criar.</p>

<form id="imagem-form" method="post" action="/gerar-imagem">

<textarea name="descricao"
placeholder="Exemplo: Um carro esportivo vermelho em uma estrada futurista..."
required></textarea>

<button id="criar" type="submit">
CRIAR IMAGEM
</button>

<p id="status"></p>

</form>
</div>

{% if resposta %}
<div class="card">
<h2>Resposta da IA</h2>
<div class="resposta">{{ resposta }}</div>
</div>
{% endif %}

{% if imagem %}
<div class="card">
<h2>SUA IMAGEM FOI CRIADA!</h2>

<img class="imagem"
src="{{ imagem }}"
alt="Imagem criada pela inteligência artificial">

<br>

<a class="download"
href="{{ imagem }}"
download="ultra-ai-imagem.png">
BAIXAR IMAGEM
</a>

</div>
{% endif %}

{% if erro %}
<div class="card">
<h2>AVISO</h2>
<div class="resposta">{{ erro }}</div>
</div>
{% endif %}

</main>

<script>
function ativarFormulario(formId, botaoId, mensagem) {
    const form = document.getElementById(formId);

    form.addEventListener("submit", function() {
        const botao = document.getElementById(botaoId);
        botao.disabled = true;
        botao.textContent = mensagem;

        const status = document.getElementById("status");
        if (status) {
            status.textContent = "Aguarde, processando...";
        }
    });
}

ativarFormulario(
    "pergunta-form",
    "enviar",
    "Consultando..."
);

ativarFormulario(
    "imagem-form",
    "criar",
    "CRIANDO IMAGEM..."
);
</script>

</body>
</html>
"""


def verificar_acesso():
    return not PASSWORD or session.get("autorizado")


def chamar_gemini(modelo, dados, timeout=120):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + modelo
        + ":generateContent"
    )

    for tentativa in range(2):
        try:
            resultado = http.post(
                url,
                params={"key": GEMINI_KEY},
                json=dados,
                timeout=(10, timeout)
            )

        except requests.exceptions.RequestException:
            logging.exception("Erro de conexão com Gemini")

            if tentativa == 0:
                time.sleep(1)
                continue

            return None, "Falha de conexão com o Gemini."

        if resultado.status_code in (429, 500, 502, 503, 504):
            if tentativa == 0:
                time.sleep(2)
                continue

        if not resultado.ok:
            logging.error(
                "Gemini HTTP %s: %s",
                resultado.status_code,
                resultado.text[:1500]
            )

            if resultado.status_code == 429:
                return None, "Limite de solicitações atingido. Tente mais tarde."

            if resultado.status_code == 503:
                return None, "Gemini sobrecarregado. Tente novamente."

            return None, (
                "Erro do Gemini HTTP "
                + str(resultado.status_code)
                + ". Confira os Logs do Render."
            )

        try:
            return resultado.json(), None
        except ValueError:
            return None, "Resposta inválida do Gemini."

    return None, "Não foi possível consultar o Gemini."


@app.route("/", methods=["GET"])
def inicio():
    if not verificar_acesso():
        return redirect("/login")

    return render_template_string(HTML)


@app.route("/login", methods=["GET"])
def login():
    if not PASSWORD:
        return redirect("/")

    return """
    <html lang="pt-br">
    <body style="background:#101827;color:white;font-family:Arial;padding:30px">
    <h2>ULTRA AI CLOUD</h2>
    <form method="post" action="/entrar">
    <input type="password" name="senha"
    placeholder="Senha de acesso" required>
    <button>Entrar</button>
    </form>
    </body>
    </html>
    """


@app.route("/entrar", methods=["POST"])
def entrar():
    if request.form.get("senha") == PASSWORD and PASSWORD:
        session["autorizado"] = True
        return redirect("/")

    return "Senha incorreta.", 401


@app.route("/perguntar", methods=["POST"])
def perguntar():
    if not verificar_acesso():
        return redirect("/login")

    pergunta = request.form.get("pergunta", "").strip()

    if not pergunta:
        return redirect("/")

    if not GEMINI_KEY:
        return render_template_string(
            HTML,
            erro="Configure GEMINI_API_KEY no Render."
        )

    dados_envio = {
        "contents": [{
            "parts": [{"text": pergunta}]
        }]
    }

    dados, erro = chamar_gemini(MODEL, dados_envio, 45)

    if erro:
        return render_template_string(HTML, erro=erro)

    try:
        partes = dados["candidates"][0]["content"]["parts"]

        resposta = "\n".join(
            parte["text"]
            for parte in partes
            if "text" in parte
        )

        if not resposta:
            resposta = "A IA não retornou texto."

        return render_template_string(
            HTML,
            resposta=resposta
        )

    except (KeyError, IndexError, TypeError):
        logging.exception("Erro ao interpretar resposta")
        return render_template_string(
            HTML,
            erro="Não foi possível interpretar a resposta."
        )


@app.route("/gerar-imagem", methods=["POST"])
def gerar_imagem():
    if not verificar_acesso():
        return redirect("/login")

    descricao = request.form.get("descricao", "").strip()

    if not descricao:
        return redirect("/")

    if not GEMINI_KEY:
        return render_template_string(
            HTML,
            erro="Configure GEMINI_API_KEY no Render."
        )

    dados_envio = {
        "contents": [{
            "parts": [{
                "text": (
                    "Crie uma imagem de alta qualidade baseada "
                    "nesta descrição. Gere a imagem solicitada: "
                    + descricao
                )
            }]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    dados, erro = chamar_gemini(
        IMAGE_MODEL,
        dados_envio,
        180
    )

    if erro:
        return render_template_string(
            HTML,
            erro=erro
        )

    try:
        partes = dados["candidates"][0]["content"]["parts"]

        for parte in partes:
            imagem = parte.get("inlineData")

            if imagem and imagem.get("data"):
                mime = imagem.get(
                    "mimeType",
                    "image/png"
                )

                if not mime.startswith("image/"):
                    continue

                imagem_base64 = imagem["data"]

                imagem_url = (
                    "data:"
                    + mime
                    + ";base64,"
                    + imagem_base64
                )

                return render_template_string(
                    HTML,
                    imagem=imagem_url
                )

        logging.error(
            "Gemini não retornou imagem: %s",
            str(dados)[:1500]
        )

        return render_template_string(
            HTML,
            erro=(
                "O modelo não retornou uma imagem. "
                "Confira se o modelo está disponível para sua chave API."
            )
        )

    except (KeyError, IndexError, TypeError):
        logging.exception("Erro ao processar imagem")

        return render_template_string(
            HTML,
            erro="Não foi possível processar a imagem gerada."
        )


@app.route("/health")
def health():
    return {
        "status": "online",
        "app": "ULTRA AI CLOUD TURBO",
        "image_generation": True
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
```
