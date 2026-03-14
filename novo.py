import time
import os
import sys
import json
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────
NOME_GRUPO = "FLASH DELIVERY JIPA 2"
ARQUIVO_CONTATOS = "contatos.txt"
ARQUIVO_COOKIES = "wa_cookies.json"

# ─────────────────────────────────────────
# CARREGA CONTATOS MONITORADOS
# ─────────────────────────────────────────
def carregar_contatos():
    if not os.path.exists(ARQUIVO_CONTATOS):
        print(f"[AVISO] Arquivo '{ARQUIVO_CONTATOS}' não encontrado.")
        return []
    with open(ARQUIVO_CONTATOS, "r", encoding="utf-8") as f:
        contatos = [linha.strip() for linha in f if linha.strip()]
    print(f"[INFO] {len(contatos)} contatos monitorados.")
    return contatos

# ─────────────────────────────────────────
# INICIA CHROME
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
    print("[INFO] Modo headless ativado")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ─────────────────────────────────────────
# SALVA COOKIES EM ARQUIVO
# ─────────────────────────────────────────
def salvar_cookies(driver):
    cookies = driver.get_cookies()
    with open(ARQUIVO_COOKIES, "w") as f:
        json.dump(cookies, f)
    print(f"[INFO] {len(cookies)} cookies salvos em '{ARQUIVO_COOKIES}'")

# ─────────────────────────────────────────
# CARREGA COOKIES DO ARQUIVO
# ─────────────────────────────────────────
def carregar_cookies(driver):
    if not os.path.exists(ARQUIVO_COOKIES):
        print("[INFO] Nenhum cookie salvo encontrado.")
        return False
    try:
        with open(ARQUIVO_COOKIES, "r") as f:
            cookies = json.load(f)
        # Abre o domínio primeiro antes de injetar cookies
        driver.get("https://web.whatsapp.com")
        time.sleep(3)
        for cookie in cookies:
            # Remove campos incompatíveis
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
            except Exception:
                pass
        print(f"[INFO] {len(cookies)} cookies carregados.")
        return True
    except Exception as e:
        print(f"[AVISO] Erro ao carregar cookies: {e}")
        return False

# ─────────────────────────────────────────
# EXIBE QR CODE NO TERMINAL
# ─────────────────────────────────────────
def exibir_qrcode_terminal(driver):
    try:
        import qrcode
        print("[INFO] Aguardando QR Code aparecer...")
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@data-ref]'))
        )
        qr_element = driver.find_element(By.XPATH, '//div[@data-ref]')
        qr_data = qr_element.get_attribute("data-ref")
        if not qr_data:
            print("[ERRO] Não foi possível extrair o QR Code.")
            return False

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        print("\n" + "=" * 50)
        print("  ESCANEIE: WhatsApp → 3 pontos → Aparelhos conectados → Conectar")
        print("=" * 50)
        matrix = qr.get_matrix()
        for row in matrix:
            linha = ""
            for cell in row:
                linha += "██" if cell else "  "
            print(linha)
        print("=" * 50)
        print("[INFO] Aguardando escaneamento (máx. 120 segundos)...")
        return True
    except Exception as e:
        print(f"[ERRO] ao exibir QR Code: {e}")
        return False

# ─────────────────────────────────────────
# ABRE O WHATSAPP WEB E AGUARDA LOGIN
# ─────────────────────────────────────────
def abrir_whatsapp(driver):
    print("[INFO] Carregando WhatsApp Web...")

    # Tenta usar cookies salvos primeiro
    tem_cookies = carregar_cookies(driver)

    if tem_cookies:
        # Recarrega a página com os cookies injetados
        driver.get("https://web.whatsapp.com")
        print("[INFO] Cookies carregados — verificando sessão...")
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
            )
            print("[✓] Sessão restaurada pelos cookies!")
            return
        except TimeoutException:
            print("[AVISO] Cookies inválidos ou expirados — pedindo novo QR Code...")

    # Sem cookies ou cookies inválidos — exibe QR Code
    driver.get("https://web.whatsapp.com")
    time.sleep(5)

    # Verifica se já está logado sem cookies
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] Já logado!")
        salvar_cookies(driver)
        return
    except TimeoutException:
        pass

    # Exibe QR Code e aguarda login
    if not exibir_qrcode_terminal(driver):
        driver.quit()
        sys.exit(1)

    try:
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] Login realizado!")
        salvar_cookies(driver)
        print("[INFO] Cookies salvos — nas próximas execuções não precisará escanear.")
        print("[AVISO] Faça commit do arquivo 'wa_cookies.json' para o GitHub!")
    except TimeoutException:
        print("[AVISO] QR Code expirou, tentando novamente...")
        exibir_qrcode_terminal(driver)
        WebDriverWait(driver, 120).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] Login realizado!")
        salvar_cookies(driver)

# ─────────────────────────────────────────
# ABRE O GRUPO
# ─────────────────────────────────────────
def abrir_grupo(driver, nome_grupo):
    print(f"[INFO] Procurando grupo: {nome_grupo}")
    try:
        search = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search.click()
        time.sleep(0.5)
        search.clear()
        search.send_keys(nome_grupo)
        time.sleep(2)
        grupo = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{nome_grupo}"]'))
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
            mensagens = driver.find_elements(By.XPATH, '//div[contains(@class,"message-in")]')
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
# RESPONDE COM REPLY
# ─────────────────────────────────────────
def responder_com_reply(driver, elemento_mensagem):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento_mensagem)
        time.sleep(0.2)
        div_nome = elemento_mensagem.find_element(By.XPATH, './/div[contains(@class,"_am2m")]')
        ActionChains(driver).move_to_element(div_nome).perform()
        time.sleep(0.6)
        seta = elemento_mensagem.find_element(By.XPATH, './/span[@data-icon="ic-chevron-down-menu"]')
        driver.execute_script("arguments[0].click();", seta)
        time.sleep(0.4)
        btn_reply = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, '//span[@data-icon="reply-refreshed"]'))
        )
        driver.execute_script("arguments[0].click();", btn_reply)
        time.sleep(0.4)
        caixa = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//footer//div[@contenteditable='true']"))
        )
        driver.execute_script("arguments[0].focus();", caixa)
        time.sleep(0.1)
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
        print("[ERRO] Nenhum contato para monitorar.")
        return

    driver = iniciar_driver()
    abrir_whatsapp(driver)

    if not abrir_grupo(driver, NOME_GRUPO):
        driver.quit()
        return

    print(f"\n[BOT] Monitorando grupo '{NOME_GRUPO}'...\n")

    ultima_id = None
    while True:
        try:
            remetente, elemento, ultima_id = aguardar_nova_mensagem(driver, contatos, ultima_id)
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
