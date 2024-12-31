import psycopg2
from psycopg2 import sql

# Configuración de la base de datos
DATABASE_URL = "postgresql://postgres:PNZhePLOpOgkrfPmTVHemsFINfqnETsv@junction.proxy.rlwy.net:34990/railway"

def get_connection():
    """Obtiene una conexión a la base de datos."""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def execute_query(query, params=None):
    """Ejecuta una consulta SQL y devuelve los resultados."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    if query.strip().upper().startswith("SELECT"):
        result = cur.fetchall()
    else:
        conn.commit()
        result = None
    cur.close()
    conn.close()
    return result