# ═══════════════════════════════════════════════════════════
#  main_once.py — GitHub Actions (raiz do repositório)
#  Adaptado para estrutura atual do projeto
# ═══════════════════════════════════════════════════════════

import logging
import sys
import os

# Aponta para onde estão os módulos (mesma pasta que main_once.py)
sys.path.insert(0, os.path.dirname(__file__))

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

    banco_dados.inicializar()
    log.info("✅ Banco de dados OK")

    if not telegram_sender.testar_conexao():
        log.error("❌ Telegram FALHOU — verifique o secret TELEGRAM_TOKEN")
        sys.exit(1)
    log.info("✅ Telegram OK")

    todos = ml_scraper.buscar_todas_categorias()

    if not todos:
        log.warning("Nenhum produto encontrado neste ciclo.")
        sys.exit(0)

    novos = [p for p in todos if not banco_dados.ja_foi_enviado(p["id"], horas=48)]
    log.info(f"Produtos novos: {len(novos)}")

    if not novos:
        log.info("Todos já foram enviados recentemente.")
        sys.exit(0)

    resultado = telegram_sender.enviar_lista_produtos(novos)

    for p in novos:
        banco_dados.registrar_envio(p, ["telegram"])

    log.info(f"✅ Enviados: {resultado['enviados']} | ❌ Falhas: {resultado['falhas']}")

if __name__ == "__main__":
    main()
