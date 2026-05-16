# ═══════════════════════════════════════════════════════════
#  main_once.py — Versão para GitHub Actions
#  Roda UM ciclo completo e encerra (sem loop infinito)
# ═══════════════════════════════════════════════════════════

import logging
import sys
import os

# Adiciona a pasta bot_promocoes ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot_promocoes"))

import banco_dados
import ml_scraper
import telegram_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
log = logging.getLogger(__name__)

def main():
    log.info("🤖 GitHub Actions — Iniciando ciclo...")

    # Banco de dados
    banco_dados.inicializar()
    log.info("✅ Banco de dados OK")

    # Testar Telegram
    if not telegram_sender.testar_conexao():
        log.error("❌ Telegram FALHOU")
        sys.exit(1)
    log.info("✅ Telegram OK")

    # Buscar produtos
    todos = ml_scraper.buscar_todas_categorias()

    if not todos:
        log.warning("Nenhum produto encontrado neste ciclo.")
        sys.exit(0)

    # Filtrar já enviados
    novos = [p for p in todos if not banco_dados.ja_foi_enviado(p["id"], horas=48)]
    log.info(f"Produtos novos: {len(novos)}")

    if not novos:
        log.info("Todos já foram enviados recentemente.")
        sys.exit(0)

    # Enviar no Telegram
    resultado = telegram_sender.enviar_lista_produtos(novos)

    # Salvar no banco
    for p in novos:
        banco_dados.registrar_envio(p, ["telegram"])

    log.info(f"✅ Enviados: {resultado['enviados']} | ❌ Falhas: {resultado['falhas']}")
    log.info("Ciclo concluído.")

if __name__ == "__main__":
    main()
