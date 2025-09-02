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
    """Genera el plan detallado para mañana con lógica de decisión en Python."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fecha_hoy = fecha_de_registro
    fecha_manana = fecha_hoy + timedelta(days=1)
    
    dia_hoy_nombre = dias_semana[fecha_hoy.weekday()]
    dia_manana_nombre = dias_semana[fecha_manana.weekday()]
    
    lo_que_tocaba_hoy = plan_semanal_actual.get(f"{dia_hoy_nombre}_Plan", "No planificado")
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")
    entreno_realizado_hoy = datos_hoy.get('entreno', '').lower()

    # --- LÓGICA DE DECISIÓN (HECHA EN PYTHON) ---
    entrenamiento_objetivo = lo_que_toca_manana
    justificacion_texto = ""
    conflicto = False

    # Verificamos si hay conflicto (ej: si el plan de mañana "Espalda" está en el entreno de hoy "Remo con barra (Espalda)")
    if lo_que_toca_manana.lower() in entreno_realizado_hoy or any(keyword in entreno_realizado_hoy for keyword in lo_que_toca_manana.lower().split()):
        conflicto = True

    if conflicto:
        # CASO A: Hay conflicto. Reorganizamos.
        entrenamiento_objetivo = lo_que_tocaba_hoy # El objetivo ahora es el entreno que se saltó hoy
        justificacion_texto = (
            f"**¡Atención, entrenador!** Como hoy has entrenado **{entreno_realizado_hoy.splitlines()[0]}** (que se solapa con el plan de mañana), "
            f"vamos a reorganizar la semana para asegurar una recuperación perfecta. Mañana harás el entrenamiento que estaba planeado para hoy: **{lo_que_tocaba_hoy}**."
        )
        # Aquí también se activaría la re-planificación
    
    # --- FIN DE LA LÓGICA DE DECISIÓN ---


    # --- EL NUEVO PROMPT (MÁS SIMPLE Y DIRECTO) ---
    prompt = f"""
    Eres un entrenador personal de élite. Tu única tarea es crear un plan de entrenamiento y dieta DETALLADO para un objetivo específico.

    **JUSTIFICACIÓN DEL PLAN DE HOY (si la hay):**
    {justificacion_texto}

    **OBJETIVO DE ENTRENAMIENTO PARA MAÑANA:**
    **{entrenamiento_objetivo}**

    **INFORMACIÓN DEL ATLETA:**
    - Perfil: {perfil}
    - Historial de Rendimiento: {historial_detallado_texto}
    - Datos del día anterior (sensaciones, nutrición): {datos_hoy}

    **INSTRUCCIONES:**
    1.  Crea un plan de entrenamiento detallado para el **"OBJETIVO DE ENTRENAMIENTO PARA MAÑANA"** que te he dado.
    2.  Aplica **sobrecarga progresiva** basándote en el historial. Sé explícito con los pesos.
    3.  Respeta el **equipamiento** y las **sensaciones** del usuario.
    4.  Crea el plan de dieta y el consejo del día.
    5.  Si la justificación inicial indica un cambio, sugiere una re-planificación semanal en la sección `### 🔄 Sugerencia de Re-planificación Semanal`.

    **FORMATO DE SALIDA:**
    Usa el formato Markdown habitual. Si hay justificación, inclúyela al principio.
    ### 🏋️ Plan de Entrenamiento para Mañana
    ### 🥗 Plan de Dieta para Mañana
    ### 💡 Consejo del Día
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None
