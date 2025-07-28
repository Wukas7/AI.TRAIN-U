import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from datetime import datetime
import time


# --- IMPORTAMOS NUESTROS MÓDULOS ---
from modules.auth import create_usertable, login_user, make_hashes
from modules.gsheets import (
    cargar_perfil, cargar_historial, cargar_plan_semana,
    guardar_registro, guardar_plan_semanal_nuevo, actualizar_plan_completo
)
from modules.aibrain import generar_plan_semanal, generar_plan_diario

# --- 3. CÓDIGO PRINCIPAL DE LA APP ---
def main():
    st.set_page_config(page_title="AI.TRAIN-U", layout="wide")
    st.title("🤖 AI.TRAIN-U")
    create_usertable()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        # --- PANTALLA DE LOGIN ---
        st.image("https://mir-s3-cdn-cf.behance.net/project_modules/fs/218fc872735831.5bf1e45999c40.gif")
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
            
        if 'plan_recien_generado' in st.session_state:
            st.header("🚀 Tu Plan para Mañana")
            st.markdown(st.session_state['plan_recien_generado'])
            st.divider()
        # Limpiamos la variable para que no aparezca en futuras recargas
            del st.session_state['plan_recien_generado']

        # (CORREGIDO) Conexión a servicios de Google en el lugar correcto
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        perfil_usuario = cargar_perfil(gspread_client, username)
        historial_df = cargar_historial(gspread_client, username)
        plan_semana_actual = cargar_plan_semana(gspread_client, username)

        if 'plan_recien_generado' in st.session_state:
            st.header("🚀 Tu Plan Detallado para el Primer Día")
            st.markdown(st.session_state['plan_recien_generado'])
            del st.session_state['plan_recien_generado']

        st.header("🗓️ Tu Hoja de Ruta Semanal")
        if not plan_semana_actual:
            st.info("Aún no tienes un plan para esta semana.")
            if st.button("💪 ¡Generar mi plan para la semana!"):
                with st.spinner("Generando tu plan estratégico..."):
                    historial_mes_str = historial_df.tail(30).to_string()
                    plan_semanal_generado_str = generar_plan_semanal(perfil_usuario, historial_mes_str)

                    if plan_semanal_generado_str:
                        guardar_plan_semanal_nuevo(gspread_client, username, plan_semanal_generado_str)
                        st.success("¡Estructura semanal guardada! Generando plan para el Lunes...")
                        time.sleep(1)

                        plan_recien_creado = cargar_plan_semana(gspread_client, username)
                        if plan_recien_creado:
                            datos_ficticios_domingo = {"entreno": "Descanso", "sensaciones": "Listo para empezar"}
                            plan_detallado_lunes = generar_plan_diario(perfil_usuario, historial_mes_str, datos_ficticios_domingo, plan_recien_creado)
                            if plan_detallado_lunes:
                                st.session_state['plan_recien_generado'] = plan_detallado_lunes
                                plan_del_lunes = plan_recien_creado.get("Lunes_Plan", "No definido")
                                actualizar_plan_completo(gspread_client, username, "Lunes", plan_del_lunes, "✅ Planificado")
                                st.success("¡Planes generados! Recargando...")
                                time.sleep(2)
                                st.rerun()
        else:
            st.subheader("Plan Actualizado de la Semana")
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            plan_data = {"Día": dias, "Plan": [plan_semana_actual.get(f"{dia}_Plan", "-") for dia in dias], "Estado": [plan_semana_actual.get(f"{dia}_Estado", "-") for dia in dias]}
            st.table(pd.DataFrame(plan_data).set_index("Día"))
            with st.expander("Ver Plan Original de la Semana"):
                st.text(plan_semana_actual.get("Plan_Original_Completo", "No disponible."))
       
    else:
        st.warning("Aún no has generado ningún plan.")
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
 
        if st.button("👁️ Mostrar mi plan para mañana"):
                    if not historial_df.empty:
                        ultimo_plan = historial_df.iloc[-1]['Plan_Generado']
                        st.markdown("---")
                        st.subheader("📋 Tu Plan Más Reciente")
                        st.markdown(ultimo_plan)
            if submitted:
                if not plan_semana_actual:
                    st.error("Primero debes generar un plan semanal.")
                else:
                    with st.spinner("Analizando tu día y preparando el plan de mañana..."):
                        datos_de_hoy = {"entreno": entreno, "sensaciones": sensaciones, "calorias": calorias, "proteinas": proteinas, "descanso": descanso}
                        historial_texto = historial_df.tail(3).to_string()
                        plan_generado = generar_plan_diario(perfil_usuario, historial_texto, datos_de_hoy, plan_semana_actual)
                        if plan_generado:
                            partes_plan = plan_generado.split("### 🔄 Sugerencia de Re-planificación Semanal")
                            plan_diario_detallado = partes_plan[0].strip()
                            nueva_fila_datos = [datetime.now().strftime('%Y-%m-%d'), calorias, proteinas, entreno, sensaciones, descanso, plan_diario_detallado]
                            guardar_registro(gspread_client, username, nueva_fila_datos)
                            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                            dia_hoy_nombre = dias_semana[(datetime.today().weekday())]
                            actualizar_plan_completo(gspread_client, username, dia_hoy_nombre, entreno, "✅ Realizado")
                            st.session_state['plan_recien_generado'] = plan_diario_detallado
                            if len(partes_plan) > 1:
                                st.info("¡La IA ha re-planificado el resto de tu semana!")
                            st.success("¡Plan para mañana generado y semana actualizada!")
                            st.markdown(plan_diario_detallado)
                            st.info("Actualizando la tabla...")
                            time.sleep(3)
                            st.rerun()

if __name__ == '__main__':
    main()
