# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v6 API de texto (sem auth, confiável)
# ═══════════════════════════════════════════════════════════

import requests
import urllib.parse
import logging
import time
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

BASE = "https://api.mercadolibre.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; bot-promocoes/1.0)",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "x-platform": "MP",
}

CUPONS_MANUAIS = {
    "moda":           "CUPOMPRAMODA",
    "moda feminina":  "MODAML",
    "moda masculina": "MODAML",
    "suplementos":    "SUPERMELI",
    "saude":          "SAUDEML",
    "beleza":         "BELEZAML",
    "eletronicos":    "ELETROML",
    "smartphones":    "FRETEGRATIS",
    "informatica":    "TECHML",
    "games":          "GAMEML",
    "casa":           "CASAML",
}

# ─── Termos de busca por categoria ──────────────────────────
BUSCAS = {
    "💊 Suplementos":       ["whey protein", "creatina", "suplemento vitamina"],
    "👗 Moda Feminina":     ["vestido feminino", "blusa feminina", "calça feminina"],
    "👔 Moda Masculina":    ["camiseta masculina", "calça jeans masculina", "camisa social"],
    "📱 Smartphones":       ["smartphone samsung", "iphone", "celular xiaomi"],
    "💻 Informática":       ["notebook", "monitor gamer", "teclado mecânico"],
    "🎮 Games":             ["controle ps5", "jogo xbox", "headset gamer"],
    "🏠 Casa e Jardim":     ["organizador casa", "jogo de cama", "panela"],
    "⚡ Eletrodomésticos":  ["air fryer", "aspirador pó", "liquidificador"],
    "🎽 Esporte e Fitness": ["tênis corrida", "legging academia", "halteres"],
    "🧴 Beleza e Saúde":    ["perfume feminino", "hidratante corporal", "protetor solar"],
    "🔥 Mais Vendidos":     ["mais vendido promoção", "oferta relâmpago"],
    "📦 Ofertas do Dia":    ["oferta do dia", "desconto especial"],
}

def gerar_link_afiliado(url: str) -> str:
    if not url:
        return url
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urllib.parse.urlencode(params)}"

def detectar_cupom(nome: str) -> str | None:
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in nome.lower():
            return cupom
    return None

def _extrair_produto(item: dict, categoria: str) -> dict | None:
    try:
        preco      = float(item.get("price", 0))
        preco_orig = float(item.get("original_price") or 0)

        if not preco_orig or preco_orig <= preco:
            return None
        desconto = round(((preco_orig - preco) / preco_orig) * 100)
        if desconto < DESCONTO_MINIMO_PERCENT:
            return None
        if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
            return None

        thumb = item.get("thumbnail", "")
        thumb = thumb.replace("I.jpg", "O.jpg").replace("http://", "https://")

        avs = item.get("reviews", {}) or {}

        return {
            "id":             item.get("id", ""),
            "titulo":         item.get("title", ""),
            "preco":          preco,
            "preco_original": preco_orig,
            "desconto":       desconto,
            "economia":       round(preco_orig - preco, 2),
            "link":           gerar_link_afiliado(item.get("permalink", "")),
            "imagem":         thumb,
            "rating":         avs.get("rating_average", 0),
            "total_reviews":  avs.get("total", 0),
            "categoria":      categoria,
            "cupom":          detectar_cupom(categoria),
        }
    except Exception as e:
        log.debug(f"Erro extraindo produto: {e}")
        return None

def buscar_por_termo(termo: str, categoria: str) -> list:
    encontrados = []
    try:
        resp = requests.get(
            f"{BASE}/sites/MLB/search",
            params={"q": termo, "sort": "best_seller", "limit": 50},
            headers=HEADERS,
            timeout=20,
        )
        log.debug(f"  [{termo}] HTTP {resp.status_code}")

        if resp.status_code != 200:
            return []

        for item in resp.json().get("results", []):
            p = _extrair_produto(item, categoria)
            if p:
                encontrados.append(p)
            if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                break

    except Exception as e:
        log.error(f"Erro na busca '{termo}': {e}")

    return encontrados

def buscar_produtos_categoria(nome: str, termos: list) -> list:
    todos = []
    ids_vistos = set()

    for termo in termos:
        produtos = buscar_por_termo(termo, nome)
        for p in produtos:
            if p["id"] not in ids_vistos:
                ids_vistos.add(p["id"])
                todos.append(p)
        time.sleep(1)
        if len(todos) >= MAX_PRODUTOS_POR_CATEGORIA:
            break

    log.info(f"[{nome}] {len(todos)} aprovados")
    return todos[:MAX_PRODUTOS_POR_CATEGORIA]

def buscar_todas_categorias() -> list:
    todos = []
    log.info(f"Buscando em {len(BUSCAS)} categorias...")
    for nome, termos in BUSCAS.items():
        todos.extend(buscar_produtos_categoria(nome, termos))
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
    rating        = produto.get("rating", 0)
    total_reviews = produto.get("total_reviews", 0)

    linha_cupom  = f"Cupom: `{cupom}` ⚠️\n" if cupom else ""
    linha_rating = ""
    if rating and total_reviews > 0:
        linha_rating = f"{'⭐' * min(round(rating), 5)} ({total_reviews} avaliações)\n"

    msg = (
        f"*{categoria}*\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"*{titulo}*\n\n"
        f"De R${preco_orig:.2f} | Por *R${preco:.2f}* 👑\n"
        f"🏷️ *{desconto}% OFF* — Economia: R${economia:.2f}\n"
        f"{linha_cupom}{linha_rating}"
        f"\n🛒 Achado no Mercado Livre\n"
        f"👉 {link}\n"
        f"\n_Preços e disponibilidade sujeitos a alteração._"
    )
    return msg
