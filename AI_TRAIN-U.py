import streamlit as st
import sqlite3
import hashlib
import pandas as pd # Lo dejamos para futuras visualizaciones

# --- 1. FUNCIONES DE SEGURIDAD Y BASE DE DATOS ---

# Función para hashear contraseñas
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Función para comprobar el hash
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Conexión a la base de datos (creará el archivo data.db si no existe)
conn = sqlite3.connect('data.db')
c = conn.cursor()

# Función para crear la tabla de usuarios
def create_usertable():
    c.execute('CREATE TABLE IF NOT EXISTS userstable(username TEXT, password TEXT)')

# Función para añadir un usuario (la usaremos nosotros para añadir usuarios manualmente)
def add_userdata(username, password):
    c.execute('INSERT INTO userstable(username,password) VALUES (?,?)', (username, password))
    conn.commit()

# Función para validar el login
def login_user(username, password):
    c.execute('SELECT * FROM userstable WHERE username =? AND password = ?', (username, password))
    data = c.fetchall()
    return data

# --- 2. CÓDIGO PRINCIPAL DE LA APP ---

def main():
    st.set_page_config(page_title="AI.TRAIN-U", layout="wide")
    st.title("AI.TRAIN-U")

    # Creamos la tabla de usuarios al iniciar la app
    create_usertable()

    # --- PANTALLA DE LOGIN ---
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Usuario")
    password = st.sidebar.text_input("Contraseña", type='password')

    if st.sidebar.button("Login"):
        hashed_pswd = make_hashes(password)
        result = login_user(username, hashed_pswd)

        if result:
            # Si el login es correcto, guardamos el estado en st.session_state
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.rerun() # Volvemos a ejecutar el script para mostrar la app principal
        else:
            st.sidebar.error("Usuario o contraseña incorrecta")

    # --- LÓGICA DE LA APLICACIÓN PRINCIPAL ---
    # Comprobamos si el usuario está logueado
    if 'logged_in' in st.session_state and st.session_state['logged_in']:
        
        # Ocultamos los campos de login y mostramos la bienvenida y el logout
        st.sidebar.empty() # Limpiamos la barra lateral del login
        st.sidebar.success(f"Conectado como: **{st.session_state['username']}**")
        if st.sidebar.button("Logout"):
            del st.session_state['logged_in']
            del st.session_state['username']
            st.rerun()

        # #######################################################################
        # ##  AQUÍ DENTRO IRÁ EL RESTO DE TU APLICACIÓN (GOOGLE, GEMINI, ETC.) ##
        # #######################################################################
        
        st.header("¡Bienvenido a tu planificador!")
        st.write("Esta es la página principal de la aplicación.")
        # Aquí añadirías el código de tu expander, formulario, etc.

    else:
        st.info("Por favor, introduce tus credenciales en la barra lateral para continuar.")

# --- SCRIPT PARA AÑADIR USUARIOS (SOLO PARA TI, EL ADMINISTRADOR) ---
# Este script solo se ejecuta si lo llamas directamente desde la terminal.
# No se ejecutará en la app de Streamlit.
if __name__ == '__main__':
    # Para añadir un nuevo usuario, descomenta las siguientes líneas,
    # pon el usuario y contraseña que quieras, y ejecuta: python tu_archivo.py
    # create_usertable()
    # add_userdata("testuser", make_hashes("1234"))
    # print("Usuario de prueba añadido.")
    
    # La función main() se ejecuta cuando abres la app en Streamlit
    main()
