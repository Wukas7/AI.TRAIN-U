# --- 1. IMPORTS Y CONFIGURACIÓN INICIAL ---
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime
import streamlit_authenticator as stauth

# Configura el título y layout de la página.
st.set_page_config(page_title="AI.TRAIN-U", layout="wide")


# --- 2. CONFIGURACIÓN DEL AUTENTICADOR (MODO DE PRUEBA HARDCODEADO) ---

# Genera un hash nuevo para "1234" en Colab y pégalo aquí.
# Esto es para estar 100% seguros de que la contraseña y el hash coinciden.
# Ejemplo de hash (USA EL TUYO PROPIO): "$2b$12$OhGHGt/CKTBtTydK2XQB/.he/XGKyn1valvPuM/y.PasRRFRMHvPy"

test_credentials = {
    "usernames": {
        "testuser": {
            "name": "Usuario de Prueba",
            "password": "$2b$12$rfLliKMoBK9dvF74DSKLYugQBhnPTOOmSX7JUUq6sU1lHYUGGpDJW" 
        }
    }
}

authenticator = stauth.Authenticate(
    test_credentials,
    "test_cookie_name", # Nombre de cookie de prueba
    "test_cookie_key_secreta", # Clave de cookie de prueba
    30 # Días de expiración
)


# --- 3. LÓGICA DE LOGIN Y EJECUCIÓN DE LA APP ---
if authenticator.login(location='main'):
    # ---- SI LLEGAS AQUÍ, EL LOGIN HA FUNCIONADO ----
    
    # 3.1. Acceder a los datos del usuario y mostrar bienvenida/logout
    name = authenticator.credentials['usernames'][authenticator.username]['name']
    username = authenticator.username
    
    authenticator.logout(location='main')
    
    st.title(f"¡Login Correcto! - Planificador de {name}")
    st.write(f"Conectado como: **{username}**")
    st.success("¡El sistema de autenticación funciona! Ahora procedemos a cargar el resto de la app.")
    st.divider()

    # 3.2. Configuración de Gemini y Google Sheets (ahora sí leemos de Secrets)
    try:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=GEMINI_API_KEY)

        google_creds_dict = st.secrets["gcp_service_account"]
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(google_creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open("AI.TRAIN-U")
        sheet_perfil = spreadsheet.worksheet("Perfil")
        sheet_registro = spreadsheet.worksheet("Registro_Diario")

        # A partir de aquí, el resto de tu código debería funcionar
        # Pega aquí tus funciones y la interfaz del formulario
        
        # Ejemplo de cómo continuaría:
        # def cargar_perfil(): ...
        # ...
        # with st.form(...): ...
        # ...

    except Exception as e:
        st.error("El login ha funcionado, pero ha habido un error al cargar las claves de Google/Gemini desde los 'Secrets'.")
        st.error(f"Error detallado: {e}")
