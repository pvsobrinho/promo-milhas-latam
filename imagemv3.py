import os
import time
import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import re
import heapq
import pytesseract
import csv

# Caminho do executável do Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configurações
NUM_ITERACOES = 5
DIRETORIO_SAIDA = "prints_milhas"
POSICAO_CLIQUE = (1747, 729)  # Ajustar conforme o botão "próxima data"
DELAY_INICIAL = 5
DELAY_CARREGAMENTO_TELA = 10
DELAY_POS_CLICK = 2
CSV_SAIDA = "milhas_resultado.csv"

# Garante que a pasta de prints exista
os.makedirs(DIRETORIO_SAIDA, exist_ok=True)

# Aviso inicial
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
        padrao_milhas = re.findall(r"\d{1,3}(?:\.\d{3})* milhas", texto)
        padrao_horario = re.findall(r"\d{2}:\d{2}", texto)

        # Novo padrão para capturar data no estilo da LATAM: 'sab., 29/11'
        padrao_data_latam = re.search(r"\b\w{3}\.,\s\d{2}/\d{2}\b", texto.lower())
        if padrao_data_latam:
            data_detectada = padrao_data_latam.group().replace("sab.", "sáb.").strip()
        else:
            data_detectada = "Data não encontrada"

        milhas_numeros = [int(m.replace(".", "").split()[0]) for m in padrao_milhas]
        horario = padrao_horario[0] if padrao_horario else "Horário não encontrado"

        print(f"📅 Data detectada: {data_detectada}")
        print(f"🕒 Horário detectado: {horario}")
        print(f"🔍 Milhas extraídas (filtradas): {milhas_numeros}")
        return milhas_numeros, data_detectada, horario
    except Exception as e:
        print(f"❌ Erro ao processar OCR: {e}")
        return [], "Erro", "Erro"

# Loop principal
for i in range(NUM_ITERACOES):
    print(f"\n📅 Iteração {i + 1}")
    time.sleep(DELAY_CARREGAMENTO_TELA)

    screenshot_path = os.path.join(DIRETORIO_SAIDA, f"milhas_dia_{i + 1}.png")
    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    print(f"🖼️ Screenshot salva: {screenshot_path}")

    milhas_dia, data_detectada, horario_voo = processar_ocr(screenshot_path)

    if milhas_dia:
        menor = min(milhas_dia)
        milhas_extraidas.append((data_detectada, menor, horario_voo))
        print(f"✅ Menor valor do dia {data_detectada}: {menor} milhas")

    pyautogui.click(POSICAO_CLIQUE)
    print(f"🖱️ Clique na posição do mouse: {POSICAO_CLIQUE}")
    time.sleep(DELAY_POS_CLICK)

# Salvar CSV
with open(CSV_SAIDA, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Data", "Milhas", "Horario"])
    for data, milhas, horario in milhas_extraidas:
        writer.writerow([data, milhas, horario])

# Top 3 menores
top_3 = heapq.nsmallest(3, milhas_extraidas, key=lambda x: x[1])
print("\n🏆 Top 3 menores valores encontrados:")
for data, milhas, horario in top_3:
    print(f"{data} às {horario}: {milhas} milhas")
