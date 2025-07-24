import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime

# --- 1. FUNCIONES DE SEGURIDAD Y BASE DE DATOS DE LOGIN ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Usamos check_same_thread=False, importante para que SQLite funcione con Streamlit
conn = sqlite3.connect('data.db', check_same_thread=False) 
c = conn.cursor()

def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')

def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    return c.fetchall()

# --- 2. FUNCIONES DE LA APLICACIÓN (GOOGLE SHEETS & GEMINI) ---
# Estas funciones ahora usan el 'username' como "llave" para filtrar los datos.

def cargar_perfil(client, username):
    """Carga el perfil del usuario específico desde Google Sheets."""
    try:
        spreadsheet = client.open("AI.TRAIN-U")
        sheet_perfil = spreadsheet.worksheet("Perfil")
        data = sheet_perfil.get_all_records()
        df = pd.DataFrame(data)
        
        # ¡LA MAGIA! Filtramos por el UserID que coincide con el username logueado
        df_usuario = df[df['UserID'] == username]
        
        if df_usuario.empty:
            return {"Error": "No se encontró un perfil para este usuario en la hoja 'Perfil'."}
        
        # Convertimos las filas filtradas en un diccionario de perfil
        perfil_dict = {row['Variable']: row['Valor'] for index, row in df_usuario.iterrows()}
        return perfil_dict
    except gspread.exceptions.WorksheetNotFound:
        return {"Error": "No se encontró la pestaña 'Perfil' en el Google Sheet."}
    except Exception as e:
        return {"Error": f"Ocurrió un error al cargar el perfil: {e}"}


def cargar_historial(client, username):
    """Carga el historial del usuario específico."""
    try:
        spreadsheet = client.open("AI.TRAIN-U")
        sheet_registro = spreadsheet.worksheet("Registro_Diario")
        data = sheet_registro.get_all_records()
        df = pd.DataFrame(data)
        
        # ¡LA MAGIA! Filtramos por el UserID
        df_usuario = df[df['UserID'] == username]
        return df_usuario # Devolvemos el DataFrame ya filtrado
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame() # Devolvemos un DataFrame vacío si no encuentra la hoja
    except Exception:
        return pd.DataFrame()


def guardar_registro(client, username, nueva_fila_datos):
    """Guarda una nueva entrada en el registro para el usuario específico."""
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_registro = spreadsheet.worksheet("Registro_Diario")
    # ¡LA MAGIA! Añadimos el username como el primer elemento de la fila a guardar
    fila_completa = [username] + nueva_fila_datos
    sheet_registro.append_row(fila_completa)


