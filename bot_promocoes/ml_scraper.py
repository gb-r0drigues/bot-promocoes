# ═══════════════════════════════════════════════════════════
#  ml_scraper.py — v5 com BeautifulSoup (HTML parsing correto)
# ═══════════════════════════════════════════════════════════

import requests
import urllib.parse
import logging
import time
import re
from bs4 import BeautifulSoup
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
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

URLS_CATEGORIAS = {
    "💊 Suplementos":       "https://lista.mercadolivre.com.br/suplementos-alimentares",
    "👗 Moda Feminina":     "https://lista.mercadolivre.com.br/roupa-feminina",
    "👔 Moda Masculina":    "https://lista.mercadolivre.com.br/roupa-masculina",
    "📱 Smartphones":       "https://lista.mercadolivre.com.br/celulares-smartphones",
    "💻 Informática":       "https://lista.mercadolivre.com.br/computadores",
    "🎮 Games":             "https://lista.mercadolivre.com.br/video-games",
    "🏠 Casa e Jardim":     "https://lista.mercadolivre.com.br/casa-moveis-decoracao",
    "⚡ Eletrodomésticos":  "https://lista.mercadolivre.com.br/eletrodomesticos",
    "🎽 Esporte e Fitness": "https://lista.mercadolivre.com.br/esportes-fitness",
    "🧴 Beleza e Saúde":    "https://lista.mercadolivre.com.br/beleza-cuidado-pessoal",
    "🔥 Mais Vendidos":     "https://www.mercadolivre.com.br/ofertas",
    "📦 Ofertas do Dia":    "https://www.mercadolivre.com.br/ofertas",
}

# ─── Link de afiliado ────────────────────────────────────────

def gerar_link_afiliado(url: str) -> str:
    if not url:
        return url
    params = {k: v for k, v in ML_AFILIADO_PARAMS.items() if v}
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urllib.parse.urlencode(params)}"

def detectar_cupom(nome: str) -> str | None:
    nome_lower = nome.lower()
    for chave, cupom in CUPONS_MANUAIS.items():
        if chave in nome_lower:
            return cupom
    return None

# ─── Limpar número do preço ──────────────────────────────────

def limpar_preco(texto: str) -> float:
    """Converte '1.299,90' ou '1299' em float."""
    if not texto:
        return 0.0
    texto = re.sub(r'[^\d,.]', '', texto)
    if ',' in texto and '.' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    elif ',' in texto:
        texto = texto.replace(',', '.')
    try:
        return float(texto)
    except ValueError:
        return 0.0

# ─── Buscar e parsear página ML ──────────────────────────────

def buscar_produtos_categoria(nome: str, url: str) -> list:
    encontrados = []
    try:
        sessao = requests.Session()
        sessao.headers.update(HEADERS)
        resp = sessao.get(url, timeout=30)
        log.info(f"[{nome}] HTTP {resp.status_code} — {len(resp.text)} chars")

        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # ── Seletores para página de lista (lista.mercadolivre.com.br)
        items = soup.select("li.ui-search-layout__item")

        # ── Seletores alternativos para página de ofertas
        if not items:
            items = soup.select("div.andes-card.poly-card")
        if not items:
            items = soup.select("li[class*='result']")
        if not items:
            items = soup.select("div[class*='item']")

        log.info(f"[{nome}] {len(items)} elementos encontrados no HTML")

        ids_vistos = set()

        for item in items:
            try:
                # Título
                titulo_el = (
                    item.select_one(".poly-component__title") or
                    item.select_one(".ui-search-item__title") or
                    item.select_one("h2") or
                    item.select_one("h3") or
                    item.select_one("[class*='title']")
                )
                if not titulo_el:
                    continue
                titulo = titulo_el.get_text(strip=True)

                # Link
                link_el = (
                    item.select_one("a.poly-component__title") or
                    item.select_one("a.ui-search-link") or
                    item.select_one("a[href*='mercadolivre']") or
                    item.select_one("a")
                )
                permalink = link_el["href"] if link_el and link_el.get("href") else ""
                if not permalink or "mercadolivre" not in permalink:
                    continue

                # ID único do produto
                pid = re.search(r'MLB[\d]+', permalink)
                pid = pid.group(0) if pid else permalink[-20:]
                if pid in ids_vistos:
                    continue
                ids_vistos.add(pid)

                # Preço atual
                preco_el = (
                    item.select_one(".andes-money-amount.poly-price__current .andes-money-amount__fraction") or
                    item.select_one(".ui-search-price__second-line .andes-money-amount__fraction") or
                    item.select_one(".price-tag-fraction") or
                    item.select_one("[class*='price-fraction']") or
                    item.select_one("[class*='amount__fraction']")
                )
                if not preco_el:
                    continue
                preco = limpar_preco(preco_el.get_text(strip=True))
                if preco <= 0:
                    continue

                # Preço original (riscado)
                preco_orig_el = (
                    item.select_one("s .andes-money-amount__fraction") or
                    item.select_one(".ui-search-price__original-value .andes-money-amount__fraction") or
                    item.select_one("[class*='original'] .andes-money-amount__fraction") or
                    item.select_one("[class*='before'] .andes-money-amount__fraction")
                )
                preco_orig = limpar_preco(preco_orig_el.get_text(strip=True)) if preco_orig_el else 0.0

                # Se não tem preço original, tenta pegar desconto direto
                if not preco_orig or preco_orig <= preco:
                    desconto_el = item.select_one("[class*='discount']") or item.select_one("[class*='pill']")
                    if desconto_el:
                        txt = desconto_el.get_text(strip=True)
                        m = re.search(r'(\d+)', txt)
                        if m:
                            pct = int(m.group(1))
                            if pct >= DESCONTO_MINIMO_PERCENT:
                                preco_orig = round(preco / (1 - pct/100), 2)
                    if not preco_orig or preco_orig <= preco:
                        continue

                desconto = round(((preco_orig - preco) / preco_orig) * 100)
                if desconto < DESCONTO_MINIMO_PERCENT:
                    continue
                if preco < PRECO_MINIMO or preco > PRECO_MAXIMO:
                    continue

                # Imagem
                img_el = item.select_one("img")
                imagem = img_el.get("src") or img_el.get("data-src", "") if img_el else ""

                encontrados.append({
                    "id":             pid,
                    "titulo":         titulo,
                    "preco":          preco,
                    "preco_original": preco_orig,
                    "desconto":       desconto,
                    "economia":       round(preco_orig - preco, 2),
                    "link":           gerar_link_afiliado(permalink.split("?")[0]),
                    "imagem":         imagem,
                    "rating":         0,
                    "total_reviews":  0,
                    "categoria":      nome,
                    "cupom":          detectar_cupom(nome),
                })

                if len(encontrados) >= MAX_PRODUTOS_POR_CATEGORIA:
                    break

            except Exception as e:
                log.debug(f"Erro no item: {e}")
                continue

        time.sleep(2)

    except Exception as e:
        log.error(f"[{nome}] Erro geral: {e}")

    log.info(f"[{nome}] {len(encontrados)} aprovados")
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
