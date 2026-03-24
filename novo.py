import time
import os
import sys
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

try:
    import qrcode
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "qrcode[pil]", "-q"])
    import qrcode

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────
NOME_GRUPO      = "FLASH DELIVERY JIPA 2"
ARQUIVO_CONTATOS = "contatos.txt"
PASTA_SESSAO    = os.path.join(os.path.dirname(__file__), "chrome_session")

# ─────────────────────────────────────────
# CARREGA CONTATOS MONITORADOS
# ─────────────────────────────────────────
def carregar_contatos():
    if not os.path.exists(ARQUIVO_CONTATOS):
        print(f"[AVISO] Arquivo '{ARQUIVO_CONTATOS}' não encontrado.")
        return []
    with open(ARQUIVO_CONTATOS, "r", encoding="utf-8") as f:
        contatos = [linha.strip() for linha in f if linha.strip()]
    print(f"[INFO] Contatos monitorados: {contatos}")
    return contatos

# ─────────────────────────────────────────
# INICIA CHROME (headless, Square Cloud)
# ─────────────────────────────────────────
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
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(chromedriver_path)
    driver  = webdriver.Chrome(service=service, options=options)
    return driver

# ─────────────────────────────────────────
# ABRE O WHATSAPP WEB E VERIFICA SESSÃO
# ─────────────────────────────────────────
def abrir_whatsapp(driver):
    driver.get("https://web.whatsapp.com")
    print("[INFO] Aguardando carregamento do WhatsApp Web...")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            )
        )
        print("[INFO] WhatsApp Web carregado com sessão salva!")
    except TimeoutException:
        print("[ERRO] Sessão expirada ou não encontrada.")
        print("[ERRO] Rode o login_unico.py localmente e suba a pasta chrome_session/")
        driver.quit()
        sys.exit(1)

# ─────────────────────────────────────────
# ABRE O GRUPO
# ─────────────────────────────────────────
def abrir_grupo(driver, nome_grupo):
    print(f"[INFO] Procurando grupo: {nome_grupo}")
    try:
        search = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
            )
        )
        search.click()
        time.sleep(0.5)
        search.clear()
        search.send_keys(nome_grupo)
        time.sleep(2)

        grupo = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f'//span[@title="{nome_grupo}"]')
            )
        )
        grupo.click()
        print(f"[INFO] Grupo '{nome_grupo}' aberto!")
        time.sleep(2)
        return True
    except TimeoutException:
        print(f"[ERRO] Grupo '{nome_grupo}' não encontrado!")
        return False

# ─────────────────────────────────────────
# AGUARDA NOVA MENSAGEM DE UM CONTATO
# ─────────────────────────────────────────
def aguardar_nova_mensagem(driver, contatos, ultima_id):
    print("[BOT] Aguardando nova mensagem...\n")
    while True:
        try:
            mensagens = driver.find_elements(
                By.XPATH, '//div[contains(@class,"message-in")]'
            )
            if mensagens:
                ultima = mensagens[-1]

                try:
                    remetente = ultima.find_element(
                        By.XPATH, './/span[contains(@class,"_ahxt")]'
                    ).text.strip()
                except NoSuchElementException:
                    remetente = ""

                id_msg = ultima.get_attribute("data-id") or ultima.text

                if remetente in contatos and id_msg != ultima_id:
                    print(f"[BOT] Nova mensagem de '{remetente}' detectada!")
                    return remetente, ultima, id_msg

        except Exception as e:
            print(f"[ERRO] ao monitorar: {e}")

        time.sleep(2)

# ─────────────────────────────────────────
# RESPONDE COM REPLY  ← lógica do projeto local
# ─────────────────────────────────────────
def responder_com_reply(driver, elemento_mensagem):
    try:
        # 1 — Scroll para centralizar a mensagem
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            elemento_mensagem
        )
        time.sleep(0.3)

        # 2 — Hover no container da mensagem para revelar a seta
        div_nome = elemento_mensagem.find_element(
            By.XPATH, './/div[contains(@class,"_am2m")]'
        )
        ActionChains(driver).move_to_element(div_nome).perform()
        time.sleep(0.6)

        # 3 — Clica na seta via JS
        seta = elemento_mensagem.find_element(
            By.XPATH, './/span[@data-icon="ic-chevron-down-menu"]'
        )
        driver.execute_script("arguments[0].click();", seta)
        time.sleep(0.4)

        # 4 — Clica em Reply via JS
        btn_reply = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, '//span[@data-icon="reply-refreshed"]')
            )
        )
        driver.execute_script("arguments[0].click();", btn_reply)
        time.sleep(0.4)

        # 5 — Foca na caixa de texto do footer
        caixa = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//footer//div[@contenteditable='true']")
            )
        )
        driver.execute_script("arguments[0].focus();", caixa)
        time.sleep(0.2)

        # 6 — Limpa, digita e envia
        caixa.send_keys(Keys.CONTROL + "a")
        caixa.send_keys(Keys.DELETE)
        caixa.send_keys("Eu")
        caixa.send_keys(Keys.ENTER)

        print("[✓] 'Eu' enviado via reply!")
        return True

    except Exception as e:
        print(f"[ERRO] Falha ao responder: {e}")
        return False

# ─────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────
def main():
    contatos = carregar_contatos()
    if not contatos:
        print("[ERRO] Nenhum contato para monitorar. Adicione nomes em 'contatos.txt' e reinicie.")
        return

    driver = iniciar_driver()
    abrir_whatsapp(driver)

    if not abrir_grupo(driver, NOME_GRUPO):
        driver.quit()
        return

    print(f"\n[BOT] Monitorando grupo '{NOME_GRUPO}'...")
    print(f"[BOT] Contatos monitorados: {contatos}\n")

    ultima_id = None

    while True:
        try:
            remetente, elemento, ultima_id = aguardar_nova_mensagem(
                driver, contatos, ultima_id
            )
            print(f"[BOT] Respondendo mensagem de '{remetente}'...")
            responder_com_reply(driver, elemento)

        except KeyboardInterrupt:
            print("\n[BOT] Encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"[ERRO] {e}")
            time.sleep(3)

    driver.quit()

if __name__ == "__main__":
    main()
