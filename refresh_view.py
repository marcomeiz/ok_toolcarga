import psycopg2
import os
import logging
from datetime import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("refresh_view.log"), logging.StreamHandler()],
)

# Obtener credenciales de la base de datos desde variables de entorno
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

def refresh_materialized_view():
    """Refresca la vista materializada monthly_collaborator_hours."""
    try:
        # Conectar a la base de datos
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Ejecutar el REFRESH MATERIALIZED VIEW
        logging.info("Refrescando la vista materializada...")
        cur.execute("REFRESH MATERIALIZED VIEW monthly_collaborator_hours;")
        conn.commit()

        # Cerrar la conexión
        cur.close()
        conn.close()

        logging.info("Vista materializada refrescada exitosamente.")
    except Exception as e:
        logging.error(f"Error al refrescar la vista materializada: {e}")

if __name__ == "__main__":
    refresh_materialized_view()