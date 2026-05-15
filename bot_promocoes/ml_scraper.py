# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v7 com tag=best_price e filtros ampliados
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
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

BUSCAS = {
    "💊 Suplementos":       ["whey protein", "creatina monohidratada", "bcaa aminoacido"],
    "👗 Moda Feminina":     ["vestido feminino", "conjunto feminino", "blusa feminina"],
    "👔 Moda Masculina":    ["camiseta masculina", "kit camisetas", "camisa masculina"],
    "📱 Smartphones":       ["smartphone samsung galaxy", "celular xiaomi", "iphone usado"],
    "💻 Informática":       ["notebook i5", "monitor led", "ssd 1tb"],
    "🎮 Games":             ["controle sem fio", "headset gamer", "cadeira gamer"],
    "🏠 Casa e Jardim":     ["jogo de panelas", "jogo de cama casal", "organizador guarda roupa"],
    "⚡ Eletrodomésticos":  ["air fryer digital", "fritadeira elétrica", "aspirador vertical"],
    "🎽 Esporte e Fitness": ["tênis esportivo", "kit halteres", "colchonete yoga"],
    "🧴 Beleza e Saúde":    ["perfume importado", "kit skincare", "protetor solar facial"],
    "🔥 Mais Vendidos":     ["kit presente", "fone bluetooth", "relogio smartwatch"],
    "📦 Ofertas do Dia":    ["ventilador turbo", "caixa de som bluetooth", "carregador rapido"],
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
        pid       = item.get("id", "")
        titulo    = item.get("title", "")
        preco     = float(item.get("price", 0))
        permalink = item.get("permalink", "")
        thumb     = item.get("thumbnail", "").replace("I.jpg", "O.jpg").replace("http://", "https://")
        avs       = item.get("reviews", {}) or {}

        if preco <= 0 or not permalink:
            return None
        if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
            return None

        # ── Tentar obter preço original de várias fontes ──────
        preco_orig = 0.0

        # Fonte 1: original_price direto
        if item.get("original_price"):
            preco_orig = float(item["original_price"])

        # Fonte 2: sale_price
        if not preco_orig and item.get("sale_price"):
            sp = item["sale_price"]
            if isinstance(sp, dict) and sp.get("price_id"):
                preco_orig = preco  # será tratado abaixo

        # Fonte 3: discount_percentage no atributo
        desconto_direto = 0
        attrs = item.get("attributes", [])
        for attr in attrs:
            if attr.get("id") == "DISCOUNT_PERCENTAGE":
                try:
                    desconto_direto = int(float(attr.get("value_name", "0").replace("%", "")))
                except Exception:
                    pass

        # Fonte 4: calcular pela diferença de preço com desconto
        if not preco_orig and desconto_direto >= DESCONTO_MINIMO_PERCENT:
            preco_orig = round(preco / (1 - desconto_direto / 100), 2)

        # Fonte 5: campo prices
        if not preco_orig:
            prices = item.get("prices", {})
            if isinstance(prices, dict):
                for p_item in prices.get("prices", []):
                    conditions = p_item.get("conditions", {})
                    if conditions.get("context") == "DISCOUNT":
                        reg = p_item.get("regular_amount")
                        if reg:
                            preco_orig = float(reg)
                            break

        # Se ainda não tem preço original, ignora
        if not preco_orig or preco_orig <= preco:
            return None

        desconto = round(((preco_orig - preco) / preco_orig) * 100)
        if desconto < DESCONTO_MINIMO_PERCENT:
            return None

        return {
            "id":             pid,
            "titulo":         titulo,
            "preco":          preco,
            "preco_original": preco_orig,
            "desconto":       desconto,
            "economia":       round(preco_orig - preco, 2),
            "link":           gerar_link_afiliado(permalink),
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
        # tag=best_price filtra só produtos com desconto real
        resp = requests.get(
            f"{BASE}/sites/MLB/search",
            params={
                "q":    termo,
                "sort": "best_seller",
                "limit": 50,
                "tag":  "best_price",
            },
            headers=HEADERS,
            timeout=20,
        )

        if resp.status_code != 200:
            log.debug(f"  [{termo}] HTTP {resp.status_code}")
            return []

        resultados = resp.json().get("results", [])
        log.debug(f"  [{termo}] {len(resultados)} itens retornados")

        for item in resultados:
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
        for p in buscar_por_termo(termo, nome):
            if p["id"] not in ids_vistos:
                ids_vistos.add(p["id"])
                todos.append(p)
        time.sleep(1.5)
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
