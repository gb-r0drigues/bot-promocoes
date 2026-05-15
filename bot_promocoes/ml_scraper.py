# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v3 com autenticação OAuth ML
# ═══════════════════════════════════════════════════════════

import requests
import urllib.parse
import logging
import time
import os
from config import (
    CATEGORIAS, DESCONTO_MINIMO_PERCENT, PRECO_MINIMO,
    PRECO_MAXIMO, MAX_PRODUTOS_POR_CATEGORIA, ML_AFILIADO_PARAMS
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
log = logging.getLogger(__name__)

BASE_URL = "https://api.mercadolibre.com"

# ─── Credenciais ML (via variáveis de ambiente ou config) ───
ML_APP_ID       = os.environ.get("ML_APP_ID", "")
ML_CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET", "")

HEADERS_BASE = {
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

_access_token = None
_token_expiry = 0

# ─── OAuth — pegar token de acesso ──────────────────────────

def obter_access_token() -> str | None:
    global _access_token, _token_expiry

    if _access_token and time.time() < _token_expiry:
        return _access_token

    if not ML_APP_ID or not ML_CLIENT_SECRET:
        log.warning("ML_APP_ID ou ML_CLIENT_SECRET não configurados. Tentando sem auth...")
        return None

    try:
        resp = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type":    "client_credentials",
                "client_id":     ML_APP_ID,
                "client_secret": ML_CLIENT_SECRET,
            },
            timeout=15,
        )

        if resp.status_code == 200:
            dados = resp.json()
            _access_token = dados.get("access_token")
            _token_expiry = time.time() + dados.get("expires_in", 21600) - 300
            log.info("✅ Token ML obtido com sucesso")
            return _access_token
        else:
            log.error(f"Erro ao obter token ML: {resp.status_code} — {resp.text[:200]}")
            return None

    except Exception as e:
        log.error(f"Falha ao autenticar no ML: {e}")
        return None

# ─── Sessão autenticada ──────────────────────────────────────

def criar_sessao() -> requests.Session:
    sessao = requests.Session()
    sessao.headers.update(HEADERS_BASE)

    token = obter_access_token()
    if token:
        sessao.headers["Authorization"] = f"Bearer {token}"

    return sessao

# ─── Link de afiliado ────────────────────────────────────────

def gerar_link_afiliado(url_produto: str) -> str:
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    separador = "&" if "?" in url_produto else "?"
    return f"{url_produto}{separador}{urllib.parse.urlencode(params)}"

# ─── Cupom ───────────────────────────────────────────────────

def buscar_cupom_produto(produto_id: str, sessao: requests.Session) -> str | None:
    try:
        resp = sessao.get(f"{BASE_URL}/items/{produto_id}/coupons", timeout=10)
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

def detectar_cupom_por_categoria(nome: str) -> str | None:
    nome_lower = nome.lower()
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in nome_lower:
            return cupom
    return None

# ─── Buscar por categoria ────────────────────────────────────

def buscar_produtos_categoria(nome: str, id_cat: str, sessao: requests.Session) -> list:
    encontrados = []
    try:
        resp = sessao.get(
            f"{BASE_URL}/sites/MLB/search",
            params={"category": id_cat, "sort": "best_seller", "limit": 50},
            timeout=20,
        )

        # Se 403, tenta busca por termo
        if resp.status_code == 403:
            log.warning(f"[{nome}] 403 na categoria, tentando por termo...")
            termo = nome.encode("ascii", "ignore").decode().strip()
            resp = sessao.get(
                f"{BASE_URL}/sites/MLB/search",
                params={"q": termo, "sort": "best_seller", "limit": 50},
                timeout=20,
            )

        if resp.status_code != 200:
            log.error(f"[{nome}] HTTP {resp.status_code}")
            return []

        resultados = resp.json().get("results", [])
        log.info(f"[{nome}] {len(resultados)} produtos na API")

        for item in resultados:
            p = _extrair_produto(item, nome, sessao)
            if p:
                encontrados.append(p)
            if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                break

        time.sleep(1)

    except Exception as e:
        log.error(f"[{nome}] Erro: {e}")

    log.info(f"[{nome}] {len(encontrados)} aprovados")
    return encontrados

# ─── Extrair produto ─────────────────────────────────────────

def _extrair_produto(item: dict, categoria: str, sessao: requests.Session) -> dict | None:
    try:
        pid           = item.get("id", "")
        titulo        = item.get("title", "")
        preco         = float(item.get("price", 0))
        preco_orig    = float(item.get("original_price") or 0)
        permalink     = item.get("permalink", "")
        thumbnail     = item.get("thumbnail", "").replace("I.jpg", "O.jpg")
        avs           = item.get("reviews", {})
        rating        = avs.get("rating_average", 0)
        total_reviews = avs.get("total", 0)

        if not preco_orig or preco_orig <= preco:
            return None
        desconto = round(((preco_orig - preco) / preco_orig) * 100)
        if desconto < DESCONTO_MINIMO_PERCENT:
            return None
        if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
            return None
        if not thumbnail:
            return None

        cupom = buscar_cupom_produto(pid, sessao) or detectar_cupom_por_categoria(categoria)

        return {
            "id": pid, "titulo": titulo, "preco": preco,
            "preco_original": preco_orig, "desconto": desconto,
            "economia": preco_orig - preco, "link": gerar_link_afiliado(permalink),
            "imagem": thumbnail, "rating": rating,
            "total_reviews": total_reviews, "categoria": categoria, "cupom": cupom,
        }
    except Exception as e:
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
