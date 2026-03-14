import os
import time
import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import re
import heapq
import pytesseract
import csv
from datetime import datetime, timedelta

# Caminho do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === CONFIGURAÇÕES ===
ORIGEM = 'CGH'
DESTINO = 'CGB'
DATA_INICIAL = '2025-10-02'
NUM_ITERACOES = 30

POSICAO_CLIQUE = (1747, 729)
DELAY_INICIAL = 5
DELAY_CARREGAMENTO_TELA = 10
DELAY_POS_CLICK = 2
VALOR_MINIMO_VALIDO = 1500

# Preparar pastas e arquivos
data_atual = datetime.strptime(DATA_INICIAL, "%Y-%m-%d")
nome_base_csv = f"milhas_{ORIGEM}_{DESTINO}_{data_atual.strftime('%d_%b').upper()}"
diretorio_saida = "prints_milhas"
csv_saida = f"{nome_base_csv}.csv"
os.makedirs(diretorio_saida, exist_ok=True)

print("⏳ Aguarde 5 segundos e posicione o mouse sobre a seta de próxima data no navegador...")
time.sleep(DELAY_INICIAL)

milhas_extraidas = []
tentativas = 0

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

# Loop principal
while tentativas < NUM_ITERACOES:
    data_formatada = data_atual.strftime("%d/%m/%Y")
    nome_data = data_atual.strftime("%d_%b_%Y").upper()
    nome_arquivo = os.path.join(diretorio_saida, f"milhas_{ORIGEM}_{DESTINO}_{nome_data}.png")

    print(f"\n📅 Iteração {tentativas + 1} — Data: {data_formatada}")
    time.sleep(DELAY_CARREGAMENTO_TELA)

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

        data_atual += timedelta(days=1)  # Avança para o próximo dia
    else:
        print("❌ Não foi possível extrair milhas válidas. Tentando novamente esta mesma data.")

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

# Top 3 menores valores
top_3 = heapq.nsmallest(3, milhas_extraidas, key=lambda x: x[1])
print("\n🏆 Top 3 menores valores encontrados:")
for data, milhas, horario in top_3:
    print(f"{data} às {horario}: {milhas} milhas")
