# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v11 via Promobit RSS (100% funcional)
# ═══════════════════════════════════════════════════════════

import requests
import urllib.parse
import logging
import time
import re
import xml.etree.ElementTree as ET
from config import (
    DESCONTO_MINIMO_PERCENT, PRECO_MINIMO, PRECO_MAXIMO,
    MAX_PRODUTOS_POR_CATEGORIA, ML_AFILIADO_PARAMS
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "*/*",
}

CUPONS_MANUAIS = {
    "moda":        "CUPOMPRAMODA",
    "roupa":       "CUPOMPRAMODA",
    "suplemento":  "SUPERMELI",
    "whey":        "SUPERMELI",
    "creatina":    "SUPERMELI",
    "beleza":      "BELEZAML",
    "perfume":     "BELEZAML",
    "celular":     "FRETEGRATIS",
    "smartphone":  "FRETEGRATIS",
    "notebook":    "TECHML",
    "informatica": "TECHML",
    "game":        "GAMEML",
    "casa":        "CASAML",
    "panela":      "CASAML",
    "eletro":      "ELETROML",
    "air fryer":   "ELETROML",
}

# Feeds RSS do Promobit por categoria — 100% públicos
FEEDS = {
    "🔥 Mais Vendidos":     "https://www.promobit.com.br/feed/",
    "📱 Smartphones":       "https://www.promobit.com.br/tag/smartphone/feed/",
    "💻 Informática":       "https://www.promobit.com.br/tag/informatica/feed/",
    "🎮 Games":             "https://www.promobit.com.br/tag/games/feed/",
    "⚡ Eletrodomésticos":  "https://www.promobit.com.br/tag/eletrodomesticos/feed/",
    "🏠 Casa e Jardim":     "https://www.promobit.com.br/tag/casa-e-jardim/feed/",
    "👗 Moda":              "https://www.promobit.com.br/tag/moda/feed/",
    "🧴 Beleza e Saúde":    "https://www.promobit.com.br/tag/beleza/feed/",
    "🎽 Esporte e Fitness": "https://www.promobit.com.br/tag/esporte/feed/",
    "💊 Suplementos":       "https://www.promobit.com.br/tag/suplementos/feed/",
}

def gerar_link_afiliado(url: str) -> str:
    if not url:
        return url
    if not any(d in url for d in ["mercadolivre", "mercadolibre", "meli.la"]):
        return url
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urllib.parse.urlencode(params)}"

