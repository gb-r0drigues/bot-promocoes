# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v4 via scraping da página de ofertas ML
#  Não depende de API nem de token — funciona em qualquer IP
# ═══════════════════════════════════════════════════════════

import requests
import urllib.parse
import logging
import time
import json
import re
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
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

# ─── URLs de busca por categoria (página pública ML) ────────
URLS_CATEGORIAS = {
    "💊 Suplementos":       "https://lista.mercadolivre.com.br/suplementos-alimentares#deal_print_id=&pricing_filter=yes",
    "👗 Moda Feminina":     "https://lista.mercadolivre.com.br/roupa-feminina#deal_print_id=&pricing_filter=yes",
    "👔 Moda Masculina":    "https://lista.mercadolivre.com.br/roupa-masculina#deal_print_id=&pricing_filter=yes",
    "📱 Smartphones":       "https://lista.mercadolivre.com.br/celulares-smartphones#deal_print_id=&pricing_filter=yes",
    "💻 Informática":       "https://lista.mercadolivre.com.br/computadores#deal_print_id=&pricing_filter=yes",
    "🎮 Games":             "https://lista.mercadolivre.com.br/video-games#deal_print_id=&pricing_filter=yes",
    "🏠 Casa e Jardim":     "https://lista.mercadolivre.com.br/casa-moveis-decoracao#deal_print_id=&pricing_filter=yes",
    "⚡ Eletrodomésticos":  "https://lista.mercadolivre.com.br/eletrodomesticos#deal_print_id=&pricing_filter=yes",
    "🎽 Esporte e Fitness": "https://lista.mercadolivre.com.br/esportes-fitness#deal_print_id=&pricing_filter=yes",
    "🧴 Beleza e Saúde":    "https://lista.mercadolivre.com.br/beleza-cuidado-pessoal#deal_print_id=&pricing_filter=yes",
    "🔥 Mais Vendidos":     "https://www.mercadolivre.com.br/ofertas",
    "📦 Ofertas do Dia":    "https://www.mercadolivre.com.br/ofertas#nav-by-cat",
}

def gerar_link_afiliado(url_produto: str) -> str:
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    separador = "&" if "?" in url_produto else "?"
    return f"{url_produto}{separador}{urllib.parse.urlencode(params)}"

def detectar_cupom_por_categoria(nome: str) -> str | None:
    nome_lower = nome.lower()
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in nome_lower:
            return cupom
    return None

# ─── Buscar via JSON embutido na página ─────────────────────

def buscar_produtos_categoria(nome: str, url: str) -> list:
    encontrados = []
    sessao = requests.Session()
    sessao.headers.update(HEADERS)

    try:
        resp = sessao.get(url, timeout=25)
        log.info(f"[{nome}] HTTP {resp.status_code}")

        if resp.status_code != 200:
            log.error(f"[{nome}] Falha ao acessar página")
            return []

        html = resp.text

        # Tenta extrair JSON de dados de produto do HTML
        padrao = re.compile(
            r'"price"\s*:\s*([\d.]+).*?"original_price"\s*:\s*([\d.]+).*?"title"\s*:\s*"([^"]+)".*?"permalink"\s*:\s*"([^"]+)".*?"thumbnail"\s*:\s*"([^"]+)"',
            re.DOTALL
        )
        matches = padrao.findall(html)

        if not matches:
            # Tenta padrão alternativo
            padrao2 = re.compile(r'__PRELOADED_STATE__\s*=\s*({.*?});</script>', re.DOTALL)
            m = padrao2.search(html)
            if m:
                try:
                    dados = json.loads(m.group(1))
                    items = _extrair_de_preloaded(dados, nome)
                    encontrados.extend(items)
                except Exception:
                    pass

        for match in matches:
            try:
                preco         = float(match[0])
                preco_orig    = float(match[1])
                titulo        = match[2]
                permalink     = match[3]
                thumbnail     = match[4]

                if preco_orig <= preco:
                    continue
                desconto = round(((preco_orig - preco) / preco_orig) * 100)
                if desconto < DESCONTO_MINIMO_PERCENT:
                    continue
                if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                    continue

                pid = permalink.split("/p/")[-1].split("?")[0] if "/p/" in permalink else permalink.split("-")[-1].split(".")[0]

                encontrados.append({
                    "id":             pid,
                    "titulo":         titulo,
                    "preco":          preco,
                    "preco_original": preco_orig,
                    "desconto":       desconto,
                    "economia":       preco_orig - preco,
                    "link":           gerar_link_afiliado(permalink),
                    "imagem":         thumbnail,
                    "rating":         0,
                    "total_reviews":  0,
                    "categoria":      nome,
                    "cupom":          detectar_cupom_por_categoria(nome),
                })

                if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                    break

            except Exception:
                continue

        # Se nada foi encontrado via regex, usa API pública sem autenticação
        if not encontrados:
            encontrados = _buscar_api_publica(nome)

        time.sleep(2)

    except Exception as e:
        log.error(f"[{nome}] Erro: {e}")
        encontrados = _buscar_api_publica(nome)

    log.info(f"[{nome}] {len(encontrados)} aprovados")
    return encontrados

