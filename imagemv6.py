import os
import time
import json
import urllib.request
import webbrowser
from urllib.parse import quote
import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import re
import heapq
import pytesseract
import csv
from datetime import datetime, timedelta


def _carregar_dotenv():
    """Carrega variáveis do arquivo .env na pasta do projeto (para RESEND_API_KEY sem reiniciar o IDE)."""
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

# Caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === CONFIGURAÇÕES ===
ORIGEM = 'CGH'
DESTINO = 'SSA'
ANO = 2026  # Ano da busca; dia e mês são lidos do primeiro print (área ao redor do cursor)
NUM_ITERACOES = 60

POSICAO_CLIQUE = (1747, 729)
DELAY_INICIAL = 5
DELAY_PRIMEIRO_PRINT = 5  # segundos extras só antes do primeiro print (para capturar a data)
DELAY_CARREGAMENTO_TELA = 10
DELAY_POS_CLICK = 2
VALOR_MINIMO_VALIDO = 1500

# Área do mini-print para extrair a data: centrada em POSICAO_CLIQUE (onde está a data na tela)
MINI_PRINT_LARGURA = 480
MINI_PRINT_ALTURA = 90

# E-mail: direto do Python (sem abrir Outlook, sem senha Microsoft)
EMAIL_ENABLED = True
# Resend sem domínio verificado só envia para o e-mail da conta. Use o mesmo e-mail do login Resend.
# Para enviar a outro e-mail (ex.: Outlook), verifique um domínio em resend.com/domains e use RESEND_FROM com esse domínio.
EMAIL_DESTINO = "paulovictor.s2013@gmail.com"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = "Pomo Milhas <onboarding@resend.dev>"  # com domínio verificado: use algo como notificacoes@seudominio.com

# Título do e-mail ao final do processamento
ASSUNTO_EMAIL_CONCLUIDO = "Promoção Milhas LATAM - processamento do robô concluído"
ASSUNTO_EMAIL_ERRO = "Promoção Milhas LATAM - erro na extração"
ASSUNTO_EMAIL_SEM_RESULTADOS = "Promoção Milhas LATAM - sem resultados"

diretorio_saida = "prints_milhas"
os.makedirs(diretorio_saida, exist_ok=True)

print("⏳ Aguarde 5 segundos. Deixe a página da LATAM com a primeira data visível...")
time.sleep(DELAY_INICIAL)
print(f"⏳ Mais {DELAY_PRIMEIRO_PRINT} segundos. Capturando a data em POSICAO_CLIQUE (1747, 729)...")
time.sleep(DELAY_PRIMEIRO_PRINT)

milhas_extraidas = []
tentativas = 0
data_primeira = None  # primeira data da busca (para intervalo no e-mail)
data_ultima = None    # última data da busca (para intervalo no e-mail)


def _ocr_data_em_imagem(img_pil, lang="eng"):
    """Roda OCR na imagem e retorna lista de (dia, mês) encontrados (DD/MM)."""
    texto = pytesseract.image_to_string(img_pil, lang=lang)
    # DD/MM com ou sem espaços em volta da barra
    matches = re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})", texto)
    result = []
    for dia_s, mes_s in matches:
        try:
            dia, mes = int(dia_s), int(mes_s)
            if 1 <= dia <= 31 and 1 <= mes <= 12:
                result.append((dia, mes))
        except ValueError:
            pass
    return result, texto.strip()


