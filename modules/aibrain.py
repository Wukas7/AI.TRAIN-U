import google.generativeai as genai
from datetime import datetime, timedelta
import streamlit as st # Necesario para st.error

def generar_plan_semana(perfil, historial_mes_str):
    """Genera la estructura de entrenamiento para 7 días con un formato estricto."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Eres un entrenador personal de élite. Tu tarea es diseñar una estructura de entrenamiento semanal.

    **PERFIL DEL USUARIO:**
    - Objetivo: {perfil.get('Objetivo', 'No especificado')}
    - Edad: {perfil.get('Edad', 'No especificado')}
    - Lesiones/Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
    - Disponibilidad: {perfil.get('Disponibilidad', 'No especificada')}
    - Equipamiento: {perfil.get('Equipamiento', 'No especificado')}
    
    **HISTORIAL DEL ÚLTIMO MES:**
    {historial_mes_str}

    **INSTRUCCIONES:**
    1.  **Analiza la Disponibilidad:** Diseña un plan que se ajuste estrictamente al número de días disponibles. Si el usuario solo puede 3 días, el plan debe tener 3 días de entrenamiento y 4 de descanso/recuperación.
    2.  **Considera el Equipamiento:** Los tipos de entrenamiento que sugieras deben ser realizables con el material disponible.
    3.  **Usa el Historial:** Observa el historial para asegurar variedad y una progresión lógica.

    **FORMATO DE SALIDA OBLIGATORIO:**
    - Responde con EXACTAMENTE 7 líneas.
    - Cada línea DEBE empezar con el nombre del día de la semana (Lunes, Martes,...), seguido de dos puntos y el plan.
    - NO incluyas saludos, introducciones o cualquier otro texto. Solo las 7 líneas del plan.

    **EJEMPLO DE RESPUESTA PERFECTA (para disponibilidad de 4 días):**
    Lunes: Empuje (Pecho, Hombro, Tríceps)
    Martes: Tirón (Espalda, Bíceps)
    Miércoles: Descanso total
    Jueves: Pierna (Cuádriceps, Femoral)
    Viernes: Cardio y Abdominales
    Sábado: Descanso total
    Domingo: Descanso total
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al generar el plan semana: {e}")
        return None

def generar_plan_diario(perfil, historial_detallado_texto, datos_hoy, plan_semanal_actual, fecha_de_registro):
    """Genera el plan detallado para mañana con lógica de decisión en Python y depuración avanzada."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fecha_hoy = fecha_de_registro
    fecha_manana = fecha_hoy + timedelta(days=1)
    
    dia_hoy_nombre = dias_semana[fecha_hoy.weekday()]
    dia_manana_nombre = dias_semana[fecha_manana.weekday()]
    
    lo_que_tocaba_hoy = plan_semanal_actual.get(f"{dia_hoy_nombre}_Plan", "No planificado")
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")
    entreno_realizado_hoy = datos_hoy.get('entreno', '').lower()

    # --- LÓGICA DE DECISIÓN MEJORADA (HECHA EN PYTHON) ---
    entrenamiento_objetivo = lo_que_toca_manana
    justificacion_texto = ""
    conflicto = False

    # Convertimos el plan de mañana en palabras clave para una mejor comparación
    palabras_clave_plan = [palabra for palabra in lo_que_toca_manana.lower().replace('(', '').replace(')', '').split() if len(palabra) > 3]

    # Comprobamos si alguna de las palabras clave del plan de mañana está en el entreno de hoy
    if entreno_realizado_hoy and any(palabra in entreno_realizado_hoy for palabra in palabras_clave_plan):
        conflicto = True

    if conflicto:
        entrenamiento_objetivo = lo_que_tocaba_hoy
        justificacion_texto = (
            f"**Justificación del Cambio:** Como hoy has entrenado ({entreno_realizado_hoy.splitlines()[0]}...), "
            f"lo cual se solapa con el plan de mañana ({lo_que_toca_manana}), vamos a reorganizar la semana para una recuperación óptima. "
            f"Mañana harás el entrenamiento que estaba planeado para hoy: **{lo_que_tocaba_hoy}**."
        )
    
    # --- (NUEVO) PANEL DE DEPURACIÓN ANTES DE LLAMAR A LA IA ---
    with st.expander("🐞 Información de Depuración (Pre-Llamada a IA)"):
        st.write("**Decisión Lógica de Python:**")
        st.write(f"- ¿Conflicto detectado?: **{conflicto}**")
        st.write(f"- Entrenamiento Realizado Hoy: `{entreno_realizado_hoy}`")
        st.write(f"- Plan Original para Mañana: `{lo_que_toca_manana}`")
        st.write(f"- **Objetivo final para la IA:** `{entrenamiento_objetivo}`")
        st.write(f"- Justificación generada: `{justificacion_texto}`")
    # -----------------------------------------------------------

    prompt = f"""
    Eres un entrenador personal. Tu única tarea es crear un plan DETALLADO para el objetivo específico que te doy.

    **Justificación del Plan (si aplica):**
    {justificacion_texto}

    **OBJETIVO DE ENTRENAMIENTO PARA MAÑANA:**
    **{entrenamiento_objetivo}**

    **INFORMACIÓN DEL ATLETA:**
    - Perfil: {perfil}
    - Historial de Rendimiento: {historial_detallado_texto}
    - Datos del día anterior: {datos_hoy}

    **INSTRUCCIONES:**
    1.  Crea un plan de entrenamiento detallado para el "OBJETIVO DE ENTRENAMIENTO PARA MAÑANA".
    2.  Aplica sobrecarga progresiva basándote en el historial.
    3.  Respeta el equipamiento y las sensaciones.
    4.  Crea el plan de dieta y el consejo del día.
    5.  Si la justificación indica un cambio, sugiere una re-planificación en la sección `### 🔄 Sugerencia de Re-planificación Semanal`.

    **FORMATO DE SALIDA:**
    ### 🏋️ Plan de Entrenamiento para Mañana
    ...
    ### 🥗 Plan de Dieta para Mañana
    ...
    ### 💡 Consejo del Día
    ...
    """
    try:
        response = model.generate_content(prompt)
        # (NUEVO) Comprobamos si la respuesta está vacía
        if not response.text or not response.text.strip():
            st.error("La IA ha devuelto una respuesta vacía. Puede ser un problema con el prompt o un filtro de seguridad.")
            return None
        return response.text
    except Exception as e:
        # (NUEVO) MOSTRAMOS EL ERROR COMPLETO EN LA APP
        st.error("Ha ocurrido un error al contactar con la IA. El plan no se ha podido generar.")
        st.exception(e) # st.exception muestra el traceback completo del error
        return None
