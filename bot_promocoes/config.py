# ═══════════════════════════════════════════════════════════
#  config.py — CONFIGURAÇÕES DO BOT DE PROMOÇÕES
#  Edite APENAS este arquivo para personalizar o robô
# ═══════════════════════════════════════════════════════════

# ─── TELEGRAM ──────────────────────────────────────────────
# Crie seu bot em https://t.me/BotFather e cole o token abaixo
TELEGRAM_TOKEN = "8988470690:AAGV_gLA0dnJp5zynFahLMPdntTqcvF1soY"

# ID do canal ou grupo. Exemplos:
#   Canal público:  "@meu_canal_promocoes"
#   Grupo privado:  "-1001234567890"
TELEGRAM_CANAL = "@🔥 Promoções — Radar de Ofertas"

# ─── WHATSAPP (Evolution API) ───────────────────────────────
# URL onde sua Evolution API está rodando
EVOLUTION_URL = "http://localhost:8080"
EVOLUTION_APIKEY = "SUA_APIKEY_EVOLUTION"

# Nome da instância criada na Evolution API
WA_INSTANCIA = "minha-instancia"

# ID do grupo WhatsApp (formato: numerosdonumero@g.us)
# Para descobrir: envie uma mensagem no grupo e veja nos logs da Evolution
WA_GRUPO_ID = "5511999999999-1234567890@g.us"

# ─── AFILIADO MERCADO LIVRE ─────────────────────────────────
# Encontre seu ID no painel: https://afiliados.mercadolivre.com.br
# Exemplo de ID: "gabriel_afiliado" ou "GA-12345"
ML_AFILIADO_ID = "141KNF"

# Parâmetros de rastreamento (deixe como está ou customize)
ML_AFILIADO_PARAMS = {
    "matt_tool":     ML_AFILIADO_ID,
    "matt_word":     "",
    "matt_source":   "telegram_whatsapp",
    "matt_campaign": "bot_promocoes",
    "matt_medium":   "afiliados",
}

# ─── CATEGORIAS PARA MONITORAR ──────────────────────────────
# True = ativo | False = pausado (sem precisar deletar)
CATEGORIAS = {
    "💊 Suplementos":        {"id": "MLB3936",  "ativo": True},
    "👗 Moda Feminina":      {"id": "MLB1939",  "ativo": True},
    "👔 Moda Masculina":     {"id": "MLB1938",  "ativo": True},
    "📱 Smartphones":        {"id": "MLB1051",  "ativo": True},
    "💻 Informática":        {"id": "MLB1648",  "ativo": True},
    "🎮 Games":              {"id": "MLB1144",  "ativo": True},
    "🏠 Casa e Jardim":      {"id": "MLB1574",  "ativo": True},
    "⚡ Eletrodomésticos":   {"id": "MLB5726",  "ativo": True},
    "🔥 Mais Vendidos":      {"id": "MLB1000",  "ativo": True},
    "🎽 Esporte e Fitness":  {"id": "MLB1276",  "ativo": True},
    "🧴 Beleza e Saúde":     {"id": "MLB1246",  "ativo": True},
    "📦 Ofertas do Dia":     {"id": "MLB5673",  "ativo": True},
}

# ─── FILTROS DE PRODUTO ─────────────────────────────────────
DESCONTO_MINIMO_PERCENT = 15   # % — produtos com menos desconto são ignorados
PRECO_MINIMO = 30.0            # R$ — ignora produtos muito baratos
PRECO_MAXIMO = 3000.0          # R$ — limite superior
MAX_PRODUTOS_POR_CATEGORIA = 3 # quantos produtos postar por categoria por ciclo

# ─── AGENDAMENTO ────────────────────────────────────────────
INTERVALO_MINUTOS = 120        # buscar novas promoções a cada 2 horas
HORARIO_INICIO = 0             # hora do dia para começar (7h)
HORARIO_FIM = 23               # hora do dia para parar (23h)

# ─── APARÊNCIA DAS MENSAGENS ─────────────────────────────────
EMOJI_FOGO = "🔥"
EMOJI_TAG  = "🏷️"
EMOJI_LINK = "🛒"
RODAPE_MENSAGEM = "\n\n💬 _Entre no grupo para mais promoções!_"
