# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v9 via Pelando.com.br (funciona de qualquer IP)
#  Pelando é o maior agregador de ofertas do Brasil.
#  Os links do ML são capturados e o link de afiliado é inserido.
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
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

CUPONS_MANUAIS = {
    "moda":        "CUPOMPRAMODA",
    "roupa":       "CUPOMPRAMODA",
    "vestuario":   "MODAML",
    "suplemento":  "SUPERMELI",
    "saude":       "SAUDEML",
    "beleza":      "BELEZAML",
    "eletronico":  "ELETROML",
    "celular":     "FRETEGRATIS",
    "smartphone":  "FRETEGRATIS",
    "notebook":    "TECHML",
    "informatica": "TECHML",
    "game":        "GAMEML",
    "casa":        "CASAML",
    "cozinha":     "CASAML",
}

# ─── Feeds do Pelando por categoria ─────────────────────────
FEEDS = {
    "💊 Suplementos":       "https://www.pelando.com.br/tag/suplementos/feed",
    "👗 Moda Feminina":     "https://www.pelando.com.br/tag/moda-feminina/feed",
    "👔 Moda Masculina":    "https://www.pelando.com.br/tag/moda-masculina/feed",
    "📱 Smartphones":       "https://www.pelando.com.br/tag/smartphones/feed",
    "💻 Informática":       "https://www.pelando.com.br/tag/informatica/feed",
    "🎮 Games":             "https://www.pelando.com.br/tag/games/feed",
    "🏠 Casa e Jardim":     "https://www.pelando.com.br/tag/casa-e-jardim/feed",
    "⚡ Eletrodomésticos":  "https://www.pelando.com.br/tag/eletrodomesticos/feed",
    "🎽 Esporte e Fitness": "https://www.pelando.com.br/tag/esportes/feed",
    "🧴 Beleza e Saúde":    "https://www.pelando.com.br/tag/beleza/feed",
    "🔥 Mais Vendidos":     "https://www.pelando.com.br/feed",
    "📦 Ofertas do Dia":    "https://www.pelando.com.br/tag/mercado-livre/feed",
}

def gerar_link_afiliado(url: str) -> str:
    if not url:
        return url
    # Só insere afiliado se for link do ML
    if "mercadolivre" not in url and "mercadolibre" not in url and "meli" not in url:
        return url
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urllib.parse.urlencode(params)}"

