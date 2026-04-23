import psycopg2
import os


def get_connection():
    try:
        # >>> PRODUÇÃO (Render / Neon)
        if os.getenv("PGHOST"):
            return psycopg2.connect(
                host=os.getenv("PGHOST"),
                database=os.getenv("PGDATABASE"),
                user=os.getenv("PGUSER"),
                password=os.getenv("PGPASSWORD"),
                sslmode=os.getenv("PGSSLMODE", "require")
            )

        # >>> LOCAL (seu PC)
        return psycopg2.connect(
            host="localhost",
            database="catalogo_filmes",
            user="postgres",
            password="1234"
        )

    except Exception as ex:
        print(f'Erro ao conectar no banco de dados: {ex}')
        return None