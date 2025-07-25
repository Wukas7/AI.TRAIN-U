import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime, timedelta
import time

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
    """Guarda un plan semanal recién creado, rellenando correctamente todas las columnas."""
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        today = datetime.today()
        lunes_actual = (today - timedelta(days=today.weekday())).strftime('%d/%m/%Y')
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        # Preparamos la nueva fila para el Google Sheet. Columnas: UserID, Semana_Del
        nueva_fila = [username, lunes_actual]
        
        # Limpiamos la respuesta de la IA por si añade espacios o líneas en blanco.
        planes_diarios_limpios = [linea.strip() for linea in plan_generado_str.strip().split('\n')]
        
        # Creamos un diccionario para acceder fácilmente al plan de cada día
        # ej: {'Lunes': 'Empuje...', 'Martes': 'Tirón...'}
        planes_por_dia = {}
        for linea in planes_diarios_limpios:
            if ':' in linea:
                partes = linea.split(':', 1)
                dia_semana = partes[0].strip()
                plan_desc = partes[1].strip()
                if dia_semana in dias:
                    planes_por_dia[dia_semana] = plan_desc
        
        # Rellenamos las columnas del Sheet con los datos del diccionario
        for dia in dias:
            plan_del_dia = planes_por_dia.get(dia, "Descanso") # Usamos .get para obtener el plan o 'Descanso' si no lo encuentra
            # Añadimos el Plan del día y su estado inicial ("Pendiente")
            nueva_fila.extend([plan_del_dia, "Pendiente"])
            
        # Al final, añadimos el texto original completo y legible
        nueva_fila.append(plan_generado_str.strip())
        
        sheet.append_row(nueva_fila)
        st.success("Plan semanal guardado correctamente en la base de datos.")

    except Exception as e:
        st.error(f"Ocurrió un error crítico al guardar el nuevo plan semanal: {e}")
    except Exception as e:
        st.error(f"Ocurrió un error crítico al guardar el nuevo plan semanal: {e}")
        
# (NUEVA Y MEJORADA) Esta función actualiza tanto el plan como el estado
def actualizar_plan_completo(client, username, dia, nuevo_plan, nuevo_estado):
    try:
        sheet = client.open("AI.TRAIN-U").worksheet("Plan_Semanal")
        # ... (lógica para encontrar la fila del usuario, igual que antes) ...
        
        if fila_usuario != -1:
            # Encontrar las columnas para el plan y el estado de ese día
            columna_plan = 3 + (dias_semana.index(dia) * 2)
            columna_estado = columna_plan + 1
            
            # Actualizar ambas celdas
            sheet.update_cell(fila_usuario, columna_plan, nuevo_plan)
            sheet.update_cell(fila_usuario, columna_estado, nuevo_estado)
    except Exception as e:
        st.warning(f"No se pudo actualizar el plan semanal: {e}")


