# ═══════════════════════════════════════════════════════════
#  main.py — Orquestrador principal do robô de promoções
#  Versão: somente Telegram
#  Execute com: python main.py
# ═══════════════════════════════════════════════════════════

import time
import logging
import schedule
from datetime import datetime

import banco_dados
import ml_scraper
import telegram_sender
from config import INTERVALO_MINUTOS, HORARIO_INICIO, HORARIO_FIM

log = logging.getLogger(__name__)

# ─── Ciclo principal ─────────────────────────────────────────

def executar_ciclo():
    agora = datetime.now()
    hora_atual = agora.hour

    if not (HORARIO_INICIO <= hora_atual < HORARIO_FIM):
        log.info(f"Fora do horário ({hora_atual}h). Próximo ciclo: {HORARIO_INICIO}h")
        return

    log.info("=" * 55)
    log.info(f"INICIANDO CICLO — {agora.strftime('%d/%m/%Y %H:%M')}")
    log.info("=" * 55)

    # 1. Buscar produtos
    todos_produtos = ml_scraper.buscar_todas_categorias()

    if not todos_produtos:
        log.warning("Nenhum produto encontrado neste ciclo.")
        return

    # 2. Filtrar já enviados
    novos_produtos = [
        p for p in todos_produtos
        if not banco_dados.ja_foi_enviado(p["id"], horas=48)
    ]

    log.info(f"Produtos novos: {len(novos_produtos)}")

    if not novos_produtos:
        log.info("Todos os produtos já foram enviados recentemente.")
        return

    # 3. Enviar no Telegram
    log.info("Enviando para Telegram...")
    resultado_tg = telegram_sender.enviar_lista_produtos(novos_produtos)

    # 4. Salvar no banco
    for produto in novos_produtos:
        banco_dados.registrar_envio(produto, ["telegram"])

    # 5. Limpar registros antigos (1x por dia)
    if agora.hour == HORARIO_INICIO:
        banco_dados.limpar_registros_antigos(dias=7)

    # 6. Resumo
    stats = banco_dados.obter_estatisticas()
    log.info("─" * 55)
    log.info(f"✅ Telegram: {resultado_tg['enviados']} enviados | {resultado_tg['falhas']} falhas")
    log.info(f"📊 Total histórico: {stats['total_enviados']} | Hoje: {stats['enviados_hoje']}")
    log.info("─" * 55)

# ─── Inicialização ────────────────────────────────────────────

def inicializar():
    log.info("🤖 Robô de Promoções ML — Iniciando (modo Telegram)...")

    banco_dados.inicializar()
    log.info("✅ Banco de dados OK")

    if telegram_sender.testar_conexao():
        log.info("✅ Telegram OK")
    else:
        log.error("❌ Telegram FALHOU — verifique TELEGRAM_TOKEN no config.py")
        return False

    return True

# ─── Agendamento ──────────────────────────────────────────────

def main():
    if not inicializar():
        log.error("Falha na inicialização. Corrija os erros acima e reinicie.")
        return

    log.info("▶️  Executando ciclo inicial...")
    executar_ciclo()

    schedule.every(INTERVALO_MINUTOS).minutes.do(executar_ciclo)
    log.info(f"⏰ Novo ciclo a cada {INTERVALO_MINUTOS} minutos")
    log.info(f"🕐 Funcionamento: {HORARIO_INICIO}h às {HORARIO_FIM}h")
    log.info("🟢 Robô rodando. Pressione Ctrl+C para parar.\n")

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\n🔴 Robô encerrado pelo usuário.")
