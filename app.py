# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, date
import holidays
from workalendar.europe.spain import Catalonia
from calendar import monthrange

# Configuración de la API de Factorial
FACTORIAL_API_KEY = "787a56c5a761f4450cddce0ed763628dd530606632116a45c965d80f6b4a73de"
FACTORIAL_BASE_URL = "https://api.factorialhr.com/api/2024-10-01"
HEADERS = {
    "accept": "application/json",
    "x-api-key": FACTORIAL_API_KEY,
}

# Configuración API de COR
API_KEY = "94466f37-58fe-4a25-ad43-1eeb14f3e39c"
CLIENT_SECRET = "1fa875c460748f63f66ce65e508415bb"
BASE_URL = "https://api.projectcor.com"

# Configuración de días festivos (España, Barcelona)
festivos_barcelona = holidays.Spain(subdiv="CT")  # Cataluña incluye Barcelona

# Nombres de los meses en español
NOMBRES_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
]

# Mapeo de nombres de empleados
NOMBRE_MAPPING = {
    "albert sunyer": "albert sunyer vilafranca",
    "david collado": "david collado preciado",
    "esther janer": "esther janer roig",
    "vanessa dueñas": "vanessa dueñas moga",
    "ariadna de angulo": "ariadna de angulo villa",
    "norma vila": "norma vila muñoz"
}

# Obtener el mes y año actual
now = datetime.now()
current_month = now.month
current_year = now.year

# Título de la app
st.title("Dashboard de Ausencias y Horas Laborables")

# Sidebar para seleccionar el mes y año
st.sidebar.header("Selecciona el Mes y Año")
selected_year = st.sidebar.selectbox("Año", range(2023, 2025), index=current_year - 2023)
selected_month = st.sidebar.selectbox("Mes", range(1, 13), index=current_month - 1)

# Funciones principales
def obtener_tipos_ausencia():
    """Obtiene los tipos de ausencia desde Factorial"""
    url = f"{FACTORIAL_BASE_URL}/resources/timeoff/leave_types"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    tipos = response.json().get('data', [])
    return {tipo['id']: tipo['translated_name'] for tipo in tipos}

def obtener_ausencias():
    """Obtiene todas las ausencias desde Factorial"""
    url = f"{FACTORIAL_BASE_URL}/resources/timeoff/leaves"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get('data', [])

def calcular_dias_laborables_por_mes(inicio, fin):
    """Calcula los días laborables por mes excluyendo sábados, domingos y festivos"""
    dias = pd.date_range(start=inicio, end=fin, freq='B')  # Días laborables (excluye sábados y domingos)
    dias_laborables = dias[~dias.isin(festivos_barcelona)]  # Excluir festivos
    dias_por_mes = dias_laborables.to_series().groupby(dias_laborables.to_period("M")).size()
    return dias_por_mes

def obtener_token_cor(api_key, client_secret):
    """Obtiene el token de acceso usando client_credentials"""
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
    """Obtiene las tareas de COR, paginadas"""
    url_tasks = f"{BASE_URL}/v1/tasks?page={page}&perPage={per_page}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    resp = requests.get(url_tasks, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        return None

def normalizar_nombre(nombre):
    """Normaliza el nombre del empleado para unificar diferentes versiones"""
    nombre_norm = ' '.join(nombre.lower().strip().split())
    return NOMBRE_MAPPING.get(nombre_norm, nombre_norm)

def calcular_ausencias_empleado(empleado_nombre, anio, mes):
    """Calcula los días de ausencia de un empleado para un mes específico"""
    ausencias = obtener_ausencias()
    dias_vacaciones = 0
    dias_otras_ausencias = 0
    dias_teletrabajo = 0
    ids_no_descuentan = {2280065}  # Día extra teletrabajo
    empleado_nombre_norm = normalizar_nombre(empleado_nombre)
    for ausencia in ausencias:
        nombre_ausencia = normalizar_nombre(ausencia.get("employee_full_name", ""))
        if nombre_ausencia != empleado_nombre_norm:
            continue
        inicio = pd.to_datetime(ausencia["start_on"])
        fin = pd.to_datetime(ausencia["finish_on"])
        if inicio.year != anio or inicio.month != mes:
            continue
        dias = calcular_dias_laborables_por_mes(inicio, fin)[pd.Period(f"{anio}-{mes:02d}")]
        tipo_id = ausencia.get("leave_type_id")
        if tipo_id in ids_no_descuentan:
            dias_teletrabajo += dias
        elif tipo_id == 2276680:  # Vacaciones
            dias_vacaciones += dias
        else:  # Otras ausencias
            dias_otras_ausencias += dias
    return dias_vacaciones, dias_otras_ausencias, dias_teletrabajo

def calcular_dias_laborables_festivos(year, month):
    """Calcula los días laborables y festivos para un mes específico"""
    cal = Catalonia()
    _, total_days = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, total_days)
    dias_laborables = 0
    for day in range(1, total_days + 1):
        current_date = date(year, month, day)
        if current_date.weekday() < 5:  # Lunes a viernes
            dias_laborables += 1
    holidays = cal.holidays(year)
    festivos_laborables = 0
    for dia, _ in holidays:
        if start_date <= dia <= end_date and dia.weekday() < 5:
            festivos_laborables += 1
    dias_laborables_netos = dias_laborables - festivos_laborables
    return dias_laborables_netos, festivos_laborables

