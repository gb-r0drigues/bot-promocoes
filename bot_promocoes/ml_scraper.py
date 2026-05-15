# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — Busca automática de ofertas + CUPONS
#  v2 — corrigido erro 403 Forbidden da API do ML
# ═══════════════════════════════════════════════════════════

import requests
import urllib.parse
import logging
import time
from config import (
    CATEGORIAS, DESCONTO_MINIMO_PERCENT, PRECO_MINIMO,
    PRECO_MAXIMO, MAX_PRODUTOS_POR_CATEGORIA, ML_AFILIADO_PARAMS, ML_AFILIADO_ID
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
log = logging.getLogger(__name__)

BASE_URL = "https://api.mercadolibre.com"

# ─── Headers que evitam o bloqueio 403 ──────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.mercadolivre.com.br/",
    "Origin": "https://www.mercadolivre.com.br",
}

# ─── Cupons manuais por categoria ───────────────────────────
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

# ─── Link de afiliado ────────────────────────────────────────

def gerar_link_afiliado(url_produto: str) -> str:
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    separador = "&" if "?" in url_produto else "?"
    query = urllib.parse.urlencode(params)
    return f"{url_produto}{separador}{query}"

# ─── Sessão reutilizável ─────────────────────────────────────

def criar_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update(HEADERS)
    return sessao

# ─── Buscar cupom via API ────────────────────────────────────

def buscar_cupom_produto(produto_id: str, sessao: requests.Session) -> str | None:
    try:
        url = f"{BASE_URL}/items/{produto_id}/coupons"
        resp = sessao.get(url, timeout=10)
        if resp.status_code == 200:
            dados = resp.json()
            cupons = dados if isinstance(dados, list) else dados.get("coupons", [])
            for c in cupons:
                codigo = c.get("code") or c.get("id", "")
                if codigo:
                    return codigo.upper()
    except Exception:
        pass
    return None

def detectar_cupom_por_categoria(nome_categoria: str) -> str | None:
    nome_lower = nome_categoria.lower()
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in nome_lower:
            return cupom
    return None

# ─── Buscar por categoria ────────────────────────────────────