def extrair_data_do_mini_print(imagem_pil):
    """Extrai a data do MEIO da faixa de datas. A data selecionada pode ser texto claro em fundo azul.
    Retorna (dia, mês) ou None. Se debug=True, retorna também o texto bruto do OCR."""
    try:
        img = imagem_pil.convert("L")
        img = img.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2)

        # Versão 1: texto escuro em fundo claro (datas não selecionadas)
        img1 = img.point(lambda x: 0 if x < 140 else 255)
        datas1, texto1 = _ocr_data_em_imagem(img1, "eng")

        # Versão 2: inverter (para texto claro em fundo escuro/azul - data selecionada)
        img2 = img.point(lambda x: 255 if x < 140 else 0)
        datas2, texto2 = _ocr_data_em_imagem(img2, "eng")

        datas_validas = datas1 or datas2
        texto_bruto = texto1 or texto2

        if not datas_validas:
            print(f"   [OCR data] Nenhum DD/MM encontrado. Texto: {repr(texto_bruto[:150])}")
            return None

        # Evitar 01/01 quando for o único valor (muitas vezes é ruído)
        if len(datas_validas) == 1 and datas_validas[0] == (1, 1):
            print(f"   [OCR data] Descartando 01/01 (possível ruído). Texto: {repr(texto_bruto[:150])}")
            return None

        # Preferir datas que não sejam 01/01 (data real da barra)
        outras = [d for d in datas_validas if d != (1, 1)]
        if outras:
            datas_validas = outras

        idx_meio = len(datas_validas) // 2
        return datas_validas[idx_meio]
    except Exception as e:
        print(f"❌ Erro ao extrair data do mini-print: {e}")
        return None


# CSV: nome genérico (a data vem do mini-print em cada iteração)
nome_base_csv = f"milhas_{ORIGEM}_{DESTINO}"
csv_saida = f"{nome_base_csv}.csv"
data_atual = datetime(ANO, 1, 1)  # fallback se OCR do mini-print falhar


def processar_ocr(imagem_path):
    try:
        imagem = Image.open(imagem_path)
        imagem = imagem.convert('L')
        imagem = imagem.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(imagem)
        imagem = enhancer.enhance(2)
        imagem = imagem.point(lambda x: 0 if x < 140 else 255)

        texto = pytesseract.image_to_string(imagem, lang='eng')
        padrao_milhas = re.findall(r"\d{1,3}(?:\.\d{3})* milhas", texto)
        padrao_horario = re.findall(r"\d{2}:\d{2}", texto)

        milhas_numeros = [int(m.replace(".", "").split()[0]) for m in padrao_milhas]
        horario = padrao_horario[0] if padrao_horario else "Horário não encontrado"

        return milhas_numeros, horario
    except Exception as e:
        print(f"❌ Erro ao processar OCR: {e}")
        return [], "Erro"


def enviar_email(assunto: str, corpo: str) -> bool:
    """Envia e-mail: se RESEND_API_KEY estiver definida, envia pela API (sem abrir programa).
    Caso contrário, abre o mailto (Outlook) para você clicar em Enviar."""
    if not EMAIL_ENABLED or not (EMAIL_DESTINO or "").strip():
        return False
    api_key = (RESEND_API_KEY or "").strip()
    if api_key:
        try:
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": RESEND_FROM,
                    "to": [EMAIL_DESTINO.strip()],
                    "subject": assunto,
                    "text": corpo,
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "PomoMilhas/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    print("📧 E-mail enviado para", EMAIL_DESTINO, "(Resend API, sem abrir Outlook).")
                    return True
        except urllib.error.HTTPError as e:
            print(f"❌ Erro ao enviar e-mail (Resend): {e.code} {e.reason}")
            try:
                body = e.read().decode()
                print(f"   Resposta: {body[:200]}")
            except Exception:
                pass
            return False
        except Exception as e:
            print(f"❌ Erro ao enviar e-mail: {e}")
            return False
    # Fallback: mailto (abre o cliente)
    try:
        url = (
            "mailto:"
            + quote(EMAIL_DESTINO.strip(), safe="")
            + "?subject="
            + quote(assunto, safe="")
            + "&body="
            + quote(corpo, safe="")
        )
        webbrowser.open(url)
        print("📧 RESEND_API_KEY não definida. Cliente de e-mail aberto — clique em Enviar.")
        return True
    except Exception as e:
        print(f"❌ Erro ao abrir e-mail: {e}")
        return False


