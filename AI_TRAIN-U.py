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
    guardar_registro, guardar_plan_semana_nuevo, actualizar_plan_completo,
    cargar_historial_detallado, guardar_entreno_detallado, cargar_lista_ejercicios,
    actualizar_perfil_usuario, cargar_df_ejercicios
)
from modules.aibrain import generar_plan_semana, generar_plan_diario

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
            
        # (CORREGIDO) Conexión a servicios de Google en el lugar correcto
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        gspread_client = gspread.authorize(creds)
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

        perfil_usuario = cargar_perfil(gspread_client, username)
        historial_df = cargar_historial(gspread_client, username)
        plan_semana_actual = cargar_plan_semana(gspread_client, username)
        historial_detallado_df = cargar_historial_detallado(gspread_client, username)
        lista_ejercicios = cargar_lista_ejercicios(gspread_client)
        df_ejercicios = cargar_df_ejercicios(gspread_client)
        
        # Lógica del Pop-up y Celebración de Racha
        racha_actual = int(perfil_usuario.get("Racha_Actual", 0))
        if 'celebrar_racha' in st.session_state:
            racha_celebrada = st.session_state['celebrar_racha']
            st.success(f"🎉 ¡Felicidades! ¡Has alcanzado una racha de {racha_celebrada} días! ¡Sigue así! 🎉")
            st.balloons()
            del st.session_state['celebrar_racha']
        elif racha_actual > 0:
            st.toast(f"¡Llevas {racha_actual} día(s) de racha! ¡A por más!", icon="🔥")
        
        if 'plan_recien_generado' in st.session_state:
            st.header("🚀 Tu Plan para Mañana")
            st.markdown(st.session_state['plan_recien_generado'])
            st.divider()
        # Limpiamos la variable para que no aparezca en futuras recargas
            del st.session_state['plan_recien_generado']


        st.header("🗓️ Tu Hoja de Ruta Semanal")
        if not plan_semana_actual:
            st.info("Aún no tienes un plan para esta semana.")
            if st.button("💪 ¡Generar mi plan para la semana!"):
                with st.spinner("Generando tu plan estratégico para la semana..."):
                    historial_mes_str = historial_df.tail(30).to_string()
                    plan_semana_generado_str = generar_plan_semana(perfil_usuario, historial_mes_str)

                    if plan_semana_generado_str:
                        guardar_plan_semana_nuevo(gspread_client, username, plan_semana_generado_str)
                        st.success("¡Plan semanal generado con éxito! Ahora ya puedes registrar tu primer día.")
                        cargar_plan_semana.clear()
                        time.sleep(3)
                        st.rerun()
        else:
            st.subheader("Plan Actualizado de la Semana")
            dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            plan_data = {"Día": dias, "Plan": [plan_semana_actual.get(f"{dia}_Plan", "-") for dia in dias], "Estado": [plan_semana_actual.get(f"{dia}_Estado", "-") for dia in dias]}
            st.table(pd.DataFrame(plan_data).set_index("Día"))
            with st.expander("Ver Plan Original de la Semana"):
                st.text(plan_semana_actual.get("Plan_Original_Completo", "No disponible."))
       

        if "Error" in perfil_usuario:
            st.error(perfil_usuario["Error"])           
        else:
            with st.expander("Ver mi Perfil y Historial Completo"):
                st.subheader("Mi Perfil")
                st.write(perfil_usuario)
                st.subheader("Historial de Registros")
                st.dataframe(historial_df)

            st.divider()
                    
            st.header(f"✍️ Registra tu Día")
            st.info("Registra tu día y, si es necesario, ajusta el plan de los días siguientes en la tabla. Cuando termines, pulsa el botón de abajo.")

            if 'plan_modificado' not in st.session_state:
                if plan_semana_actual:
                    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    plan_editable_data = {dia: plan_semana_actual.get(f"{dia}_Plan", "-") for dia in dias}
                    st.session_state.plan_modificado = pd.DataFrame([plan_editable_data])
                else:
                    st.session_state.plan_modificado = pd.DataFrame()

            if not st.session_state.plan_modificado.empty:
                st.subheader("Planificación Futura (Editable)")
                plan_modificado_df = st.data_editor(st.session_state.plan_modificado, key="editor_plan_semanal")
                st.session_state.plan_modificado = plan_modificado_df # Guardamos los cambios del usuario

            with st.form("registro_y_generacion_form"):
                st.subheader("Registro del Día Realizado")
                fecha_registro = st.date_input("¿Para qué día es este registro?", value=datetime.today(), max_value=datetime.today())
            
            usar_entreno_detallado = st.toggle("Añadir entrenamiento detallado", value=True)
                            
                if usar_entreno_detallado:
                    st.subheader("🏋️ Entrenamiento Detallado")
                    df_entreno_vacio = pd.DataFrame(
                        [{"Ejercicio": None, "Series": 4, "Repeticiones": None, "Peso_kg": None}]
                    )
                    entreno_registrado_df = st.data_editor(
                        df_entreno_vacio, num_rows="dynamic",
                        column_config={
                            "Ejercicio": st.column_config.SelectboxColumn("Ejercicio", options=lista_ejercicios, required=True),
                            "Series": st.column_config.NumberColumn("Nº series", min_value=1, step=1, required=True),
                            "Repeticiones": st.column_config.NumberColumn("Repeticiones", min_value=0, step=1, required=True),
                            "Peso_kg": st.column_config.NumberColumn("Peso (kg)", min_value=0.0, format="%.2f kg", required=True),
                        }
                    )
                    entreno_simple = st.text_area("Notas adicionales del entreno (opcional)")
                else:
                    st.subheader("🏃 Entrenamiento Simple")
                    entreno_simple = st.text_area("Describe tu entrenamiento (ej: 'Salí a correr 45 min a ritmo suave')")

                sensaciones = st.text_area("¿Cómo te sientes?")
                calorias = st.number_input("Calorías consumidas (aprox.)", min_value=0, step=100)
                proteinas = st.number_input("Proteínas consumidas (g)", min_value=0, step=10)
                descanso = st.slider("¿Cuántas horas has dormido?", 0.0, 12.0, 8.0, 0.5)
                
                submitted_final = st.form_submit_button("💾 Guardar Todo y Generar Plan de Mañana")

            if submitted_final:
                if not plan_semana_actual:
                    st.error("Primero debes generar un plan semanal.")
                else:
                    with st.spinner("Guardando tus datos y generando el nuevo plan..."):
                        resumen_entreno_hoy = ""
                        if usar_entreno_detallado:
                            resumen_tabla = "\n".join(
                                f"- {row['Ejercicio']}: {row['Serie']}x{row['Repeticiones']} @ {row['Peso_kg']}kg" 
                                for _, row in entreno_registrado_df.iterrows() if row['Ejercicio'] and pd.notna(row.get('Repeticiones'))
                            )
                            resumen_entreno_hoy = resumen_tabla + (f"\n\n**Notas:**\n{entreno_simple}" if entreno_simple else "")
                            fecha_guardado_str = fecha_registro.strftime('%Y-%m-%d')
                            guardar_entreno_detallado(gspread_client, username, fecha_guardado_str, entreno_registrado_df)
                        else:
                            resumen_entreno_hoy = entreno_simple
            
                    # Guardar el registro general
                    fecha_guardado = fecha_registro.strftime('%Y-%m-%d')
                    nueva_fila_datos = [fecha_guardado, calorias, proteinas, resumen_entreno_hoy, sensaciones, descanso, ""] # El plan se genera después
                    guardar_registro(gspread_client, username, nueva_fila_datos)
                    actualizar_fila_plan_semanal(gspread_client, username, st.session_state.plan_modificado)
                    plan_confirmado = cargar_plan_semana(gspread_client, username)
            
                    datos_de_hoy = {"entreno": resumen_entreno_hoy, "sensaciones": sensaciones, ...}
                    historial_detallado_texto = historial_detallado_df.tail(20).to_string()
            
                    # El prompt de la IA ahora es simple. Solo necesita saber qué toca mañana.
                    plan_generado = generar_plan_diario(perfil_usuario, historial_detallado_texto, datos_de_hoy, plan_confirmado, fecha_registro)

                    if plan_generado:
                                                 
                            # ------RACHA DE DIAS------------
                            racha_actual = int(perfil_usuario.get("Racha_Actual", 0))
                            ultimo_dia_str = perfil_usuario.get("Ultimo_Dia_Registrado", None)
                    

                            # Convertimos la fecha de hoy y la última fecha a objetos 'date' para poder compararlas
                            fecha_de_hoy_obj = fecha_registro

                            if ultimo_dia_str and ultimo_dia_str.strip() != "":
                                formatos_posibles = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'] # AAAA-MM-DD, DD/MM/AAAA, DD-MM-AAAA
                                ultimo_dia_obj = None
                                for formato in formatos_posibles:
                                    try:
                                        ultimo_dia_obj = datetime.strptime(ultimo_dia_str, formato).date()
                                        break # Si funciona, salimos del bucle
                                    except ValueError:
                                        continue

                                if ultimo_dia_obj:
                                    diferencia_dias = (fecha_de_hoy_obj - ultimo_dia_obj).days

                                    if diferencia_dias == 1:
                                        racha_actual += 1
                                    elif diferencia_dias > 1:
                                        racha_actual = 1
                                    # Si es 0 o menos, no hacemos nada con la racha
                            else:
                            # Es el primer registro válido
                                racha_actual = 1
        
                            # Guardamos los nuevos valores en el Google Sheet
                            actualizar_perfil_usuario(gspread_client, username, "Racha_Actual", racha_actual)
                            actualizar_perfil_usuario(gspread_client, username, "Ultimo_Dia_Registrado", fecha_de_hoy_obj.strftime('%Y-%m-%d'))

                            if racha_actual > 0 and racha_actual % 10 == 0:
                                st.session_state['celebrar_racha'] = racha_actual       
                            
                            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                            dia_a_actualizar = dias_semana[fecha_registro.weekday()]
                                
                            plan_previsto = plan_semana_actual.get(f"{dia_a_actualizar}_Plan", "")
                            
                            if resumen_entreno_hoy and (resumen_entreno_hoy.strip().lower() in plan_previsto.strip().lower() or plan_previsto.strip().lower() in resumen_entreno_hoy.strip().lower()):
                               nuevo_estado = "✅ Realizado"
                            else:
                                nuevo_estado = "🔄 Modificado"
                                    
                            actualizar_plan_completo(gspread_client, username, dia_a_actualizar, resumen_entreno_hoy, nuevo_estado)

                            if len(partes_plan) > 1:
                                st.info("¡La IA ha re-planificado el resto de tu semana!")
                            st.success("¡Plan generado y semana actualizada!")
                            st.info("Actualizando la tabla...")
                            st.session_state['plan_recien_generado'] = plan_generado
                            del st.session_state['plan_modificado'] 
                            time.sleep(2)
                            st.rerun()

            st.divider()
    
            # --- (NUEVO) Panel de Reorganización Semanal y Generación de Plan ---
            if plan_semana_actual:
                st.header("🔄 2. Reorganiza tu Semana y Genera el Plan")
                st.info("Ajusta el plan para los próximos días si lo necesitas. Cuando estés listo, genera el plan para mañana.")
        
                dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
                # Preparamos los datos para la tabla editable
                plan_editable_data = {}
                for dia in dias:
                    plan_editable_data[f"{dia}_Plan"] = plan_semana_actual.get(f"{dia}_Plan", "-")
        
                df_plan_editable = pd.DataFrame([plan_editable_data])
        
                # Creamos una copia para que el usuario la edite
                plan_modificado_df = st.data_editor(df_plan_editable)

                if st.button("💾 Guardar Cambios y Generar Plan para Mañana"):
                    with st.spinner("Guardando tu nuevo plan y generando la rutina de mañana..."):
                        # 1. Guardamos la nueva estructura en el Google Sheet
                        actualizar_fila_plan_semanal(gspread_client, username, plan_modificado_df)

                        # 2. Cargamos el plan recién actualizado para pasárselo a la IA
                        plan_semana_confirmado = cargar_plan_semana(gspread_client, username)
                    
                        # 3. Llamamos a la IA con el objetivo claro
                        datos_ultimo_dia = {"entreno": resumen_entreno_hoy, "sensaciones": sensaciones, ...} # Necesitamos recuperar estos datos
                        historial_detallado_texto = historial_detallado_df.tail(20).to_string()
                
                        # Usamos la fecha del último registro guardado
                        fecha_ultimo_registro = #...
                        plan_generado = generar_plan_diario(perfil_usuario, historial_detallado_texto, datos_ultimo_dia, plan_semana_confirmado, fecha_ultimo_registro)

                        if plan_generado:
                            # Guardamos el plan generado en el registro del día anterior
                            actualizar_celda_registro(gspread_client, username, fecha_ultimo_registro, plan_generado)
                    
                            st.session_state['plan_recien_generado'] = plan_generado
                            st.rerun()
            
          
            
            if st.button("👁️ Mostrar mi plan para mañana"):
                if not historial_df.empty:
                    if 'Plan_Generado' in historial_df.columns:
                        ultimo_plan = historial_df.iloc[-1]['Plan_Generado']
                        st.markdown("---")
                        st.subheader("📋 Tu Plan Más Reciente")
                        st.markdown(ultimo_plan)
                    else:
                        st.warning("La columna 'Plan_Generado' no se encontró en el historial.")
                else:
                     st.warning("Aún no has generado ningún plan.")

if __name__ == '__main__':
    main()



















































