import logging

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
            erro="Configure a chave GEMINI_API_KEY no painel do Render."
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

        if not resultado.ok:
            logging.error(
                "Erro Gemini: HTTP %s - %s",
                resultado.status_code,
                resultado.text[:1500]
            )
            return render_template_string(
                HTML,
                erro=f"Erro na comunicação com o Gemini (HTTP {resultado.status_code}). Consulte os Logs do Render."
            )

        dados = resultado.json()

        candidatos = dados.get("candidates", [])
        if not candidatos:
            logging.error("Gemini retornou resposta sem candidatos: %s",
                          str(dados)[:1500])
            return render_template_string(
                HTML,
                erro="O Gemini não retornou uma resposta. Verifique os Logs."
            )

        partes = candidatos[0].get("content", {}).get("parts", [])
        resposta = "\n".join(
            parte["text"] for parte in partes if "text" in parte
        )

        if not resposta:
            return render_template_string(
                HTML,
                erro="O Gemini não retornou texto. Tente outra pergunta."
            )

        return render_template_string(HTML, resposta=resposta)

    except Exception as e:
        logging.error("Falha na consulta Gemini: %s", type(e).__name__)
        return render_template_string(
            HTML,
            erro="Falha na conexão com o Gemini. Consulte os Logs do Render."
        )
