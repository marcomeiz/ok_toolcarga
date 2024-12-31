from db import execute_query

# Probar la conexión
result = execute_query("SELECT version();")
print("Conexión exitosa. Versión de PostgreSQL:", result[0][0])