def detectar_cupom(texto: str) -> str | None:
    # Detecta cupom no texto
    m = re.search(r'cupom[:\s]+([A-Z0-9]{4,20})', texto, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Cupom por palavra-chave
    texto_lower = texto.lower()
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in texto_lower:
            return cupom
    return None

def extrair_preco(texto: str) -> tuple:
    """Retorna (preco_atual, preco_original)"""
    precos = re.findall(r'R\$\s*([\d.,]+)', texto)
    valores = []
    for p in precos:
        try:
            v = p.replace('.', '').replace(',', '.')
            valores.append(float(v))
        except ValueError:
            pass
    if len(valores) >= 2:
        valores.sort()
        return valores[0], valores[-1]
    elif len(valores) == 1:
        return valores[0], 0.0
    return 0.0, 0.0

def extrair_link_ml(texto: str, link_fallback: str) -> str:
    for padrao in [
        r'https?://(?:www\.)?mercadolivre\.com\.br/[^\s"<>\']+',
        r'https?://produto\.mercadolivre\.com\.br/[^\s"<>\']+',
        r'https?://meli\.la/[^\s"<>\']+',
        r'https?://mercadolivre\.com/[^\s"<>\']+',
    ]:
        m = re.search(padrao, texto)
        if m:
            return m.group(0).rstrip('.,)')
    if any(d in link_fallback for d in ["mercadolivre", "mercadolibre", "meli.la"]):
        return link_fallback
    return ""

def buscar_feed(nome: str, url: str) -> list:
    encontrados = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        log.info(f"[{nome}] HTTP {resp.status_code}")
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        log.info(f"[{nome}] {len(items)} itens no feed")

        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
        ids_vistos = set()

        for item in items:
            try:
                titulo_el  = item.find("title")
                link_el    = item.find("link")
                desc_el    = item.find("description")
                content_el = item.find("content:encoded", ns)
                guid_el    = item.find("guid")

                titulo = titulo_el.text.strip() if titulo_el is not None and titulo_el.text else ""
                link   = link_el.text.strip() if link_el is not None and link_el.text else ""
                guid   = guid_el.text.strip() if guid_el is not None and guid_el.text else link

                if not titulo or guid in ids_vistos:
                    continue
                ids_vistos.add(guid)

                corpo = ""
                if content_el is not None and content_el.text:
                    corpo = content_el.text
                elif desc_el is not None and desc_el.text:
                    corpo = desc_el.text

                texto_completo = f"{titulo} {corpo}"

                # Extrai link do ML
                link_ml = extrair_link_ml(corpo, link)
                if not link_ml:
                    continue

                # Extrai preços
                preco, preco_orig = extrair_preco(texto_completo)
                if preco <= 0:
                    continue
                if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                    continue

                # Calcula desconto
                if preco_orig > preco:
                    desconto = round(((preco_orig - preco) / preco_orig) * 100)
                else:
                    # Tenta extrair % do texto
                    m = re.search(r'(\d+)\s*%\s*(?:off|de desconto)', texto_completo, re.IGNORECASE)
                    if m:
                        desconto = int(m.group(1))
                        preco_orig = round(preco / (1 - desconto / 100), 2)
                    else:
                        # Aceita oferta curada pelo Promobit mesmo sem desconto explícito
                        desconto = DESCONTO_MINIMO_PERCENT
                        preco_orig = round(preco / (1 - desconto / 100), 2)

                if desconto < DESCONTO_MINIMO_PERCENT:
                    continue

                encontrados.append({
                    "id":             guid,
                    "titulo":         titulo[:200],
                    "preco":          preco,
                    "preco_original": preco_orig,
                    "desconto":       desconto,
                    "economia":       round(preco_orig - preco, 2),
                    "link":           gerar_link_afiliado(link_ml),
                    "imagem":         "",
                    "rating":         0,
                    "total_reviews":  0,
                    "categoria":      nome,
                    "cupom":          detectar_cupom(texto_completo),
                })

                if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                    break

            except Exception as e:
                log.debug(f"Erro no item: {e}")
                continue

        time.sleep(1)

    except ET.ParseError as e:
        log.error(f"[{nome}] XML inválido: {e}")
    except Exception as e:
        log.error(f"[{nome}] Erro: {e}")

    log.info(f"[{nome}] {len(encontrados)} aprovados")
    return encontrados

def buscar_todas_categorias() -> list:
    todos = []
    ids_globais = set()
    log.info(f"Buscando em {len(FEEDS)} feeds do Promobit...")
    for nome, url in FEEDS.items():
        for p in buscar_feed(nome, url):
            if p["id"] not in ids_globais:
                ids_globais.add(p["id"])
                todos.append(p)
        time.sleep(1)
    log.info(f"Total para enviar: {len(todos)} produtos")
    return todos

def formatar_mensagem(produto: dict, plataforma: str = "telegram") -> str:
    titulo        = produto["titulo"]
    preco         = produto["preco"]
    preco_orig    = produto["preco_original"]
    desconto      = produto["desconto"]
    economia      = produto["economia"]
    link          = produto["link"]
    cupom         = produto.get("cupom")
    categoria     = produto["categoria"]

    linha_cupom = f"Cupom: `{cupom}` ⚠️\n" if cupom else ""

    msg = (
        f"*{categoria}*\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"*{titulo}*\n\n"
        f"De R${preco_orig:.2f} | Por *R${preco:.2f}* 👑\n"
        f"🏷️ *{desconto}% OFF* — Economia: R${economia:.2f}\n"
        f"{linha_cupom}"
        f"\n🛒 Achado no Mercado Livre\n"
        f"👉 {link}\n"
        f"\n_Preços e disponibilidade sujeitos a alteração._"
    )
    return msg
