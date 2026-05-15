# 🤖 GUIA COMPLETO — Robô de Promoções ML

## O que você vai construir

Um robô que monitora o Mercado Livre automaticamente, detecta produtos com desconto e cupons, e envia para o seu canal Telegram e grupo WhatsApp — tudo no formato profissional:

```
👗 Moda Feminina

Camiseta Tech Light Insider

De R$189,00 | Por R$57,00 👑
🏷️ 69% OFF — Economia: R$132,00
Cupom: CUPOMPRAMODA ⚠️

🛒 Achado no Mercado Livre
👉 https://produto.link/afiliado
```

---

## PASSO 1 — Pré-requisitos

Instale o Python (versão 3.11 ou superior):
- Windows: https://www.python.org/downloads/
- Ubuntu/Linux: `sudo apt install python3 python3-pip`

Verifique: `python --version`

---

## PASSO 2 — Instalar dependências

```bash
# Abra o terminal na pasta do projeto
pip install -r requirements.txt
```

---

## PASSO 3 — Criar o Bot do Telegram

1. Abra o Telegram e procure por **@BotFather**
2. Envie `/newbot`
3. Escolha um nome: ex. `Promoções ML Radar`
4. Escolha um usuário: ex. `PromocoesMLRadarBot`
5. Copie o **token** que ele gerar (parece: `7123456789:AAH...`)

### Criar seu canal:
1. Telegram → Novo Canal
2. Dê um nome chamativo: `🔥 Promoções ML — Radar de Ofertas`
3. Tipo: **Público** (para crescer mais rápido)
4. Username: `@promoml_radar` (exemplo)
5. **Adicione seu bot como Administrador** do canal

### Pegar o ID (se canal privado):
- Adicione `@userinfobot` ao canal e envie qualquer mensagem
- Ele retorna o ID no formato `-100...`

---

## PASSO 4 — Configurar conta de Afiliado ML

1. Acesse: https://afiliados.mercadolivre.com.br
2. Cadastre-se (gratuito)
3. No painel, copie seu **ID de afiliado** (ex: `gabriel_promo`)
4. Configure o parâmetro `ML_AFILIADO_ID` no `config.py`

> ⚠️ Sem o ID de afiliado, os links não rastreiam suas vendas!

---

## PASSO 5 — Configurar WhatsApp (Evolution API)

### Opção A — Railway (recomendado, gratuito):

1. Acesse https://railway.app e crie conta
2. Clique em **New Project → Deploy from GitHub**
3. Use o repositório oficial: `EvolutionAPI/evolution-api`
4. Após o deploy, copie a URL gerada (ex: `https://sua-api.railway.app`)

### Opção B — Local (para testes):

```bash
# Requer Docker instalado
docker run -p 8080:8080 atendai/evolution-api:latest
```

### Criar instância e escanear QR Code:

```bash
# Substituir pela sua URL e apikey
curl -X POST https://sua-api.railway.app/instance/create \
  -H "Content-Type: application/json" \
  -H "apikey: SUA_APIKEY" \
  -d '{"instanceName": "minha-instancia", "qrcode": true}'
```

1. Acesse: `https://sua-api.railway.app/instance/qrcode/minha-instancia/qr`
2. Escaneie o QR Code com o WhatsApp do número que enviará as promoções
3. Confirme: `https://sua-api.railway.app/instance/connectionState/minha-instancia`

### Pegar ID do grupo WhatsApp:
- Crie um grupo → Adicione o número conectado como admin
- Envie uma mensagem no grupo
- Veja os logs da Evolution API para pegar o ID no formato `5511...@g.us`

---

## PASSO 6 — Editar o config.py

Abra o arquivo `config.py` e preencha:

```python
# Telegram
TELEGRAM_TOKEN = "7123456789:AAH..."   # seu token do BotFather
TELEGRAM_CANAL = "@promoml_radar"      # ou "-100123456" se privado

# WhatsApp
EVOLUTION_URL    = "https://sua-api.railway.app"
EVOLUTION_APIKEY = "sua-chave-aqui"
WA_INSTANCIA     = "minha-instancia"
WA_GRUPO_ID      = "5511999999999-1234567890@g.us"

# Afiliado
ML_AFILIADO_ID = "gabriel_promo"
```

---

## PASSO 7 — Testar localmente

```bash
python main.py
```

Você deve ver no terminal:
```
✅ Banco de dados OK
✅ Telegram OK
✅ WhatsApp OK
▶️  Executando ciclo inicial...
[💊 Suplementos] 3 aprovados
[👗 Moda Feminina] 2 aprovados
✅ Telegram: 5 enviados | 0 falhas
✅ WhatsApp: 5 enviados | 0 falhas
```

---

## PASSO 8 — Deploy gratuito (rodar 24/7)

### Railway.app (mais fácil):

1. Crie conta em https://railway.app
2. **New Project → Deploy from local**
3. Faça upload da pasta `bot_promocoes/`
4. Em **Variables**, adicione as variáveis do `config.py`
5. O robô roda automaticamente e de graça

### Render.com (alternativa):

1. Crie conta em https://render.com
2. **New → Background Worker**
3. Conecte ao repositório ou faça upload
4. Build command: `pip install -r requirements.txt`
5. Start command: `python main.py`

---

## Adicionar cupons manualmente

Edite o dicionário `CUPONS_MANUAIS` no `ml_scraper.py`:

```python
CUPONS_MANUAIS = {
    "moda":        "NOVODESCONTO",
    "suplementos": "SUPMELI25",
    # adicione mais conforme surgem promoções
}
```

> 💡 Dica: Siga canais de cupons no Telegram como @CupomNaçãoBR para ficar atualizado.

---

## Dúvidas frequentes

**O robô pode ser banido?**
- Telegram: Não, canais de promoção são permitidos.
- WhatsApp: Risco baixo mas existe. Use um número secundário.

**Quanto tempo para aparecer comissões?**
- As comissões aparecem no painel de afiliados ML em até 48h após a venda.

**Posso mudar o intervalo de busca?**
- Sim. No `config.py`, altere `INTERVALO_MINUTOS = 120` para o valor desejado.
- Recomendo no mínimo 60 minutos para não sobrecarregar a API.

**Como crescer o canal rápido?**
- Divulgue em grupos de WhatsApp que você já participa
- Poste em comunidades do Facebook e Instagram
- Use palavras-chave no nome: "promoções", "ofertas", "desconto"

---

## Estrutura de arquivos

```
bot_promocoes/
├── config.py           ← Edite este (suas chaves e preferências)
├── ml_scraper.py       ← Busca produtos + formata mensagens + cupons
├── banco_dados.py      ← Evita duplicatas (SQLite local)
├── telegram_sender.py  ← Envia para canal Telegram
├── whatsapp_sender.py  ← Envia para grupo WhatsApp
├── main.py             ← Roda tudo (entry point)
├── requirements.txt    ← Dependências Python
└── promocoes.db        ← Criado automaticamente pelo bot
```

---

Bons negócios! 🚀
