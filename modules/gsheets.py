import pandas as pd
from datetime import datetime, timedelta
import streamlit as st # Necesario para st.error, etc.
import gspread

# --- 2. FUNCIONES DE LA APLICACIÓN (GOOGLE SHEETS & GEMINI) ---
# --- Funciones de Carga de Datos (Tu código original + la nueva para el plan semanal) ---
def cargar_perfil(client, username):
    try:
        spreadsheet = client.open("AI.TRAIN-U")
        sheet_perfil = spreadsheet.worksheet("Perfil")
        data = sheet_perfil.get_all_records()
        df = pd.DataFrame(data)
        df_usuario = df[df['UserID'] == username]
        if df_usuario.empty:
            return {"Error": "No se encontró un perfil para este usuario en la hoja 'Perfil'."}
        perfil_dict = {row['Variable']: row['Valor'] for index, row in df_usuario.iterrows()}
        return perfil_dict
    except Exception as e:
        return {"Error": f"Ocurrió un error al cargar el perfil: {e}"}

def cargar_historial(client, username):
    try:
        spreadsheet = client.open("AI.TRAIN-U")
        sheet_registro = spreadsheet.worksheet("Registro_Diario")
        data = sheet_registro.get_all_records()
        df = pd.DataFrame(data)
        df_usuario = df[df['UserID'] == username]
        return df_usuario
    except Exception:
        return pd.DataFrame()

def cargar_plan_semana(client, username):
    """(NUEVA) Carga el plan de la semana actual para un usuario."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        data = sheet.get_all_records()
        if not data: return None
        df = pd.DataFrame(data)
        today = datetime.today()
        lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
        df_semana = df[(df['UserID'] == username) & (df['Semana_Del'] == lunes_actual)]
        if df_semana.empty:
            return None
        return df_semana.iloc[0].to_dict()
    except Exception:
        return None

# --- Funciones de Guardado/Actualización de Datos ---
def guardar_registro(client, username, nueva_fila_datos):
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_registro = spreadsheet.worksheet("Registro_Diario")
    fila_completa = [username] + nueva_fila_datos
    sheet_registro.append_row(fila_completa)
    
def guardar_plan_semana_nuevo(client, username, plan_generado_str):
    """Guarda un plan semanal recién creado, rellenando correctamente todas las columnas."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        today = datetime.today()
        lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        nueva_fila = [username, lunes_actual]
        planes_diarios_limpios = [linea.strip() for linea in plan_generado_str.strip().split('\n')]
        planes_por_dia = {}
        for linea in planes_diarios_limpios:
            if ':' in linea:
                partes = linea.split(':', 1)
                dia_semana = partes[0].strip()
                plan_desc = partes[1].strip()
                if dia_semana in dias:
                    planes_por_dia[dia_semana] = plan_desc
        for dia in dias:
            plan_del_dia = planes_por_dia.get(dia, "Descanso")
            nueva_fila.extend([plan_del_dia, "Pendiente"])
        nueva_fila.append(plan_generado_str.strip())
        sheet.append_row(nueva_fila)
        st.success("Plan semanal guardado correctamente en la base de datos.")
    except Exception as e:
        st.error(f"Ocurrió un error crítico al guardar el nuevo plan semanal: {e}")
        
# (NUEVA Y MEJORADA) Esta función actualiza tanto el plan como el estado
def actualizar_plan_completo(client, username, dia, nuevo_plan, nuevo_estado):
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        today = datetime.today()
        lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
        
        # (CORREGIDO) Lógica para encontrar la fila del usuario
        cell_semana = sheet.findall(lunes_actual)
        fila_usuario = -1
        for cell in cell_semana:
            user_en_fila = sheet.cell(cell.row, 1).value
            if user_en_fila == username:
                fila_usuario = cell.row
                break
        
        if fila_usuario != -1:
            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            columna_plan_idx = 3 + (dias_semana.index(dia) * 2)
            columna_estado_idx = columna_plan_idx + 1
            
            # Actualizamos 2 celdas en una sola petición para optimizar
            sheet.update_cells([
                gspread.Cell(fila_usuario, columna_plan_idx, nuevo_plan),
                gspread.Cell(fila_usuario, columna_estado_idx, nuevo_estado)
            ])
            
    except Exception as e:
        st.warning(f"No se pudo actualizar el plan semanal: {e}")

# --- (NUEVA) FUNCIÓN PARA GUARDAR EL ENTRENO DETALLADO ---
def guardar_entreno_detallado(client, username, fecha, df_entreno):
    """Guarda cada fila de un DataFrame de entreno en el Sheet."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Registro_Detallado")
        
        # Preparamos las filas para añadir
        filas_a_anadir = []
        for index, row in df_entreno.iterrows():
            # Ignoramos filas vacías
            if row["Ejercicio"] and row["Repeticiones"] and row["Peso_kg"]:
                filas_a_anadir.append([
                    username,
                    fecha,
                    row["Ejercicio"],
                    row["Serie"],
                    row["Repeticiones"],
                    row["Peso_kg"]
                ])
        
        if filas_a_anadir:
            sheet.append_rows(filas_a_anadir) # append_rows es más eficiente
            return True
        return False
        
    except Exception as e:
        st.error(f"Error al guardar el entreno detallado: {e}")
        return False

def cargar_lista_ejercicios(client):
    """Carga la lista de todos los ejercicios disponibles."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Ejercicios")
        # get_col(1) coge todos los valores de la primera columna
        lista_ejercicios = sheet.get_col(1, include_empty=False)[1:] # [1:] para saltar la cabecera
        return lista_ejercicios
    except:
        # Si falla, devuelve una lista de ejemplo para que la app no se rompa
        return ["Press Banca", "Sentadilla", "Peso Muerto"]

# --- (NUEVA) FUNCIÓN PARA CARGAR EL HISTORIAL DETALLADO ---
def cargar_historial_detallado(client, username):
    """Carga el historial de ejercicios detallado."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Registro_Detallado")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame()
        return df[df['UserID'] == username]
    except Exception:
        return pd.DataFrame()