def apagar_mini_prints():
    """Remove os mini-prints (e prints de data) da pasta prints_milhas. Mantém só os prints de tela inteira."""
    if not os.path.isdir(diretorio_saida):
        return
    apagados = 0
    for nome in os.listdir(diretorio_saida):
        if "_mini" in nome and nome.lower().endswith(".png"):
            path = os.path.join(diretorio_saida, nome)
            try:
                os.remove(path)
                apagados += 1
                print(f"   Apagado: {nome}")
            except OSError as e:
                print(f"   Não foi possível apagar {nome}: {e}")
    if apagados:
        print(f"🗑️ {apagados} mini-print(s) removido(s). Prints de tela inteira mantidos.")


# Loop principal: em cada iteração, mini-print em POSICAO_CLIQUE antes do clique para capturar a data da tela
while tentativas < NUM_ITERACOES:
    print(f"\n📅 Iteração {tentativas + 1}")
    time.sleep(DELAY_CARREGAMENTO_TELA)

    # Antes do clique: mini-print na área da data (POSICAO_CLIQUE = 1747, 729) para ler a data visível (ex.: 08/05)
    cx, cy = POSICAO_CLIQUE
    rx = max(0, cx - MINI_PRINT_LARGURA // 2)
    ry = max(0, cy - MINI_PRINT_ALTURA // 2)
    mini_img = pyautogui.screenshot(region=(rx, ry, MINI_PRINT_LARGURA, MINI_PRINT_ALTURA))
    par_data = extrair_data_do_mini_print(mini_img)
    if par_data:
        dia_hoje, mes_hoje = par_data
        data_atual = datetime(ANO, mes_hoje, dia_hoje)
        data_formatada = data_atual.strftime("%d/%m/%Y")
        print(f"📅 Data no mini-print ({cx}, {cy}): {data_formatada}")
    else:
        data_formatada = data_atual.strftime("%d/%m/%Y")
        print(f"⚠️ Data não lida no mini-print, usando: {data_formatada}")

    if data_primeira is None:
        data_primeira = data_formatada
    data_ultima = data_formatada

    nome_data = data_atual.strftime("%d_%b_%Y").upper()
    # Salva o mini-print com o mesmo padrão da iteração (será apagado ao final do processamento)
    nome_mini = f"milhas_{ORIGEM}_{DESTINO}_{nome_data}_iter{tentativas + 1}_mini.png"
    path_mini = os.path.join(diretorio_saida, nome_mini)
    mini_img.save(path_mini)
    print(f"🖼️ Mini-print salvo: {path_mini}")

    nome_arquivo = os.path.join(diretorio_saida, f"milhas_{ORIGEM}_{DESTINO}_{nome_data}.png")
    pyautogui.screenshot(nome_arquivo)
    print(f"🖼️ Screenshot salva: {nome_arquivo}")

    milhas_dia, horario_voo = processar_ocr(nome_arquivo)

    milhas_validas = [m for m in milhas_dia if m >= VALOR_MINIMO_VALIDO]

    if not milhas_validas and milhas_dia:
        print(f"⚠️ Milhas inválidas detectadas ({milhas_dia}), aguardando 5 segundos e tentando novamente...")
        time.sleep(5)
        pyautogui.screenshot(nome_arquivo)
        milhas_dia, horario_voo = processar_ocr(nome_arquivo)
        milhas_validas = [m for m in milhas_dia if m >= VALOR_MINIMO_VALIDO]

    if milhas_validas:
        menor = min(milhas_validas)
        milhas_extraidas.append((data_formatada, menor, horario_voo))
        print(f"🕒 Horário detectado: {horario_voo}")
        print(f"🔍 Milhas extraídas: {milhas_dia}")
        print(f"✅ Menor valor do dia {data_formatada}: {menor} milhas")
    else:
        print("❌ Não foi possível extrair milhas válidas. Tentando novamente esta mesma data.")
        msg_erro = (
            "Promoção Milhas LATAM – erro na extração\n\n"
            f"Rota: {ORIGEM} → {DESTINO}\n"
        )
        if data_primeira and data_ultima:
            msg_erro += f"Pesquisa feita de {data_primeira} a {data_ultima}\n\n"
        msg_erro += (
            f"Data da busca (voo na tela): {data_formatada}\n\n"
            "Não foi possível extrair milhas válidas para esta data."
        )
        enviar_email(ASSUNTO_EMAIL_ERRO, msg_erro)

    # Só depois de processar e salvar: clica para avançar (próximo dia)
    pyautogui.click(POSICAO_CLIQUE)
    print(f"🖱️ Clique na posição do mouse: {POSICAO_CLIQUE}")
    time.sleep(DELAY_POS_CLICK)

    tentativas += 1

# Salvar CSV
with open(csv_saida, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Data", "Milhas", "Horario"])
    for data, milhas, horario in milhas_extraidas:
        writer.writerow([data, milhas, horario])

# Top 3 menores valores (global — pode repetir data)
top_3 = heapq.nsmallest(3, milhas_extraidas, key=lambda x: x[1])
print("\n🏆 Top 3 menores valores encontrados:")
for data, milhas, horario in top_3:
    print(f"{data} às {horario}: {milhas} milhas")

# Top 10 com datas diferentes (uma opção por dia; só se tiver >= 15 iterações)
MIN_ITERACOES_PARA_TOP_10 = 15
top_10_datas_diferentes = []
if len(milhas_extraidas) >= MIN_ITERACOES_PARA_TOP_10:
    # milhas_extraidas já tem no máximo um registro por data; os 10 menores são 10 datas diferentes
    top_10_datas_diferentes = heapq.nsmallest(10, milhas_extraidas, key=lambda x: x[1])
    print("\n📋 Top 10 opções com datas diferentes:")
    for i, (data, milhas, horario) in enumerate(top_10_datas_diferentes, 1):
        print(f"  {i}. {data} às {horario}: {milhas} milhas")

# Intervalo da busca (para os e-mails)
intervalo_busca = ""
if data_primeira and data_ultima:
    intervalo_busca = f"Pesquisa feita de {data_primeira} a {data_ultima}"

# Notificação por e-mail ao final do processamento
if milhas_extraidas:
    linhas = [
        "Promoção Milhas LATAM – processamento do robô concluído",
        f"Rota: {ORIGEM} → {DESTINO}",
        f"Datas processadas: {len(milhas_extraidas)}",
    ]
    if intervalo_busca:
        linhas.append(intervalo_busca)
    linhas.extend(["", "Top 3 menores preços:"])
    for i, (data, milhas, horario) in enumerate(top_3, 1):
        linhas.append(f"  {i}. {data} às {horario}: {milhas} milhas")
    if top_10_datas_diferentes:
        linhas.append("")
        linhas.append("Outras 10 opções de voos com datas diferentes:")
        for i, (data, milhas, horario) in enumerate(top_10_datas_diferentes, 1):
            linhas.append(f"  {i}. {data} às {horario}: {milhas} milhas")
    corpo = "\n".join(linhas)
    enviar_email(ASSUNTO_EMAIL_CONCLUIDO, corpo)
else:
    corpo_sem_resultados = (
        f"Promoção Milhas LATAM ({ORIGEM} → {DESTINO}) finalizou, mas nenhum valor em milhas foi extraído."
    )
    if intervalo_busca:
        corpo_sem_resultados = intervalo_busca + "\n\n" + corpo_sem_resultados
    enviar_email(ASSUNTO_EMAIL_SEM_RESULTADOS, corpo_sem_resultados)

# Após enviar o e-mail: apagar mini-prints (manter só prints de tela inteira)
print("\n🗑️ Removendo mini-prints...")
apagar_mini_prints()
