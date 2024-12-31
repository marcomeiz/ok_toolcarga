from db import execute_query
from datetime import datetime
import requests
import json  # Para imprimir el JSON de manera legible

# Configuración API de COR
API_KEY = "94466f37-58fe-4a25-ad43-1eeb14f3e39c"
CLIENT_SECRET = "1fa875c460748f63f66ce65e508415bb"
BASE_URL = "https://api.projectcor.com"

def obtener_token_cor(api_key, client_secret):
    """Obtiene el token de acceso usando client_credentials."""
    url_token = f"{BASE_URL}/v1/oauth/token?grant_type=client_credentials"
    import base64
    basic_creds = base64.b64encode(f"{api_key}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {basic_creds}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    resp = requests.post(url_token, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("access_token")
    else:
        return None
    
def obtener_tareas_cor(access_token, page=1, per_page=10):
    """Obtiene las tareas de COR, paginadas."""
    url_tasks = f"{BASE_URL}/v1/tasks?page={page}&perPage={per_page}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    resp = requests.get(url_tasks, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"Error al obtener tareas: {resp.status_code} - {resp.text}")
        return None

def obtener_todas_las_tareas(access_token):
    """Obtiene todas las tareas de COR."""
    all_tasks = []
    page = 1
    per_page = 200  # Número máximo de tareas por página
    while True:
        data = obtener_tareas_cor(access_token, page=page, per_page=per_page)
        if not data or "data" not in data or not data["data"]:
            break
        tasks = data["data"]
        all_tasks.extend(tasks)
        print(f"Obtenidas {len(tasks)} tareas de la página {page}.")
        page += 1
    return all_tasks

def mapear_tarea(tarea):
    """Mapea una tarea de COR a los campos de la tabla cor_tareas."""
    # Extraer nombres de colaboradores
    colaboradores = tarea.get("collaborators", [])
    nombres_colaboradores = [
        f"{colab.get('first_name', '')} {colab.get('last_name', '')}".strip()
        for colab in colaboradores
    ]
    nombres_colaboradores_str = ", ".join(nombres_colaboradores)  # Convertir a cadena separada por comas

    return {
        "cliente": tarea.get("project", {}).get("client", {}).get("name", ""),
        "proyecto": tarea.get("project", {}).get("name", ""),
        "id_proyecto": tarea.get("project", {}).get("id"),
        "tarea": tarea.get("title", ""),
        "id_tarea": tarea.get("id"),
        "estado": tarea.get("status", ""),
        "fecha_inicio": tarea.get("datetime"),
        "finalizacion": tarea.get("deadline"),
        "project_manager": f"{tarea.get('pm', {}).get('first_name', '')} {tarea.get('pm', {}).get('last_name', '')}".strip(),
        "colaboradores": nombres_colaboradores_str,  # Cadena de nombres separados por comas
        "horas_cargadas": tarea.get("hour_charged", 0.0),
        "horas_estimadas": tarea.get("estimated", 0.0),
        "link_tarea": f"https://ooptimo.cor.works/tasks/{tarea.get('id')}"
    }





























from db import execute_query

def insertar_tarea(tarea):
    """Inserta una tarea en la tabla cor_tareas."""
    query = """
    INSERT INTO cor_tareas (
        cliente, proyecto, id_proyecto, tarea, id_tarea, estado,
        fecha_inicio, finalizacion, project_manager, colaboradores,
        horas_cargadas, horas_estimadas, link_tarea
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    datos = mapear_tarea(tarea)
    execute_query(query, tuple(datos.values()))

if __name__ == "__main__":
    access_token = obtener_token_cor(API_KEY, CLIENT_SECRET)
    if not access_token:
        print("Error al obtener el token de COR.")
    else:
        # Obtener todas las tareas
        print("Obteniendo todas las tareas de COR...")
        tareas = obtener_todas_las_tareas(access_token)
        print(f"Total de tareas obtenidas: {len(tareas)}")

        # Insertar cada tarea en la base de datos
        for i, tarea in enumerate(tareas, start=1):
            try:
                insertar_tarea(tarea)
                if i % 100 == 0:  # Mostrar progreso cada 100 tareas
                    print(f"Tareas insertadas: {i}/{len(tareas)}")
            except Exception as e:
                print(f"Error al insertar la tarea {tarea['title']}: {e}")
        print("Migración completada.")






































