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

NOME_GRUPO = "FLASH DELIVERY JIPA 2"
ARQUIVO_CONTATOS = "contatos.txt"
PASTA_SESSAO = os.path.join(os.path.dirname(__file__), "chrome_session")

def carregar_contatos():
    if not os.path.exists(ARQUIVO_CONTATOS):
        print(f"[AVISO] Arquivo '{ARQUIVO_CONTATOS}' não encontrado.")
        return []
    with open(ARQUIVO_CONTATOS, "r", encoding="utf-8") as f:
        contatos = [linha.strip() for linha in f if linha.strip()]
    print(f"[INFO] {len(contatos)} contatos monitorados.")
    return contatos

def iniciar_driver():
    chromedriver_path = chromedriver_autoinstaller.install()
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

def abrir_whatsapp(driver):
    driver.get("https://web.whatsapp.com")
    print("[INFO] Carregando WhatsApp Web...")
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        print("[✓] WhatsApp Web carregado!")
    except TimeoutException:
        print("[ERRO] Sessão expirada. Execute o workflow 'Login WhatsApp' para renovar.")
        driver.quit()
        sys.exit(1)

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

def responder_com_reply(driver, elemento_mensagem):
    try:
        # ── 1: Scroll para a mensagem ──
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento_mensagem)
        time.sleep(0.3)

        # ── 2: Hover via JS no elemento da mensagem ──
        driver.execute_script("""
            var el = arguments[0];
            el.dispatchEvent(new MouseEvent('mouseover', {bubbles: true, cancelable: true}));
            el.dispatchEvent(new MouseEvent('mouseenter', {bubbles: true, cancelable: true}));
            el.dispatchEvent(new MouseEvent('mousemove', {bubbles: true, cancelable: true}));
        """, elemento_mensagem)
        time.sleep(1.0)

        # ── 3: Busca a seta no container pai (_amj_) ──
        seta = None
        try:
            # A seta fica no container externo, não dentro da mensagem
            container = elemento_mensagem.find_element(By.XPATH, './ancestor::div[contains(@class,"focusable-list-item")]')
            seta = container.find_element(By.XPATH, './/span[@data-icon="ic-chevron-down-menu"]')
            print("[INFO] Seta encontrada no container pai")
        except Exception:
            pass

        if seta is None:
            # Fallback: busca global pela última seta visível
            setas = driver.find_elements(By.XPATH, '//span[@data-icon="ic-chevron-down-menu"]')
            if setas:
                seta = setas[-1]
                print("[INFO] Seta encontrada globalmente")

        if seta is None:
            print("[ERRO] Seta não encontrada.")
            return False

        driver.execute_script("arguments[0].click();", seta)
        time.sleep(0.6)

        # ── 4: Clica em Responder — tenta vários seletores ──
        btn_reply = None
        xpaths_reply = [
            '//span[@data-icon="reply-refreshed"]',
            '//span[@data-icon="reply"]',
            '//*[contains(@aria-label,"Reply")]',
            '//*[contains(@aria-label,"Responder")]',
            '//li[.//span[normalize-space()="Responder"]]',
            '//li[.//span[normalize-space()="Reply"]]',
            '//div[contains(@class,"_amj_")]//span[contains(@data-icon,"reply")]',
        ]
        for xpath in xpaths_reply:
            try:
                btn_reply = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                print(f"[INFO] Reply encontrado: {xpath}")
                break
            except TimeoutException:
                continue

        if btn_reply is None:
            # Último recurso: imprime o HTML do menu aberto para debug
            try:
                menu = driver.find_element(By.XPATH, '//ul[contains(@class,"_amj") or @role="menu"]')
                print(f"[DEBUG MENU] {menu.get_attribute('outerHTML')[:1000]}")
            except Exception:
                pass
            print("[ERRO] Botão reply não encontrado.")
            return False

        driver.execute_script("arguments[0].click();", btn_reply)
        time.sleep(0.4)

        # ── 5: Digita "Eu" e envia ──
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
