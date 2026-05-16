# ═══════════════════════════════════════════════════════════
#  config.py — Lê variáveis do ambiente (GitHub Actions Secrets)
# ═══════════════════════════════════════════════════════════
import os

# ─── TELEGRAM ───────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CANAL = os.environ.get("TELEGRAM_CANAL", "")

# ─── AFILIADO ML ────────────────────────────────────────────
ML_AFILIADO_ID = os.environ.get("ML_AFILIADO_ID", "")
ML_APP_ID      = os.environ.get("ML_APP_ID", "")
ML_CLIENT_SECRET = os.environ.get("ML_CLIENT_SECRET", "")

ML_AFILIADO_PARAMS = {
    "matt_tool":     ML_AFILIADO_ID,
    "matt_source":   "telegram",
    "matt_campaign": "bot_promocoes",
    "matt_medium":   "afiliados",
}

# ─── FILTROS ────────────────────────────────────────────────
DESCONTO_MINIMO_PERCENT   = 15
PRECO_MINIMO              = 30.0
PRECO_MAXIMO              = 3000.0
MAX_PRODUTOS_POR_CATEGORIA = 3

# ─── HORÁRIO (não usado no GitHub Actions, mas mantido) ─────
INTERVALO_MINUTOS = 120
HORARIO_INICIO    = 7
HORARIO_FIM       = 23