def calcular_horas_disponibles(year, month, vacaciones_en_dias, otras_ausencias_en_dias, buffer_porcentaje=0.1):
    """Calcula las horas disponibles reales tras restar vacaciones, festivos y buffer"""
    dias_laborables, _ = calcular_dias_laborables_festivos(year, month)
    horas_por_dia = 7 if month == 8 else 8
    horas_brutas = dias_laborables * horas_por_dia
    horas_vacaciones = vacaciones_en_dias * horas_por_dia
    horas_otras_ausencias = otras_ausencias_en_dias * horas_por_dia
    buffer = horas_brutas * buffer_porcentaje
    horas_disponibles_reales = horas_brutas - horas_vacaciones - horas_otras_ausencias - buffer
    return horas_disponibles_reales

# Caché para evitar múltiples llamadas a la API
@st.cache_data
def fetch_ausencias():
    return obtener_ausencias()

@st.cache_data
def fetch_tipos_ausencia():
    return obtener_tipos_ausencia()

@st.cache_data
def fetch_tasks():
    access_token = obtener_token_cor(API_KEY, CLIENT_SECRET)
    if not access_token:
        return []
    all_tasks = []
    page = 1
    per_page = 200
    while True:
        data = obtener_tareas_cor(access_token, page=page, per_page=per_page)
        if not data or "data" not in data:
            break
        tasks = data["data"]
        if not tasks:
            break
        filtered_tasks = [t for t in tasks if t.get("hour_charged", 0) > 0 or t.get("estimated", 0) > 0]
        all_tasks.extend(filtered_tasks)
        page += 1
    return all_tasks

def process_tasks(tasks):
    """Procesa las tareas y construye el diccionario empleadosPorMes"""
    empleadosPorMes = {}
    for task in tasks:
        dt_str = task.get("datetime")
        if not dt_str:
            continue
        dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        year = dt_obj.year
        month = dt_obj.month
        month_name = NOMBRES_MESES[month - 1]
        sheetName = f"{month_name}-{year}"
        if sheetName not in empleadosPorMes:
            empleadosPorMes[sheetName] = {}
        hour_charged = task.get("hour_charged", 0)
        estimated_min = task.get("estimated", 0)
        estimated_hours = estimated_min / 60.0
        colaboradores = task.get("collaborators", [])
        if not colaboradores:
            continue
        num_cols = len(colaboradores)
        if num_cols == 0:
            continue
        hc_por_colab = hour_charged / num_cols
        est_por_colab = estimated_hours / num_cols
        for colab in colaboradores:
            raw_name = f"{colab.get('first_name','')} {colab.get('last_name','')}".strip()
            colab_name = normalizar_nombre(raw_name)
            if colab_name not in empleadosPorMes[sheetName]:
                empleadosPorMes[sheetName][colab_name] = {
                    "horas_cargadas": 0.0,
                    "horas_estimadas": 0.0,
                    "vacaciones": 0,
                    "otras_ausencias": 0,
                    "teletrabajo": 0
                }
            empleadosPorMes[sheetName][colab_name]["horas_cargadas"] += hc_por_colab
            empleadosPorMes[sheetName][colab_name]["horas_estimadas"] += est_por_colab
    return empleadosPorMes

def update_empleados_por_mes(empleadosPorMes):
    """Actualiza el diccionario empleadosPorMes con datos de ausencias"""
    tipos = fetch_tipos_ausencia()
    ausencias = fetch_ausencias()
    for sheetName, colaboradores in empleadosPorMes.items():
        mes_nombre, anio_str = sheetName.split("-")
        anio = int(anio_str)
        mes = NOMBRES_MESES.index(mes_nombre) + 1
        for colaborador in colaboradores.keys():
            vacaciones, otras_ausencias, teletrabajo = calcular_ausencias_empleado(colaborador, anio, mes)
            empleadosPorMes[sheetName][colaborador].update({
                "vacaciones": vacaciones,
                "otras_ausencias": otras_ausencias,
                "teletrabajo": teletrabajo
            })
    return empleadosPorMes

# Fetch and process data
tasks = fetch_tasks()
empleadosPorMes = process_tasks(tasks)
empleadosPorMes = update_empleados_por_mes(empleadosPorMes)

# Get the selected sheetName
selected_month_name = NOMBRES_MESES[selected_month - 1]
sheetName = f"{selected_month_name}-{selected_year}"

# Check if the sheetName exists
if sheetName in empleadosPorMes:
    colaboradores_data = empleadosPorMes[sheetName]
    # Create a DataFrame
    df = pd.DataFrame(colaboradores_data).T.reset_index()
    df.rename(columns={"index": "Colaborador"}, inplace=True)
    # Calculate available hours
    df["Horas Disponibles"] = df.apply(lambda row: calcular_horas_disponibles(selected_year, selected_month, row["vacaciones"], row["otras_ausencias"]), axis=1)
    # Calculate % de Carga Planificada
    df["% Carga Planificada"] = df.apply(lambda row: f"{round((row['horas_estimadas'] / row['Horas Disponibles']) * 100, 1)}%" if row['Horas Disponibles'] > 0 else "0%", axis=1)
    # Calculate % de Carga Real
    df["% Carga Real"] = df.apply(lambda row: f"{round((row['horas_cargadas'] / row['Horas Disponibles']) * 100, 1)}%" if row['Horas Disponibles'] > 0 else "0%", axis=1)
    # Display the data
    st.write(f"Datos para {sheetName}")
    st.dataframe(df)
    # Create a bar chart
    fig = px.bar(df, x='Colaborador', y='Horas Disponibles', title='Horas Disponibles por Empleado')
    st.plotly_chart(fig)
else:
    st.write(f"No hay datos disponibles para {sheetName}")