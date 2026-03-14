from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import heapq

# ======= CONFIGURAÇÕES DO USUÁRIO ========
ORIGEM = 'GRU'
DESTINO = 'BPS'
DATA_INICIAL = '2025-09-01'
DATA_FINAL = '2025-09-30'
# ========================================

data_atual = datetime.strptime(DATA_INICIAL, '%Y-%m-%d')
data_final = datetime.strptime(DATA_FINAL, '%Y-%m-%d')

# Setup do navegador sem perfil
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

print("🧭 O navegador foi aberto. Agora você pode:")
print("1. Colar a URL da LATAM na barra de endereços.")
print("2. Fazer login manualmente, se necessário.")
print("3. Depois, pressione [ENTER] aqui no terminal para o robô começar.")
input("▶️  Pressione ENTER para iniciar o robô...")

milhas_por_data = []

def extrair_milhas():
    milhas_element = wait.until(
        EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'milhas')]"))
    )
    texto = milhas_element.text.strip()
    milhas = int(texto.split(' ')[0].replace('.', ''))
    return milhas

url_base = (
    f"https://www.latamairlines.com/br/pt/oferta-voos?"
    f"origin={ORIGEM}&destination={DESTINO}"
    f"&adt=1&chd=0&inf=0&trip=OW&cabin=Economy"
    f"&redemption=true&sort=RECOMMENDED&outbound="
)

while data_atual <= data_final:
    data_str = data_atual.strftime('%Y-%m-%d')
    url = url_base + f"{data_str}T15%3A00%3A00.000Z"

    print(f"Abrindo: {url}")
    driver.get(url)

    try:
        milhas = extrair_milhas()
        milhas_por_data.append((milhas, data_str))
        print(f"✅ {data_str}: {milhas} milhas")
    except Exception as e:
        print(f"❌ {data_str}: erro ao extrair milhas: {e}")

    data_atual += timedelta(days=1)

driver.quit()

# Exibir os 5 menores valores
top_5 = heapq.nsmallest(5, milhas_por_data, key=lambda x: x[0])
print("\n🏆 Top 5 menores valores encontrados:")
for milhas, data in top_5:
    print(f"{data}: {milhas} milhas")
