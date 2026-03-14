import time
import os
import sys
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

try:
    import qrcode
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode[pil]", "-q"])
    import qrcode

PASTA_SESSAO = os.path.join(os.path.dirname(__file__), "chrome_session")

def iniciar_driver():
    chromedriver_path = chromedriver_autoinstaller.install()
    print(f"[INFO] ChromeDriver: {chromedriver_path}")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={PASTA_SESSAO}")
    options.add_argument("--profile-directory=Default")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def exibir_qrcode(driver):
    print("[INFO] Aguardando QR Code...")
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, '//div[@data-ref]'))
    )
    qr_data = driver.find_element(By.XPATH, '//div[@data-ref]').get_attribute("data-ref")

    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)

    print("\n" + "=" * 50)
    print("  ESCANEIE: WhatsApp → 3 pontos → Aparelhos conectados → Conectar")
    print("=" * 50)
    for row in qr.get_matrix():
        print("".join("██" if cell else "  " for cell in row))
    print("=" * 50)
    print("[INFO] Aguardando escaneamento (máx. 120 segundos)...")

def main():
    print("=" * 50)
    print("  MODO LOGIN — salva sessão no Linux para reutilizar")
    print("=" * 50)

    driver = iniciar_driver()
    driver.get("https://web.whatsapp.com")
    time.sleep(5)

    # Verifica se já está logado
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] Já logado! Sessão salva em chrome_session/")
        driver.quit()
        return
    except TimeoutException:
        pass

    # Exibe QR Code e aguarda login
    exibir_qrcode(driver)

    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] Login realizado! Sessão salva em chrome_session/")
        time.sleep(3)  # aguarda a sessão ser gravada no disco
    except TimeoutException:
        print("[AVISO] QR Code expirou, tentando novamente...")
        exibir_qrcode(driver)
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] Login realizado!")
        time.sleep(3)

    driver.quit()
    print("[✓] Sessão pronta para ser commitada.")

if __name__ == "__main__":
    main()
