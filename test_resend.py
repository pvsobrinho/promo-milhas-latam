"""
Teste rápido do envio de e-mail via Resend.
Rode: python test_resend.py

A chave pode estar em variável de ambiente RESEND_API_KEY ou no arquivo .env na pasta do projeto:
  RESEND_API_KEY=re_sua_chave_aqui
"""
import os
import json
import urllib.request

def _carregar_dotenv():
    """Carrega variáveis do arquivo .env (sem dependência externa)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and value:
                    os.environ.setdefault(key, value)

_carregar_dotenv()
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
# Resend sem domínio verificado só envia para o e-mail da conta (o do login)
EMAIL_DESTINO = "paulovictor.s2013@gmail.com"

if not RESEND_API_KEY:
    print("RESEND_API_KEY não encontrada.")
    print("Opção 1: Crie um arquivo .env nesta pasta com a linha:")
    print("  RESEND_API_KEY=re_sua_chave_aqui")
    print("Opção 2: Defina a variável de ambiente e reinicie o Cursor (para o terminal ver a variável).")
    exit(1)

print("Enviando e-mail de teste para", EMAIL_DESTINO, "...")
try:
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps({
            "from": "Pomo Milhas <onboarding@resend.dev>",
            "to": [EMAIL_DESTINO],
            "subject": "Pomo Milhas – teste Resend",
            "text": "Se você recebeu esta mensagem, o envio pela API Resend está funcionando.",
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "PomoMilhas/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if 200 <= resp.status < 300:
            print("E-mail enviado com sucesso. Confira a caixa de entrada (e o spam) de", EMAIL_DESTINO)
        else:
            print("Resposta inesperada:", resp.status)
except urllib.error.HTTPError as e:
    print("Erro HTTP:", e.code, e.reason)
    try:
        print(e.read().decode())
    except Exception:
        pass
except Exception as e:
    print("Erro:", e)
