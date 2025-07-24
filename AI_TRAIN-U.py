import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime

# --- 1. FUNCIONES DE SEGURIDAD Y BASE DE DATOS DE LOGIN ---
# ... (las mismas funciones: make_hashes, check_hashes, create_usertable, add_userdata, login_user) ...
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()
conn = sqlite3.connect('data.db', check_same_thread=False) # check_same_thread=False es importante para Streamlit
c = conn.cursor()
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')
def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    return c.fetchall()

# --- 2. FUNCIONES DE LA APLICACIÓN (GOOGLE SHEETS) ---
# Estas funciones ahora usan el 'username' para filtrar los datos
def cargar_perfil(client, username):
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_perfil = spreadsheet.worksheet("Perfil")
    data = sheet_perfil.get_all_records()
    df = pd.DataFrame(data)
    
    # ¡LA MAGIA! Filtramos por el UserID que coincide con el username logueado
    df_usuario = df[df['UserID'] == username]
    
    if df_usuario.empty:
        return {"Error": "No se encontró perfil para este usuario."}
    
    perfil_dict = {row['Variable']: row['Valor'] for index, row in df_usuario.iterrows()}
    return perfil_dict

def cargar_historial(client, username):
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_registro = spreadsheet.worksheet("Registro_Diario")
    data = sheet_registro.get_all_records()
    df = pd.DataFrame(data)
    
    # ¡LA MAGIA! Filtramos por el UserID
    df_usuario = df[df['UserID'] == username]
    return df_usuario # Devolvemos el DataFrame filtrado

def guardar_registro(client, username, nueva_fila_datos):
    spreadsheet = client.open("AI.TRAIN-U")
    sheet_registro = spreadsheet.worksheet("Registro_Diario")
    # ¡LA MAGIA! Añadimos el username como el primer elemento de la fila
    fila_completa = [username] + nueva_fila_datos
    sheet_registro.append_row(fila_completa)
    
# ... (tu función generar_plan no necesita cambios) ...
def generar_plan(perfil, historial_str, datos_hoy):
    """Llama a la API de Gemini para generar el plan."""
    # TODO ESTE BLOQUE DEBE ESTAR INDENTADO
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un entrenador personal y nutricionista experto en IA. Tu objetivo es crear un plan de entrenamiento y dieta para mañana basado en mi perfil, mi historial y mis datos de hoy.

    **MI PERFIL:**
    - Objetivo: {perfil.get('Objetivo', 'No especificado')}
    - Edad: {perfil.get('Edad', 'No especificado')}
    # ... (el resto de tu prompt) ...
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
    st.title("AI.TRAIN-U")
    create_usertable()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        # PANTALLA DE LOGIN
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
        st.info("Por favor, introduce tus credenciales para continuar.")
    else:
        # --- APLICACIÓN PRINCIPAL (SI EL LOGIN ES CORRECTO) ---
        username = st.session_state['username']
        
        st.sidebar.success(f"Conectado como: **{username}**")
        if st.sidebar.button("Logout"):
            del st.session_state['logged_in']
            del st.session_state['username']
            st.rerun()

        # Conexión a servicios de Google (dentro del área logueada)
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        # Cargar datos y mostrar la interfaz
        perfil_usuario = cargar_perfil(gspread_client, username)
        historial_df = cargar_historial(gspread_client, username)

        st.header(f"Registro del día de {username}")
        # ... (Aquí va tu 'with st.expander' y 'with st.form') ...
        # ... (Tu lógica de 'if submitted') ...
        # La única diferencia es que la llamada a guardar_registro ahora incluye el username:
        # guardar_registro(gspread_client, username, nueva_fila)

if __name__ == '__main__':
    main()