def generar_plan(perfil, historial_str, datos_hoy):
    """Llama a la API de Gemini para generar el plan, con el prompt original."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un entrenador personal y nutricionista experto en IA. Tu objetivo es crear un plan de entrenamiento y dieta para mañana basado en mi perfil, mi historial y mis datos de hoy.

    **MI PERFIL:**
    - Objetivo: {perfil.get('Objetivo', 'No especificado')}
    - Edad: {perfil.get('Edad', 'No especificado')}
    - Peso (kg): {perfil.get('Peso (kg)', 'No especificado')} kg
    - Altura (cm): {perfil.get('Altura (cm)', 'No especificado')} cm
    - Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
    - Preferencias Comida: {perfil.get('Preferencias Comida', 'Ninguna')}

    **MI HISTORIAL RECIENTE (últimos días):**
    {historial_str}

    **DATOS DE HOY ({datetime.now().strftime('%Y-%m-%d')}):**
    - Calorías consumidas: {datos_hoy['calorias']} kcal
    - Proteínas consumidas: {datos_hoy['proteinas']} g
    - Entrenamiento realizado: {datos_hoy['entreno']}
    - Sensaciones (dolor, energía, motivación, etc.): {datos_hoy['sensaciones']}
    - Horas de descanso/sueño: {datos_hoy['descanso']} horas

    **TU TAREA:**
    Basado en TODA esta información, genera un plan claro y conciso para MAÑANA. El plan debe ser realista, adaptarse a mis sensaciones y ayudarme a progresar hacia mi objetivo.
    Responde en formato Markdown con las siguientes secciones:
    
    ### 🏋️ Plan de Entrenamiento para Mañana
    - Describe el tipo de entrenamiento (fuerza, cardio, descanso activo, etc.).
    - Lista los ejercicios con series y repeticiones. Sé específico.
    - Si hoy reporté dolor, adapta el entreno para no forzar esa zona.

    ### 🥗 Plan de Dieta para Mañana
    - Sugiere un objetivo de calorías y macronutrientes (proteínas, grasas, carbohidratos).
    - Da ejemplos de 3-4 comidas (desayuno, almuerzo, cena, snack) que cumplan con el objetivo y mis preferencias.

    ### 💡 Consejo del Día
    - Dame un consejo breve sobre motivación, técnica, recuperación o nutrición.

    Sé motivador pero realista. ¡Vamos a por ello!
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA: {e}")
        return None


# --- 3. CÓDIGO PRINCIPAL DE LA APP ---
def main():
    st.set_page_config(page_title="AI.TRAIN-U", layout="wide")
    st.title("🤖 AI.TRAIN-U")
    create_usertable()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        # PANTALLA DE LOGIN
        st.image("https://www.behance.net/gallery/72735831/GYM-Workout/modules/423539339")
        st.sidebar.header("Login")
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

        # --- Conexión a servicios de Google ---
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        # --- Cargar datos específicos del usuario ---
        perfil_usuario = cargar_perfil(gspread_client, username)
        historial_df = cargar_historial(gspread_client, username)
        
        # --- Comprobar si el perfil se cargó correctamente ---
        if "Error" in perfil_usuario:
            st.error(perfil_usuario["Error"])
        else:
            # --- INTERFAZ ORIGINAL (EXPANDER Y FORMULARIO) ---
            with st.expander("Ver mi Perfil y Historial"):
                st.subheader("Mi Perfil")
                st.write(perfil_usuario)
                st.subheader("Historial de Registros")
                st.dataframe(historial_df.tail(7))
            
            st.header(f"Registro del día")
            
            with st.form("registro_diario_form"):
                calorias = st.number_input("Calorías consumidas hoy (aprox.)", min_value=0, step=100)
                proteinas = st.number_input("Proteínas consumidas hoy (g)", min_value=0, step=10)
                entreno = st.text_area("¿Qué entrenamiento has hecho hoy? (Ej: Pecho y tríceps, 3 series de press banca...)")
                sensaciones = st.text_area("¿Cómo te sientes? (energía, dolor, motivación, etc.)")
                descanso = st.slider("¿Cuántas horas has dormido?", 0, 12, 8)
                submitted = st.form_submit_button("✅ Generar mi plan para mañana")

            if submitted:
                with st.spinner("Tu entrenador IA está pensando... 🧠"):
                    datos_de_hoy = {
                        "calorias": calorias, "proteinas": proteinas, "entreno": entreno,
                        "sensaciones": sensaciones, "descanso": descanso
                    }
                    historial_texto = historial_df.tail(5).to_string()
                    plan_generado = generar_plan(perfil_usuario, historial_texto, datos_de_hoy)

                    if plan_generado:
                        # Preparamos la nueva fila SIN el UserID, la función se encarga de añadirlo
                        nueva_fila_datos = [
                            datetime.now().strftime('%Y-%m-%d'), calorias, proteinas, entreno,
                            sensaciones, descanso, plan_generado
                        ]
                        guardar_registro(gspread_client, username, nueva_fila_datos)
                        
                        st.success("¡Plan generado con éxito!")
                        st.markdown(plan_generado)

if __name__ == '__main__':
    main()
