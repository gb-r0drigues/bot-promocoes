# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v10 endpoints highlights/deals do ML
#  Usa endpoints públicos diferentes que não são bloqueados
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
    "Cache-Control": "no-cache",
}

CUPONS_MANUAIS = {
    "moda":        "CUPOMPRAMODA",
    "roupa":       "CUPOMPRAMODA",
    "suplemento":  "SUPERMELI",
    "saude":       "SAUDEML",
    "beleza":      "BELEZAML",
    "celular":     "FRETEGRATIS",
    "smartphone":  "FRETEGRATIS",
    "notebook":    "TECHML",
    "informatica": "TECHML",
    "game":        "GAMEML",
    "casa":        "CASAML",
}

# Endpoints públicos do ML que funcionam sem auth e sem bloqueio por categoria
ENDPOINTS = [
    # Destaques gerais MLB
    {"nome": "🔥 Destaques ML",      "url": f"{BASE}/highlights/MLB"},
    # Destaques por categoria
    {"nome": "📱 Smartphones",       "url": f"{BASE}/highlights/MLB/category/MLB1051"},
    {"nome": "💻 Informática",       "url": f"{BASE}/highlights/MLB/category/MLB1648"},
    {"nome": "🎮 Games",             "url": f"{BASE}/highlights/MLB/category/MLB1144"},
    {"nome": "⚡ Eletrodomésticos",  "url": f"{BASE}/highlights/MLB/category/MLB5726"},
    {"nome": "🏠 Casa e Jardim",     "url": f"{BASE}/highlights/MLB/category/MLB1574"},
    {"nome": "👗 Moda",              "url": f"{BASE}/highlights/MLB/category/MLB1430"},
    {"nome": "🧴 Beleza e Saúde",    "url": f"{BASE}/highlights/MLB/category/MLB1246"},
    {"nome": "🎽 Esporte",           "url": f"{BASE}/highlights/MLB/category/MLB1276"},
    {"nome": "💊 Suplementos",       "url": f"{BASE}/highlights/MLB/category/MLB3936"},
]

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

def buscar_detalhes_item(item_id: str) -> dict:
    """Busca preço original de um item específico."""
    try:
        resp = requests.get(
            f"{BASE}/items/{item_id}",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}

def buscar_endpoint(nome: str, url: str) -> list:
    encontrados = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        log.info(f"[{nome}] HTTP {resp.status_code}")

        if resp.status_code != 200:
            log.warning(f"[{nome}] Endpoint indisponível")
            return []

        dados = resp.json()

        # highlights retorna {"content": [...]} com IDs ou objetos
        content = dados if isinstance(dados, list) else dados.get("content", [])

        log.info(f"[{nome}] {len(content)} itens retornados")

        ids_vistos = set()

        for entry in content:
            try:
                # Pode ser só o ID ou um objeto completo
                if isinstance(entry, str):
                    item_id = entry
                    item = buscar_detalhes_item(item_id)
                elif isinstance(entry, dict):
                    item_id = entry.get("id", "")
                    item = entry
                else:
                    continue

                if not item_id or item_id in ids_vistos:
                    continue
                ids_vistos.add(item_id)

                # Se não tem preço no objeto, busca detalhes
                if not item.get("price"):
                    item = buscar_detalhes_item(item_id)
                if not item:
                    continue

                preco      = float(item.get("price", 0))
                preco_orig = float(item.get("original_price") or 0)
                titulo     = item.get("title", "")
                permalink  = item.get("permalink", "")
                thumb      = item.get("thumbnail", "").replace("I.jpg", "O.jpg").replace("http://", "https://")
                avs        = item.get("reviews", {}) or {}

                if preco <= 0 or not permalink:
                    continue
                if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                    continue
                if not preco_orig or preco_orig <= preco:
                    continue

                desconto = round(((preco_orig - preco) / preco_orig) * 100)
                if desconto < DESCONTO_MINIMO_PERCENT:
                    continue

                encontrados.append({
                    "id":             item_id,
                    "titulo":         titulo,
                    "preco":          preco,
                    "preco_original": preco_orig,
                    "desconto":       desconto,
                    "economia":       round(preco_orig - preco, 2),
                    "link":           gerar_link_afiliado(permalink),
                    "imagem":         thumb,
                    "rating":         avs.get("rating_average", 0),
                    "total_reviews":  avs.get("total", 0),
                    "categoria":      nome,
                    "cupom":          detectar_cupom(nome),
                })

                if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                    break

                time.sleep(0.3)

            except Exception as e:
                log.debug(f"Erro no item: {e}")
                continue

    except Exception as e:
        log.error(f"[{nome}] Erro geral: {e}")

    log.info(f"[{nome}] {len(encontrados)} aprovados")
    return encontrados

def buscar_todas_categorias() -> list:
    todos = []
    ids_globais = set()
    log.info(f"Buscando em {len(ENDPOINTS)} endpoints...")

    for ep in ENDPOINTS:
        produtos = buscar_endpoint(ep["nome"], ep["url"])
        for p in produtos:
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