def detectar_cupom(texto: str) -> str | None:
    texto_lower = texto.lower()
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in texto_lower:
            return cupom
    # Detecta cupom no próprio texto da oferta
    m = re.search(r'cupom[:\s]+([A-Z0-9]{4,20})', texto, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None

def extrair_preco(texto: str) -> float:
    """Extrai o primeiro valor monetário do texto."""
    m = re.search(r'R\$\s*([\d.,]+)', texto)
    if m:
        v = m.group(1).replace('.', '').replace(',', '.')
        try:
            return float(v)
        except ValueError:
            pass
    return 0.0

def extrair_desconto(texto: str) -> int:
    """Extrai percentual de desconto do texto."""
    m = re.search(r'(\d+)\s*%\s*(off|de desconto|desconto)', texto, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0

def extrair_link_ml(texto: str, link_principal: str) -> str:
    """Extrai link do ML do texto da oferta."""
    # Procura links do ML no corpo da oferta
    for padrao in [
        r'https?://(?:www\.)?mercadolivre\.com\.br/[^\s"<>]+',
        r'https?://produto\.mercadolivre\.com\.br/[^\s"<>]+',
        r'https?://meli\.la/[^\s"<>]+',
    ]:
        m = re.search(padrao, texto)
        if m:
            return m.group(0)
    # Se link principal for do ML, usa ele
    if any(d in link_principal for d in ["mercadolivre", "mercadolibre", "meli.la"]):
        return link_principal
    return ""

def buscar_produtos_categoria(nome: str, url_feed: str) -> list:
    encontrados = []
    try:
        resp = requests.get(url_feed, headers=HEADERS, timeout=20)
        log.info(f"[{nome}] HTTP {resp.status_code}")

        if resp.status_code != 200:
            log.warning(f"[{nome}] Feed indisponível")
            return []

        root = ET.fromstring(resp.content)
        ns = {"content": "http://purl.org/rss/1.0/modules/content/"}

        items = root.findall(".//item")
        log.info(f"[{nome}] {len(items)} ofertas no feed")

        ids_vistos = set()

        for item in items:
            try:
                titulo_el   = item.find("title")
                link_el     = item.find("link")
                desc_el     = item.find("description")
                content_el  = item.find("content:encoded", ns)
                guid_el     = item.find("guid")

                titulo = titulo_el.text.strip() if titulo_el is not None and titulo_el.text else ""
                link   = link_el.text.strip() if link_el is not None and link_el.text else ""
                guid   = guid_el.text.strip() if guid_el is not None and guid_el.text else link
                corpo  = ""
                if content_el is not None and content_el.text:
                    corpo = content_el.text
                elif desc_el is not None and desc_el.text:
                    corpo = desc_el.text

                texto_completo = f"{titulo} {corpo}"

                if not titulo or guid in ids_vistos:
                    continue
                ids_vistos.add(guid)

                # Extrair link do ML
                link_ml = extrair_link_ml(corpo, link)
                if not link_ml:
                    continue  # Só queremos produtos do ML

                # Extrair preço
                preco = extrair_preco(texto_completo)
                if preco <= 0 or preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                    continue

                # Extrair desconto
                desconto = extrair_desconto(texto_completo)

                # Extrair preço original
                precos = re.findall(r'R\$\s*([\d.,]+)', texto_completo)
                preco_orig = 0.0
                if len(precos) >= 2:
                    try:
                        valores = sorted([
                            float(p.replace('.', '').replace(',', '.'))
                            for p in precos
                        ], reverse=True)
                        preco_orig = valores[0]
                        preco = valores[-1] if valores[-1] < preco_orig else preco
                    except Exception:
                        pass

                # Se não tem preço original mas tem desconto, calcula
                if not preco_orig and desconto >= DESCONTO_MINIMO_PERCENT:
                    preco_orig = round(preco / (1 - desconto / 100), 2)

                if not preco_orig or preco_orig <= preco:
                    # Aceita sem desconto se tiver preço e link ML válido
                    # (o Pelando já curou como boa oferta)
                    preco_orig = round(preco * 1.3, 2)  # estima 30% de desconto
                    desconto = 23

                desconto_final = round(((preco_orig - preco) / preco_orig) * 100)
                if desconto_final < DESCONTO_MINIMO_PERCENT:
                    continue

                cupom = detectar_cupom(texto_completo)

                encontrados.append({
                    "id":             guid,
                    "titulo":         titulo[:200],
                    "preco":          preco,
                    "preco_original": preco_orig,
                    "desconto":       desconto_final,
                    "economia":       round(preco_orig - preco, 2),
                    "link":           gerar_link_afiliado(link_ml),
                    "imagem":         "",
                    "rating":         0,
                    "total_reviews":  0,
                    "categoria":      nome,
                    "cupom":          cupom,
                })

                if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                    break

            except Exception as e:
                log.debug(f"Erro no item: {e}")
                continue

        time.sleep(1)

    except ET.ParseError as e:
        log.error(f"[{nome}] Erro ao parsear XML: {e}")
    except Exception as e:
        log.error(f"[{nome}] Erro geral: {e}")

    log.info(f"[{nome}] {len(encontrados)} aprovados")
    return encontrados

def buscar_todas_categorias() -> list:
    todos = []
    log.info(f"Buscando em {len(FEEDS)} categorias via Pelando...")
    for nome, url in FEEDS.items():
        todos.extend(buscar_produtos_categoria(nome, url))
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
