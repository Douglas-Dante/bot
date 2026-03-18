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

# ─────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────
NOME_GRUPO = "FLASH DELIVERY JIPA 2"
ARQUIVO_CONTATOS = "contatos.txt"
PASTA_SESSAO = os.path.join(os.path.dirname(__file__), "chrome_session")

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
# INICIA CHROME COM SESSÃO SALVA
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
    print(f"[INFO] Usando sessão: {PASTA_SESSAO}")

    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ─────────────────────────────────────────
# ABRE O WHATSAPP WEB
# ─────────────────────────────────────────
def abrir_whatsapp(driver):
    driver.get("https://web.whatsapp.com")
    print("[INFO] Carregando WhatsApp Web...")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] WhatsApp Web carregado com sessão salva!")
    except TimeoutException:
        print("[ERRO] Sessão expirada. Execute o workflow 'Login WhatsApp' para renovar.")
        driver.quit()
        sys.exit(1)

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
# PEGA A ÚLTIMA MENSAGEM DO GRUPO
# ─────────────────────────────────────────
def pegar_ultima_mensagem(driver):
    try:
        mensagens = driver.find_elements(By.XPATH, '//div[contains(@class,"message-in")]')
        if not mensagens:
            return None, None
        ultima = mensagens[-1]
        try:
            remetente = ultima.find_element(
                By.XPATH, './/span[contains(@class,"_ahxt")]'
            ).text.strip()
        except NoSuchElementException:
            remetente = ""
        return remetente, ultima
    except Exception as e:
        print(f"[ERRO] ao pegar mensagem: {e}")
        return None, None

# ─────────────────────────────────────────
# DEBUG: imprime o HTML da mensagem
# para identificar os seletores corretos
# ─────────────────────────────────────────
def debug_html_mensagem(driver, elemento):
    try:
        html = elemento.get_attribute("outerHTML")
        # Imprime só os primeiros 3000 chars para não poluir o log
        print("\n[DEBUG HTML DA MENSAGEM]\n")
        print(html[:3000])
        print("\n[FIM DEBUG]\n")
    except Exception as e:
        print(f"[DEBUG ERRO] {e}")

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
        # ── 1: Scroll ──
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento_mensagem)
        time.sleep(0.3)

        # ── 2: Imprime HTML para debug (identifica seletores no Linux) ──
        debug_html_mensagem(driver, elemento_mensagem)

        # ── 3: Hover no container da mensagem para revelar a seta ──
        # Tenta _am2m primeiro, depois fallback para o próprio elemento
        try:
            alvo_hover = elemento_mensagem.find_element(
                By.XPATH, './/*[contains(@class,"_am2m") or contains(@class,"copyable-area") or contains(@class,"message-in")]'
            )
        except NoSuchElementException:
            alvo_hover = elemento_mensagem

        ActionChains(driver).move_to_element(alvo_hover).perform()
        time.sleep(0.8)

        # ── 4: Clica na seta (tenta múltiplos seletores) ──
        seta = None
        for xpath in [
            './/span[@data-icon="ic-chevron-down-menu"]',
            './/span[@data-icon="down-context"]',
            './/button[contains(@aria-label,"Menu")]',
        ]:
            try:
                seta = elemento_mensagem.find_element(By.XPATH, xpath)
                print(f"[INFO] Seta encontrada com: {xpath}")
                break
            except NoSuchElementException:
                continue

        if seta is None:
            # Fallback: busca globalmente a seta mais recente
            for xpath in [
                '//span[@data-icon="ic-chevron-down-menu"]',
                '//span[@data-icon="down-context"]',
            ]:
                try:
                    setas = driver.find_elements(By.XPATH, xpath)
                    if setas:
                        seta = setas[-1]
                        print(f"[INFO] Seta encontrada globalmente: {xpath}")
                        break
                except Exception:
                    continue

        if seta is None:
            print("[ERRO] Seta do menu não encontrada em nenhum seletor.")
            return False

        driver.execute_script("arguments[0].click();", seta)
        time.sleep(0.5)

        # ── 5: Clica em Reply ──
        btn_reply = None
        for xpath in [
            '//span[@data-icon="reply-refreshed"]',
            '//span[@data-icon="reply"]',
            '//li[.//span[text()="Responder"]]',
            '//li[.//span[text()="Reply"]]',
        ]:
            try:
                btn_reply = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                print(f"[INFO] Botão reply encontrado: {xpath}")
                break
            except TimeoutException:
                continue

        if btn_reply is None:
            print("[ERRO] Botão reply não encontrado.")
            return False

        driver.execute_script("arguments[0].click();", btn_reply)
        time.sleep(0.4)

        # ── 6: Digita "Eu" e envia ──
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
