import os
import time
import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import re
import heapq
import pytesseract
import csv
from datetime import datetime, timedelta

# Caminho do executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ====== CONFIGURAÇÕES ======
DATA_INICIAL = datetime(2025, 9, 1)  # Você pode alterar para a data desejada
NUM_ITERACOES = 7
DIRETORIO_SAIDA = "prints_milhas"
POSICAO_CLIQUE = (1747, 729)  # Atualizar se necessário
DELAY_INICIAL = 5
DELAY_CARREGAMENTO_TELA = 10
DELAY_POS_CLICK = 2
CSV_SAIDA = "milhas_resultado.csv"
# ============================

os.makedirs(DIRETORIO_SAIDA, exist_ok=True)

print("⏳ Aguarde 5 segundos e posicione o mouse sobre a seta de próxima data no navegador...")
time.sleep(DELAY_INICIAL)

milhas_extraidas = []

def processar_ocr(imagem_path):
    try:
        imagem = Image.open(imagem_path).convert('L')
        imagem = imagem.filter(ImageFilter.SHARPEN)
        imagem = ImageEnhance.Contrast(imagem).enhance(2)
        imagem = imagem.point(lambda x: 0 if x < 140 else 255)

        texto = pytesseract.image_to_string(imagem, lang='eng')

        milhas = re.findall(r"\d{1,3}(?:\.\d{3})* milhas", texto)
        horarios = re.findall(r"\d{2}:\d{2}", texto)

        milhas_numeros = [int(m.replace(".", "").split()[0]) for m in milhas]
        horario = horarios[0] if horarios else "Horário não encontrado"

        print(f"🕒 Horário detectado: {horario}")
        print(f"🔍 Milhas extraídas: {milhas_numeros}")
        return milhas_numeros, horario
    except Exception as e:
        print(f"❌ Erro ao processar OCR: {e}")
        return [], "Erro"

# Loop principal
for i in range(NUM_ITERACOES):
    data_atual = DATA_INICIAL + timedelta(days=i)
    data_formatada = data_atual.strftime('%d/%m/%Y')
    print(f"\n📅 Iteração {i + 1} — Data: {data_formatada}")
    time.sleep(DELAY_CARREGAMENTO_TELA)

    screenshot_path = os.path.join(DIRETORIO_SAIDA, f"milhas_dia_{i + 1}.png")
    pyautogui.screenshot().save(screenshot_path)
    print(f"🖼️ Screenshot salva: {screenshot_path}")

    milhas_dia, horario = processar_ocr(screenshot_path)

    if milhas_dia:
        menor = min(milhas_dia)
        milhas_extraidas.append((data_formatada, menor, horario))
        print(f"✅ Menor valor do dia {data_formatada}: {menor} milhas")

    pyautogui.click(POSICAO_CLIQUE)
    print(f"🖱️ Clique na posição do mouse: {POSICAO_CLIQUE}")
    time.sleep(DELAY_POS_CLICK)

# Salvar resultados
with open(CSV_SAIDA, mode='w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Data", "Milhas", "Horario"])
    writer.writerows(milhas_extraidas)

# Top 3 menores
top_3 = heapq.nsmallest(3, milhas_extraidas, key=lambda x: x[1])
print("\n🏆 Top 3 menores valores encontrados:")
for data, milhas, horario in top_3:
    print(f"{data} às {horario}: {milhas} milhas")