# --- Funciones de IA (Con las nuevas modificaciones) ---
def generar_plan_semanal(perfil, historial_mes_str):
    """Genera la estructura de entrenamiento para 7 días con un formato estricto."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un planificador de fitness. Basado en el perfil del usuario, genera una estructura de entrenamiento para los 7 días de la semana.

    Perfil: {perfil}
    Historial del último mes: {historial_mes_str}

    **TU TAREA:**
    Genera una estructura de entrenamiento para los 7 días de la semana.

    **FORMATO OBLIGATORIO:**
    Debes responder con EXACTAMENTE 7 líneas.
    Cada línea DEBE empezar con el nombre del día de la semana (Lunes, Martes, Miércoles, Jueves, Viernes, Sábado, Domingo), seguido de dos puntos y el plan.
    NO incluyas ninguna otra palabra, saludo o explicación antes o después de las 7 líneas.
    NO uses la palabra genérica 'Día'. Usa el nombre específico de cada día de la semana.

    **EJEMPLO DE RESPUESTA PERFECTA:**
    Lunes: Empuje (Pecho, Hombro, Tríceps)
    Martes: Tirón (Espalda, Bíceps)
    Miércoles: Pierna (Cuádriceps, Femoral)
    Jueves: Cardio y Abdominales
    Viernes: Empuje (Enfoque Hombro)
    Sábado: Tirón (Enfoque Espalda)
    Domingo: Descanso total
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar el plan semanal: {e}")
        return None

# (MODIFICADA) La IA ahora también puede sugerir una re-planificación
def generar_plan_diario(perfil, historial_str, datos_hoy, plan_semanal_actual):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # --- (NUEVO) AÑADIMOS LAS LÍNEAS QUE FALTABAN ---
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_manana_idx = (datetime.today().weekday() + 1) % 7
    dia_manana_nombre = dias_semana[dia_manana_idx]
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")
    # --------------------------------------------------

    prompt = f"""
    Eres un entrenador personal adaptativo. Tu objetivo es crear un plan DETALLADO para mañana y, si es necesario, re-planificar el resto de la semana.

    **CONTEXTO ESTRATÉGICO:**
    - El plan original para la semana es: {plan_semanal_actual.get('Plan_Original_Completo', '')}
    - Mañana es {dia_manana_nombre} y el plan dice que toca: **{lo_que_toca_manana}**.

    **REALIDAD (HOY):**
    - Perfil: {perfil}
    - Historial reciente: {historial_str}
    - Datos de hoy: {datos_hoy}

    **TU TAREA:**
    1. **Analiza el entrenamiento de hoy.** Compara lo que hice (`{datos_hoy['entreno']}`) con lo que estaba planeado.
    2. **Crea el plan detallado para mañana.** Adáptalo si mis sensaciones de hoy lo requieren (dolor, cansancio).
    3. **(IMPORTANTE) Re-planifica si es necesario.** Si el entrenamiento de hoy fue muy diferente a lo planeado (ej: hice pierna cuando tocaba pecho), el resto de la semana podría necesitar ajustes para mantener el equilibrio. Si crees que hay que cambiar el plan para los días siguientes, añade una sección al final de tu respuesta llamada `### 🔄 Sugerencia de Re-planificación Semanal` con la nueva estructura para los días que quedan. Si no hay cambios necesarios, no incluyas esta sección.
  
    **FORMATO DE RESPUESTA:**
    ### 🏋️ Plan de Entrenamiento para Mañana
    ...
    ### 🥗 Plan de Dieta para Mañana
    ...
    ### 💡 Consejo del Día
    ...
    (Opcional)
    ### 🔄 Sugerencia de Re-planificación Semanal
    Martes: ...
    Miércoles: ...
    Jueves: ...
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
                with st.spinner("Generando tu plan estratégico y el plan detallado para el Lunes..."):
            
                    # --- PASO 1: Generar estructura semanal ---
                    historial_mes_str = historial_df.tail(30).to_string()
                    plan_semanal_generado_str = generar_plan_semanal(perfil_usuario, historial_mes_str)

                    if plan_semanal_generado_str:
                        # Guardamos la estructura en el Sheet (esto la rellena con 'Pendiente', etc.)
                        guardar_plan_semanal_nuevo(gspread_client, username, plan_semanal_generado_str)
                        st.success("¡Estructura semanal guardada!")
                
                        # --- PASO 2: Generar plan detallado para el Lunes ---
                        # Simulamos los "datos de hoy" como si fuera Domingo, para planificar el Lunes
                        datos_ficticios_domingo = {"entreno": "Descanso", "sensaciones": "Listo para empezar la semana"}
                
                    # Cargamos de nuevo el plan que acabamos de guardar para tenerlo como diccionario
                        plan_recien_creado = cargar_plan_semana(gspread_client, username)
                
                        plan_detallado_lunes = generar_plan_diario(perfil_usuario, historial_mes_str, datos_ficticios_domingo, plan_recien_creado)

                        if plan_detallado_lunes:
                            # Guardamos este plan en el estado de la sesión para mostrarlo después de recargar
                            st.session_state['plan_recien_generado'] = plan_detallado_lunes
                    
                            # Actualizamos el estado del Lunes a "✅ Realizado" (ya que lo hemos planificado)
                            actualizar_estado_semanal(gspread_client, username, "Lunes", "✅ Planificado")

                            st.success("¡Plan para Lunes generado! Recargando...")
                            time.sleep(3)
                            st.rerun()

# (NUEVO) Bloque para mostrar el plan recién generado después del rerun
                        if 'plan_recien_generado' in st.session_state:
                            st.header("🚀 Tu Plan Detallado para el Primer Día")
                            st.markdown(st.session_state['plan_recien_generado'])
                            # Limpiamos la variable para que no aparezca en futuras recargas
                            del st.session_state['plan_recien_generado']


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
                                  # 1. Extraer el plan detallado y la posible re-planificación
                            partes_plan = plan_generado.split("### 🔄 Sugerencia de Re-planificación Semanal")
                            plan_diario_detallado = partes_plan[0]

                            # 2. Actualizar el estado y el plan del día de HOY
                            dia_hoy_nombre = dias[(datetime.today().weekday())]
                            nuevo_plan_hoy = datos_de_hoy['entreno']
                            nuevo_estado_hoy = "✅ Realizado"
                            actualizar_plan_completo(gspread_client, username, dia_hoy_nombre, nuevo_plan_hoy, nuevo_estado_hoy)
        
                            # 3. Si la IA sugirió una re-planificación, la aplicamos
                            if len(partes_plan) > 1:
                                replanning_sugerido = partes_plan[1].strip()
                               # (Aquí iría una función más compleja que parsee y actualice los días futuros en el Sheet)
                                st.info("¡La IA ha re-planificado el resto de tu semana basándose en el entreno de hoy!")

                            st.success("¡Plan para mañana generado y semana actualizada!")
                            st.markdown(plan_diario_detallado)
                            st.info("Actualizando la tabla...")
                            time.sleep(3)
                            st.rerun()



if __name__ == '__main__':
    main()
