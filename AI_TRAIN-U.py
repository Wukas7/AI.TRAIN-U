import streamlit as st
import streamlit_authenticator as stauth

# --- 1. CONSTRUIR LA CONFIGURACIÓN DESDE LOS SECRETS ---
try:
    # Leemos cada lista por separado
    usernames = st.secrets['credentials']['usernames']
    names = st.secrets['credentials']['names']
    passwords = st.secrets['credentials']['passwords']

    # Creamos el diccionario de credenciales con la estructura correcta
    credentials = {
        "usernames": {
            username: {
                "name": name,
                "password": password
            }
            for username, name, password in zip(usernames, names, passwords)
        }
    }

    # Inicializamos el autenticador
    authenticator = stauth.Authenticate(
        credentials,
        "cookie_de_prueba",
        "clave_secreta_de_prueba",
        30
    )

except Exception as e:
    st.error("Ha ocurrido un error al configurar el autenticador.")
    st.error(f"Error detallado: {e}")
    st.stop()


# --- 2. RENDERIZAR EL WIDGET DE LOGIN ---
if authenticator.login(location='main'):
    st.write(f"¡Bienvenido, *{st.session_state['name']}*!")
    st.title("¡LOGIN CORRECTO!")
    authenticator.logout(location='main')
