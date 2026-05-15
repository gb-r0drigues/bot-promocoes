# ═══════════════════════════════════════════════════════════
#  banco_dados.py — Controle de produtos já enviados
#  Usa SQLite local, sem precisar instalar nada extra
# ═══════════════════════════════════════════════════════════

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

CAMINHO_DB = Path(__file__).parent / "promocoes.db"

# ─── Inicializar banco de dados ──────────────────────────────

def inicializar():
    """Cria o banco de dados e as tabelas se não existirem."""
    with sqlite3.connect(CAMINHO_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS produtos_enviados (
                id              TEXT PRIMARY KEY,
                titulo          TEXT NOT NULL,
                preco           REAL NOT NULL,
                desconto        INTEGER NOT NULL,
                categoria       TEXT NOT NULL,
                enviado_em      TEXT NOT NULL,
                plataformas     TEXT NOT NULL DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs_envio (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id      TEXT NOT NULL,
                plataforma      TEXT NOT NULL,
                status          TEXT NOT NULL,
                mensagem        TEXT,
                data_hora       TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_enviado_em
            ON produtos_enviados (enviado_em)
        """)

        conn.commit()
    log.info(f"Banco de dados inicializado: {CAMINHO_DB}")

# ─── Verificar se produto já foi enviado ─────────────────────

def ja_foi_enviado(produto_id: str, horas: int = 48) -> bool:
    """
    Retorna True se o produto foi enviado nas últimas N horas.
    Evita repostar o mesmo produto com frequência.
    """
    limite = (datetime.now() - timedelta(hours=horas)).isoformat()

    with sqlite3.connect(CAMINHO_DB) as conn:
        resultado = conn.execute(
            "SELECT 1 FROM produtos_enviados WHERE id = ? AND enviado_em >= ?",
            (produto_id, limite)
        ).fetchone()

    return resultado is not None

# ─── Registrar produto enviado ───────────────────────────────

def registrar_envio(produto: dict, plataformas: list):
    """
    Salva o produto no banco para não repostar.
    plataformas: ex. ["telegram", "whatsapp"]
    """
    agora = datetime.now().isoformat()

    with sqlite3.connect(CAMINHO_DB) as conn:
        # Upsert: se já existe, atualiza as plataformas
        conn.execute("""
            INSERT INTO produtos_enviados (id, titulo, preco, desconto, categoria, enviado_em, plataformas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                enviado_em = excluded.enviado_em,
                plataformas = excluded.plataformas
        """, (
            produto["id"],
            produto["titulo"],
            produto["preco"],
            produto["desconto"],
            produto["categoria"],
            agora,
            ",".join(plataformas)
        ))
        conn.commit()

# ─── Registrar log de envio ──────────────────────────────────

def registrar_log(produto_id: str, plataforma: str, status: str, mensagem: str = ""):
    """Registra cada tentativa de envio para diagnóstico."""
    agora = datetime.now().isoformat()

    with sqlite3.connect(CAMINHO_DB) as conn:
        conn.execute("""
            INSERT INTO logs_envio (produto_id, plataforma, status, mensagem, data_hora)
            VALUES (?, ?, ?, ?, ?)
        """, (produto_id, plataforma, status, mensagem, agora))
        conn.commit()

# ─── Limpar registros antigos ────────────────────────────────

def limpar_registros_antigos(dias: int = 7):
    """Remove registros com mais de N dias para não ocupar disco."""
    limite = (datetime.now() - timedelta(days=dias)).isoformat()

    with sqlite3.connect(CAMINHO_DB) as conn:
        cursor = conn.execute(
            "DELETE FROM produtos_enviados WHERE enviado_em < ?", (limite,)
        )
        removidos = cursor.rowcount
        conn.execute(
            "DELETE FROM logs_envio WHERE data_hora < ?", (limite,)
        )
        conn.commit()

    if removidos > 0:
        log.info(f"Limpeza: {removidos} registros antigos removidos")

# ─── Estatísticas ────────────────────────────────────────────

def obter_estatisticas() -> dict:
    """Retorna estatísticas básicas do banco."""
    with sqlite3.connect(CAMINHO_DB) as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM produtos_enviados"
        ).fetchone()[0]

        hoje = conn.execute(
            "SELECT COUNT(*) FROM produtos_enviados WHERE enviado_em >= ?",
            (datetime.now().strftime("%Y-%m-%d"),)
        ).fetchone()[0]

        por_categoria = conn.execute("""
            SELECT categoria, COUNT(*) as qtd
            FROM produtos_enviados
            GROUP BY categoria
            ORDER BY qtd DESC
        """).fetchall()

    return {
        "total_enviados":    total,
        "enviados_hoje":     hoje,
        "por_categoria":     {cat: qtd for cat, qtd in por_categoria},
    }
