import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. FUNCIONES DE SEGURIDAD Y BASE DE DATOS DE LOGIN ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()
conn = sqlite3.connect('data.db', check_same_thread=False) 
c = conn.cursor()
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')
def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    return c.fetchall()

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
    
def guardar_plan_semanal_nuevo(client, username, plan_generado_str):
    """(CORREGIDO) Guarda un plan semanal recién creado en el Sheet."""
    sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
    today = datetime.today()
    lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    planes_diarios = plan_generado_str.split('\n')
    nueva_fila = [username, lunes_actual]
    
    # Este bucle ahora es más inteligente y tolerante a errores de formato de la IA
    for dia in dias:
        plan_encontrado_para_dia = "Descanso" # Valor por defecto
        for linea in planes_diarios:
            linea_limpia = linea.strip()
            if linea_limpia.startswith(dia):
                partes = linea_limpia.split(':', 1)
                if len(partes) > 1:
                    plan_encontrado_para_dia = partes[1].strip()
                break # Dejamos de buscar una vez que encontramos el día
        nueva_fila.extend([plan_encontrado_para_dia, "Pendiente"])
    
    nueva_fila.append(plan_generado_str)
    sheet.append_row(nueva_fila)
        
def actualizar_estado_semanal(client, username, dia, estado):
    """(NUEVA) Actualiza el estado de un día en el plan semanal."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        today = datetime.today()
        lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
        
        cell_semana = sheet.findall(lunes_actual)
        fila_usuario = -1
        for cell in cell_semana:
            user_en_fila = sheet.cell(cell.row, 1).value
            if user_en_fila == username:
                fila_usuario = cell.row
                break
        
        if fila_usuario != -1:
            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            columna_estado = 3 + (dias_semana.index(dia) * 2) + 1
            sheet.update_cell(fila_usuario, columna_estado, estado)
    except Exception as e:
        st.warning(f"No se pudo actualizar el plan semanal: {e}")

# --- Funciones de IA (Con las nuevas modificaciones) ---
def generar_plan_semanal(perfil):
    """(NUEVA) Genera la estructura de entrenamiento para 7 días."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un planificador de fitness a largo plazo. Basado en el perfil del usuario, genera una estructura de entrenamiento LÓGICA y EQUILIBRADA para los próximos 7 días.
    Perfil: {perfil}
    Responde ÚNICAMENTE con la lista de 7 días, un día por línea, con el formato 'Día: Grupo Muscular o Actividad'. Sé conciso.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar el plan semanal: {e}")
        return None

def generar_plan_diario(perfil, historial_str, datos_hoy, plan_semanal_actual):
    """(MODIFICADA) Genera el plan detallado para mañana, usando el plan semanal como guía."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_manana_idx = (datetime.today().weekday() + 1) % 7
    dia_manana_nombre = dias_semana[dia_manana_idx]
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")

    prompt = f"""
    Eres un entrenador personal y nutricionista. Tu objetivo es crear un plan DETALLADO para mañana.

    **CONTEXTO ESTRATÉGICO:**
    - El plan general para mañana ({dia_manana_nombre}) es: **{lo_que_toca_manana}**.

    **MI PERFIL:** {perfil}
    **MI HISTORIAL RECIENTE:** {historial_str}
    **DATOS DE HOY:** {datos_hoy}

    **TU TAREA:**
    1. **Valida si el plan de mañana ({lo_que_toca_manana}) sigue teniendo sentido.** Basado en mis sensaciones de hoy, recomienda un cambio si es necesario. Si haces un cambio, explícalo.
    2. **Crea el plan detallado para mañana.** Mantén el formato original que ya funcionaba, con las secciones de Entrenamiento, Dieta y Consejo.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None

