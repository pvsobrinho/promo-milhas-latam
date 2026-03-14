import os
import time
import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import re
import heapq
import pytesseract
from datetime import datetime, timedelta

# Caminho do executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ========= CONFIGURAÇÕES =========
NUM_ITERACOES = 10
DIRETORIO_SAIDA = "prints_milhas"
POSICAO_CLIQUE = (1747, 729)  # Altere conforme a posição da seta de próxima data
DELAY_INICIAL = 5
DELAY_ENTRE_ITERACOES = 10
DATA_INICIAL = datetime.strptime("2025-09-01", "%Y-%m-%d")
# =================================

# Garante diretório
if not os.path.exists(DIRETORIO_SAIDA):
    os.makedirs(DIRETORIO_SAIDA)

print("⏳ Aguarde 5 segundos e posicione o mouse sobre a seta de próxima data no navegador...")
time.sleep(DELAY_INICIAL)

milhas_extraidas = []

def processar_ocr(imagem_path):
    try:
        imagem = Image.open(imagem_path)
        imagem = imagem.convert('L')
        imagem = imagem.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(imagem)
        imagem = enhancer.enhance(2)
        imagem = imagem.point(lambda x: 0 if x < 140 else 255)

        texto = pytesseract.image_to_string(imagem, lang='eng')
        padrao = re.findall(r"\d{1,3}(?:\.\d{3})* milhas", texto)

        milhas_validas = []
        for m in padrao:
            try:
                valor = int(m.replace(".", "").split()[0])
                if 1000 <= valor <= 500000:  # filtro para evitar valores irreais
                    milhas_validas.append(valor)
            except:
                continue

        if milhas_validas:
            print(f"🔍 Milhas extraídas (filtradas): {milhas_validas}")
            return milhas_validas
        else:
            print(f"🔍 Texto detectado, mas sem milhas válidas:\n{texto}")
            return []

    except Exception as e:
        print(f"❌ Erro ao processar OCR: {e}")
        return []

# Loop principal
for i in range(NUM_ITERACOES):
    data_estimativa = (DATA_INICIAL + timedelta(days=i)).strftime('%d/%m/%Y')
    print(f"\n📅 Iteração {i + 1} (Data estimada: {data_estimativa})")

    screenshot_path = os.path.join(DIRETORIO_SAIDA, f"milhas_dia_{i + 1}.png")
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    print(f"🖼️ Screenshot salva: {screenshot_path}")

    milhas_dia = processar_ocr(screenshot_path)
    if milhas_dia:
        menor = min(milhas_dia)
        milhas_extraidas.append((menor, data_estimativa))
        print(f"✅ Menor valor do dia {data_estimativa}: {menor} milhas")

    pyautogui.click(POSICAO_CLIQUE)
    print(f"🖱️ Clique na posição do mouse: {POSICAO_CLIQUE}")
    time.sleep(DELAY_ENTRE_ITERACOES)

# Exibe top 5 menores
top_5 = heapq.nsmallest(5, milhas_extraidas, key=lambda x: x[0])
print("\n🏆 Top 5 menores valores encontrados:")
for milhas, data in top_5:
    print(f"{data}: {milhas} milhas")