def buscar_produtos_categoria(nome_categoria: str, id_categoria: str, sessao: requests.Session) -> list:
    produtos_encontrados = []
    try:
        url = f"{BASE_URL}/sites/MLB/search"
        params = {
            "category": id_categoria,
            "sort":     "best_seller",
            "limit":    50,
        }

        resp = sessao.get(url, params=params, timeout=20)

        if resp.status_code == 403:
            log.warning(f"[{nome_categoria}] 403 na busca por categoria, tentando busca por termo...")
            # Fallback: busca por palavra-chave da categoria
            nome_simples = nome_categoria.replace("💊","").replace("👗","").replace("👔","") \
                .replace("📱","").replace("💻","").replace("🎮","").replace("🏠","") \
                .replace("⚡","").replace("🔥","").replace("🎽","").replace("🧴","") \
                .replace("📦","").strip()
            params2 = {"q": nome_simples, "sort": "best_seller", "limit": 50}
            resp = sessao.get(url, params=params2, timeout=20)

        if resp.status_code != 200:
            log.error(f"[{nome_categoria}] Erro HTTP {resp.status_code}")
            return []

        resultados = resp.json().get("results", [])
        log.info(f"[{nome_categoria}] {len(resultados)} produtos na API")

        for item in resultados:
            produto = _extrair_produto(item, nome_categoria, sessao)
            if produto:
                produtos_encontrados.append(produto)
            if len(produtos_encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                break

        # Pequena pausa entre categorias para não sobrecarregar a API
        time.sleep(1)

    except requests.exceptions.RequestException as e:
        log.error(f"[{nome_categoria}] Erro de conexão: {e}")
    except Exception as e:
        log.error(f"[{nome_categoria}] Erro inesperado: {e}")

    log.info(f"[{nome_categoria}] {len(produtos_encontrados)} aprovados")
    return produtos_encontrados

# ─── Extrair produto ─────────────────────────────────────────

def _extrair_produto(item: dict, categoria: str, sessao: requests.Session) -> dict | None:
    try:
        produto_id     = item.get("id", "")
        titulo         = item.get("title", "")
        preco          = float(item.get("price", 0))
        preco_original = float(item.get("original_price") or 0)
        permalink      = item.get("permalink", "")
        thumbnail      = item.get("thumbnail", "").replace("I.jpg", "O.jpg")
        avaliacoes     = item.get("reviews", {})
        rating         = avaliacoes.get("rating_average", 0)
        total_reviews  = avaliacoes.get("total", 0)

        if not preco_original or preco_original <= preco:
            return None
        desconto = round(((preco_original - preco) / preco_original) * 100)
        if desconto < DESCONTO_MINIMO_PERCENT:
            return None
        if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
            return None
        if not thumbnail:
            return None

        cupom = buscar_cupom_produto(produto_id, sessao)
        if not cupom:
            cupom = detectar_cupom_por_categoria(categoria)

        return {
            "id":             produto_id,
            "titulo":         titulo,
            "preco":          preco,
            "preco_original": preco_original,
            "desconto":       desconto,
            "economia":       preco_original - preco,
            "link":           gerar_link_afiliado(permalink),
            "imagem":         thumbnail,
            "rating":         rating,
            "total_reviews":  total_reviews,
            "categoria":      categoria,
            "cupom":          cupom,
        }
    except (ValueError, TypeError, KeyError) as e:
        log.warning(f"Erro produto {item.get('id','?')}: {e}")
        return None

# ─── Todas as categorias ─────────────────────────────────────

def buscar_todas_categorias() -> list:
    todos = []
    ativas = {n: d for n, d in CATEGORIAS.items() if d.get("ativo")}
    log.info(f"Buscando em {len(ativas)} categorias...")

    sessao = criar_sessao()

    for nome, dados in ativas.items():
        todos.extend(buscar_produtos_categoria(nome, dados["id"], sessao))

    log.info(f"Total para enviar: {len(todos)} produtos")
    return todos

# ─── Formatar mensagem ────────────────────────────────────────

def formatar_mensagem(produto: dict, plataforma: str = "telegram") -> str:
    titulo         = produto["titulo"]
    preco          = produto["preco"]
    preco_original = produto["preco_original"]
    desconto       = produto["desconto"]
    economia       = produto["economia"]
    link           = produto["link"]
    cupom          = produto.get("cupom")
    categoria      = produto["categoria"]
    rating         = produto.get("rating", 0)
    total_reviews  = produto.get("total_reviews", 0)

    linha_cupom  = f"Cupom: `{cupom}` ⚠️\n" if cupom else ""
    linha_rating = ""
    if rating and total_reviews > 0:
        estrelas = "⭐" * min(round(rating), 5)
        linha_rating = f"{estrelas} ({total_reviews} avaliações)\n"

    if plataforma == "telegram":
        msg = (
            f"*{categoria}*\n"
            f"━━━━━━━━━━━━━━━━━\n\n"
            f"*{titulo}*\n\n"
            f"De R${preco_original:.2f} | Por *R${preco:.2f}* 👑\n"
            f"🏷️ *{desconto}% OFF* — Economia: R${economia:.2f}\n"
            f"{linha_cupom}"
            f"{linha_rating}"
            f"\n🛒 Achado no Mercado Livre\n"
            f"👉 {link}\n"
            f"\n_Preços e disponibilidade sujeitos a alteração._"
        )
    else:
        msg = (
            f"*{categoria}*\n\n"
            f"{titulo}\n\n"
            f"De R${preco_original:.2f} | Por *R${preco:.2f}* 👑\n"
            f"🏷️ *{desconto}% OFF* — Economia: R${economia:.2f}\n"
            f"{linha_cupom}"
            f"{linha_rating}"
            f"\n🛒 Achado no Mercado Livre\n"
            f"👉 {link}\n"
            f"\n_Preços sujeitos a alteração._"
        )
    return msg
