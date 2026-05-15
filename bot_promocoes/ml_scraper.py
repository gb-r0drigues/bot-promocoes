# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v8 com diagnóstico detalhado
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
    "💊 Suplementos":       ["whey protein", "creatina"],
    "👗 Moda Feminina":     ["vestido feminino", "blusa feminina"],
    "👔 Moda Masculina":    ["camiseta masculina", "camisa masculina"],
    "📱 Smartphones":       ["smartphone samsung", "celular xiaomi"],
    "💻 Informática":       ["notebook", "ssd"],
    "🎮 Games":             ["headset gamer", "controle ps5"],
    "🏠 Casa e Jardim":     ["jogo de panelas", "jogo de cama"],
    "⚡ Eletrodomésticos":  ["air fryer", "aspirador"],
    "🎽 Esporte e Fitness": ["tenis esportivo", "halteres"],
    "🧴 Beleza e Saúde":    ["perfume importado", "protetor solar"],
    "🔥 Mais Vendidos":     ["fone bluetooth", "smartwatch"],
    "📦 Ofertas do Dia":    ["caixa de som", "carregador rapido"],
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
        preco_orig = float(item.get("original_price") or 0)
        permalink = item.get("permalink", "")
        thumb     = item.get("thumbnail", "").replace("I.jpg", "O.jpg").replace("http://", "https://")
        avs       = item.get("reviews", {}) or {}

        if preco <= 0 or not permalink:
            return None
        if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
            return None
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
        log.debug(f"Erro extraindo: {e}")
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

        if resp.status_code != 200:
            log.warning(f"  [{termo}] HTTP {resp.status_code}")
            return []

        resultados = resp.json().get("results", [])

        # ── Diagnóstico: inspecionar primeiros 3 itens ──────
        com_preco_orig = sum(1 for r in resultados if r.get("original_price"))
        log.info(f"  [{termo}] {len(resultados)} itens | {com_preco_orig} com original_price")

        if resultados and com_preco_orig == 0:
            # Mostra campos do primeiro item para diagnóstico
            primeiro = resultados[0]
            campos = {k: v for k, v in primeiro.items()
                      if k in ("price","original_price","sale_price","discount","prices","tags")}
            log.info(f"  Campos do 1º item: {campos}")

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