# --- 3. CÓDIGO PRINCIPAL DE LA APP ---
def main():
    st.set_page_config(page_title="AI.TRAIN-U", layout="wide")
    st.title("🤖 AI.TRAIN-U")
    create_usertable()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.image("https://mir-s3-cdn-cf.behance.net/project_modules/fs/218fc872735831.5bf1e45999c40.gif")
        st.sidebar.header("Login")
        # ... (código de login sin cambios) ...
        username_input = st.sidebar.text_input("Usuario")
        password_input = st.sidebar.text_input("Contraseña", type='password')
        if st.sidebar.button("Login"):
            hashed_pswd = make_hashes(password_input)
            result = login_user(username_input, hashed_pswd)
            if result:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username_input
                st.rerun()
            else:
                st.sidebar.error("Usuario o contraseña incorrecta")
        st.info("Por favor, introduce tus credenciales en la barra lateral para continuar.")
    
    else:
        # --- APLICACIÓN PRINCIPAL (SI EL LOGIN ES CORRECTO) ---
        username = st.session_state['username']
        
        st.sidebar.success(f"Conectado como: **{username}**")
        if st.sidebar.button("Logout"):
            del st.session_state['logged_in']
            del st.session_state['username']
            st.rerun()

        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        perfil_usuario = cargar_perfil(gspread_client, username)
        historial_df = cargar_historial(gspread_client, username)
        
        # --- (NUEVO) SECCIÓN 1: PANEL SEMANAL ---
        st.header("🗓️ Tu Hoja de Ruta Semanal")
        plan_semana_actual = cargar_plan_semana(gspread_client, username)
        
        if not plan_semana_actual:
            st.info("Aún no tienes un plan para esta semana.")
            if st.button("💪 ¡Generar mi plan para la semana!"):
                with st.spinner("Generando tu plan estratégico..."):
                    plan_semanal_generado = generar_plan_semanal(perfil_usuario)
                    if plan_semanal_generado:
                        guardar_plan_semanal_nuevo(gspread_client, username, plan_semanal_generado)
                        st.success("¡Plan semanal generado! Recargando...")
                        st.rerun()
        else:
            st.subheader("Plan Actualizado de la Semana")
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            plan_data = {
                "Día": dias,
                "Plan": [plan_semana_actual.get(f"{dia}_Plan", "-") for dia in dias],
                "Estado": [plan_semana_actual.get(f"{dia}_Estado", "-") for dia in dias]
            }
            st.table(pd.DataFrame(plan_data).set_index("Día"))
            with st.expander("Ver Plan Original de la Semana"):
                st.text(plan_semana_actual.get("Plan_Original_Completo", "No disponible."))

        st.divider()

        if "Error" in perfil_usuario:
            st.error(perfil_usuario["Error"])
        else:
            with st.expander("Ver mi Perfil y Historial Completo"):
                st.subheader("Mi Perfil")
                st.write(perfil_usuario)
                st.subheader("Historial de Registros")
                st.dataframe(historial_df)
            
            st.header(f"✍️ Registro del Día")
            with st.form("registro_diario_form"):
                entreno = st.text_area("¿Qué entrenamiento has hecho hoy?")
                sensaciones = st.text_area("¿Cómo te sientes?")
                calorias = st.number_input("Calorías consumidas (aprox.)", min_value=0, step=100)
                proteinas = st.number_input("Proteínas consumidas (g)", min_value=0, step=10)
                descanso = st.slider("¿Cuántas horas has dormido?", 0.0, 12.0, 8.0, 0.5)
                submitted = st.form_submit_button("✅ Generar plan para mañana")

            if submitted:
                if not plan_semana_actual:
                    st.error("Primero debes generar un plan semanal antes de registrar tu día.")
                else:
                    with st.spinner("Analizando tu día y preparando el plan de mañana..."):
                        datos_de_hoy = {"entreno": entreno, "sensaciones": sensaciones, "calorias": calorias, "proteinas": proteinas, "descanso": descanso}
                        historial_texto = historial_df.tail(3).to_string()
                        
                        plan_generado = generar_plan_diario(perfil_usuario, historial_texto, datos_de_hoy, plan_semana_actual)

                        if plan_generado:
                            nueva_fila_datos = [datetime.now().strftime('%Y-%m-%d'), calorias, proteinas, entreno, sensaciones, descanso, plan_generado]
                            guardar_registro(gspread_client, username, nueva_fila_datos)
                            
                            dia_hoy_nombre = dias[(datetime.today().weekday())]
                            plan_hoy_previsto = plan_semana_actual.get(f"{dia_hoy_nombre}_Plan", "")
                            if entreno.lower() in plan_hoy_previsto.lower() or plan_hoy_previsto.lower() in entreno.lower():
                                estado_hoy = "✅ Realizado"
                            else:
                                estado_hoy = f"🔄 Modificado"
                            actualizar_estado_semanal(gspread_client, username, dia_hoy_nombre, estado_hoy)
                            
                            st.success("¡Plan para mañana generado y semana actualizada!")
                            st.markdown(plan_generado)
                            st.info("Actualizando la tabla del plan semanal en 3 segundos...")
                            time.sleep(3) # Damos tiempo al usuario para leer el mensaje
                            st.rerun() # Forzamos la recarga de la página


if __name__ == '__main__':
    main()
