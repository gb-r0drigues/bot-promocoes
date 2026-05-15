# ═══════════════════════════════════════════════════════════
#  whatsapp_sender.py — Envia promoções para grupo WhatsApp
#  Usa Evolution API (solução brasileira, gratuita)
# ═══════════════════════════════════════════════════════════

import requests
import time
import logging
import base64
from config import EVOLUTION_URL, EVOLUTION_APIKEY, WA_INSTANCIA, WA_GRUPO_ID
from ml_scraper import formatar_mensagem

log = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/json",
    "apikey":       EVOLUTION_APIKEY,
}

# ─── Enviar produto ──────────────────────────────────────────

def enviar_produto(produto: dict) -> bool:
    """
    Envia o produto como imagem + texto para o grupo WhatsApp.
    """
    mensagem = formatar_mensagem(produto, plataforma="whatsapp")
    imagem   = produto.get("imagem", "")

    try:
        if imagem:
            sucesso = _enviar_com_imagem(imagem, mensagem)
        else:
            sucesso = _enviar_so_texto(mensagem)

        if sucesso:
            log.info(f"[WhatsApp] ✅ Enviado: {produto['titulo'][:60]}...")
        return sucesso

    except Exception as e:
        log.error(f"[WhatsApp] ❌ Erro ao enviar {produto['id']}: {e}")
        return False

# ─── Enviar imagem + texto ────────────────────────────────────

def _enviar_com_imagem(url_imagem: str, legenda: str) -> bool:
    """Envia mensagem com imagem via Evolution API."""
    url = f"{EVOLUTION_URL}/message/sendMedia/{WA_INSTANCIA}"

    payload = {
        "number":    WA_GRUPO_ID,
        "mediatype": "image",
        "media":     url_imagem,
        "caption":   legenda,
    }

    response = requests.post(url, json=payload, headers=HEADERS, timeout=30)

    if response.status_code in (200, 201):
        return True

    # Se imagem falhou, tenta só texto
    if response.status_code in (400, 422):
        log.warning("[WhatsApp] Imagem inválida, enviando só texto...")
        return _enviar_so_texto(legenda)

    log.error(f"[WhatsApp] Erro HTTP {response.status_code}: {response.text[:200]}")
    return False

# ─── Enviar só texto ─────────────────────────────────────────

def _enviar_so_texto(mensagem: str) -> bool:
    """Envia mensagem de texto simples."""
    url = f"{EVOLUTION_URL}/message/sendText/{WA_INSTANCIA}"

    payload = {
        "number": WA_GRUPO_ID,
        "text":   mensagem,
    }

    response = requests.post(url, json=payload, headers=HEADERS, timeout=20)

    if response.status_code in (200, 201):
        return True

    log.error(f"[WhatsApp] Erro texto: {response.status_code} — {response.text[:200]}")
    return False

# ─── Enviar múltiplos produtos ───────────────────────────────

def enviar_lista_produtos(produtos: list, intervalo_segundos: int = 5) -> dict:
    """
    Envia lista de produtos com intervalo.
    WhatsApp precisa de intervalo maior que Telegram.
    """
    enviados = 0
    falhas   = 0

    for produto in produtos:
        sucesso = enviar_produto(produto)

        if sucesso:
            enviados += 1
        else:
            falhas += 1

        time.sleep(intervalo_segundos)

    log.info(f"[WhatsApp] Ciclo concluído — ✅ {enviados} | ❌ {falhas}")
    return {"enviados": enviados, "falhas": falhas}

# ─── Testar conexão ──────────────────────────────────────────

def testar_conexao() -> bool:
    """Verifica se a instância WhatsApp está conectada."""
    try:
        url = f"{EVOLUTION_URL}/instance/connectionState/{WA_INSTANCIA}"
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            estado = response.json().get("instance", {}).get("state", "desconhecido")
            if estado == "open":
                log.info("[WhatsApp] Instância conectada ✅")
                return True
            else:
                log.warning(f"[WhatsApp] Instância {estado} — escaneie o QR Code")
                return False

        log.error(f"[WhatsApp] Erro ao verificar instância: {response.status_code}")
        return False

    except Exception as e:
        log.error(f"[WhatsApp] Falha na conexão: {e}")
        return False
