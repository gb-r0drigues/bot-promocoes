# ═══════════════════════════════════════════════════════════
#  telegram_sender.py — Envia promoções para o canal Telegram
# ═══════════════════════════════════════════════════════════

import requests
import time
import logging
from config import TELEGRAM_TOKEN, TELEGRAM_CANAL
from ml_scraper import formatar_mensagem

log = logging.getLogger(__name__)

BASE_TELEGRAM = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ─── Enviar foto com legenda ─────────────────────────────────

def enviar_produto(produto: dict) -> bool:
    """
    Envia o produto como foto + texto formatado para o canal.
    Retorna True se enviado com sucesso, False caso contrário.
    """
    mensagem = formatar_mensagem(produto, plataforma="telegram")
    imagem   = produto.get("imagem", "")

    try:
        if imagem:
            sucesso = _enviar_com_foto(imagem, mensagem)
        else:
            sucesso = _enviar_so_texto(mensagem)

        if sucesso:
            log.info(f"[Telegram] ✅ Enviado: {produto['titulo'][:60]}...")
        return sucesso

    except Exception as e:
        log.error(f"[Telegram] ❌ Erro ao enviar {produto['id']}: {e}")
        return False

# ─── Enviar foto + texto ─────────────────────────────────────

def _enviar_com_foto(url_imagem: str, legenda: str) -> bool:
    """Envia mensagem com foto usando sendPhoto."""
    url = f"{BASE_TELEGRAM}/sendPhoto"

    payload = {
        "chat_id":    TELEGRAM_CANAL,
        "photo":      url_imagem,
        "caption":    legenda[:1024],        # Telegram limita legenda a 1024 chars
        "parse_mode": "Markdown",
    }

    response = requests.post(url, json=payload, timeout=20)

    if response.status_code == 200:
        return True

    # Se a foto falhou (URL inválida), tenta só texto
    if response.status_code in (400, 413):
        log.warning("[Telegram] Foto inválida, enviando só texto...")
        return _enviar_so_texto(legenda)

    # Rate limit — espera e tenta novamente
    if response.status_code == 429:
        retry_after = response.json().get("parameters", {}).get("retry_after", 30)
        log.warning(f"[Telegram] Rate limit. Aguardando {retry_after}s...")
        time.sleep(retry_after)
        return _enviar_com_foto(url_imagem, legenda)

    log.error(f"[Telegram] Erro HTTP {response.status_code}: {response.text[:200]}")
    return False

# ─── Enviar só texto ─────────────────────────────────────────

def _enviar_so_texto(mensagem: str) -> bool:
    """Envia mensagem de texto simples."""
    url = f"{BASE_TELEGRAM}/sendMessage"

    payload = {
        "chat_id":                  TELEGRAM_CANAL,
        "text":                     mensagem[:4096],
        "parse_mode":               "Markdown",
        "disable_web_page_preview": False,
    }

    response = requests.post(url, json=payload, timeout=20)

    if response.status_code == 200:
        return True

    log.error(f"[Telegram] Erro ao enviar texto: {response.status_code} — {response.text[:200]}")
    return False

# ─── Enviar múltiplos produtos ───────────────────────────────

def enviar_lista_produtos(produtos: list, intervalo_segundos: int = 3) -> dict:
    """
    Envia uma lista de produtos com intervalo entre cada envio.
    Retorna resumo: {"enviados": N, "falhas": N}
    """
    enviados = 0
    falhas   = 0

    for produto in produtos:
        sucesso = enviar_produto(produto)

        if sucesso:
            enviados += 1
        else:
            falhas += 1

        # Pausa entre envios para não bater no rate limit
        time.sleep(intervalo_segundos)

    log.info(f"[Telegram] Ciclo concluído — ✅ {enviados} enviados | ❌ {falhas} falhas")
    return {"enviados": enviados, "falhas": falhas}

# ─── Enviar mensagem de status ───────────────────────────────

def enviar_status(mensagem: str):
    """Envia uma mensagem de texto livre (para avisos/status)."""
    _enviar_so_texto(mensagem)

# ─── Testar conexão ──────────────────────────────────────────

def testar_conexao() -> bool:
    """Testa se o token do bot é válido."""
    try:
        url = f"{BASE_TELEGRAM}/getMe"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            bot = response.json()["result"]
            log.info(f"[Telegram] Conectado como @{bot['username']} ✅")
            return True

        log.error(f"[Telegram] Token inválido: {response.status_code}")
        return False

    except Exception as e:
        log.error(f"[Telegram] Falha na conexão: {e}")
        return False