def _extrair_de_preloaded(dados: dict, nome: str) -> list:
    encontrados = []
    try:
        items = dados.get("initialState", {}).get("results", [])
        for item in items:
            preco      = float(item.get("price", 0))
            preco_orig = float(item.get("original_price") or 0)
            if not preco_orig or preco_orig <= preco:
                continue
            desconto = round(((preco_orig - preco) / preco_orig) * 100)
            if desconto < DESCONTO_MINIMO_PERCENT:
                continue
            if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                continue
            encontrados.append({
                "id":             item.get("id", ""),
                "titulo":         item.get("title", ""),
                "preco":          preco,
                "preco_original": preco_orig,
                "desconto":       desconto,
                "economia":       preco_orig - preco,
                "link":           gerar_link_afiliado(item.get("permalink", "")),
                "imagem":         item.get("thumbnail", ""),
                "rating":         0,
                "total_reviews":  0,
                "categoria":      nome,
                "cupom":          detectar_cupom_por_categoria(nome),
            })
    except Exception:
        pass
    return encontrados

# ─── Fallback: API pública sem token ────────────────────────

def _buscar_api_publica(nome: str) -> list:
    """Tenta a API pública com query de texto — último recurso."""
    encontrados = []
    try:
        termos = {
            "💊 Suplementos": "suplemento proteina",
            "👗 Moda Feminina": "vestido feminino",
            "👔 Moda Masculina": "camisa masculina",
            "📱 Smartphones": "smartphone samsung",
            "💻 Informática": "notebook",
            "🎮 Games": "jogo ps5",
            "🏠 Casa e Jardim": "organizador casa",
            "⚡ Eletrodomésticos": "air fryer",
            "🎽 Esporte e Fitness": "tenis corrida",
            "🧴 Beleza e Saúde": "perfume importado",
            "🔥 Mais Vendidos": "mais vendidos",
            "📦 Ofertas do Dia": "oferta do dia",
        }
        termo = termos.get(nome, nome.replace("📦","").replace("🔥","").strip())
        url = f"https://api.mercadolibre.com/sites/MLB/search"
        params = {"q": termo, "sort": "best_seller", "limit": 50}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code == 200:
            for item in resp.json().get("results", []):
                preco      = float(item.get("price", 0))
                preco_orig = float(item.get("original_price") or 0)
                if not preco_orig or preco_orig <= preco:
                    continue
                desconto = round(((preco_orig - preco) / preco_orig) * 100)
                if desconto < DESCONTO_MINIMO_PERCENT:
                    continue
                if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                    continue
                encontrados.append({
                    "id":             item.get("id", ""),
                    "titulo":         item.get("title", ""),
                    "preco":          preco,
                    "preco_original": preco_orig,
                    "desconto":       desconto,
                    "economia":       preco_orig - preco,
                    "link":           gerar_link_afiliado(item.get("permalink", "")),
                    "imagem":         item.get("thumbnail", "").replace("I.jpg","O.jpg"),
                    "rating":         item.get("reviews", {}).get("rating_average", 0),
                    "total_reviews":  item.get("reviews", {}).get("total", 0),
                    "categoria":      nome,
                    "cupom":          detectar_cupom_por_categoria(nome),
                })
                if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                    break
    except Exception as e:
        log.error(f"[{nome}] API pública também falhou: {e}")
    return encontrados

# ─── Todas as categorias ─────────────────────────────────────

def buscar_todas_categorias() -> list:
    todos = []
    log.info(f"Buscando em {len(URLS_CATEGORIAS)} categorias...")
    for nome, url in URLS_CATEGORIAS.items():
        todos.extend(buscar_produtos_categoria(nome, url))
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
