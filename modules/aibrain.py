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
    """Genera el plan detallado para mañana con lógica de reorganización y sobrecarga progresiva avanzada."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    fecha_hoy = fecha_de_registro
    fecha_manana = fecha_hoy + timedelta(days=1)
    
    dia_hoy_nombre = dias_semana[fecha_hoy.weekday()]
    dia_manana_nombre = dias_semana[fecha_manana.weekday()]
    
    lo_que_tocaba_hoy = plan_semanal_actual.get(f"{dia_hoy_nombre}_Plan", "No planificado")
    lo_que_toca_manana = plan_semanal_actual.get(f"{dia_manana_nombre}_Plan", "Día libre")

    prompt = f"""
    Eres un entrenador personal de élite, experto en fisiología, planificación adaptativa y sobrecarga progresiva. Tu objetivo es crear un plan DETALLADO para mañana, tomando decisiones inteligentes basadas en toda la información disponible.

    **INFORMACIÓN DISPONIBLE:**

    1.  **PLAN ESTRATÉGICO SEMANAL ORIGINAL:**
        {plan_semanal_actual.get('Plan_Original_Completo', '')}

    2.  **CONTEXTO DE HOY ({fecha_hoy.strftime('%A, %d')}):**
        - Entrenamiento que ESTABA PLANEADO para hoy: **{lo_que_tocaba_hoy}**
        - Entrenamiento que se HA REALIZADO REALMENTE hoy: **{datos_hoy.get('entreno', 'No especificado')}**
        - Sensaciones y otros datos de hoy: {datos_hoy}

    3.  **PLAN PARA MAÑANA ({fecha_manana.strftime('%A, %d')}):**
        - Según el plan original, mañana tocaría: **{lo_que_toca_manana}**.

    4.  **PERFIL Y CONTEXTO DEL ATLETA:**
        - Perfil Completo:
            - Objetivo: {perfil.get('Objetivo', 'No especificado')}
            - Lesiones/Limitaciones: {perfil.get('Lesiones/Limitaciones', 'Ninguna')}
            - Disponibilidad: {perfil.get('Disponibilidad', 'No especificada')}
            - Equipamiento: {perfil.get('Equipamiento', 'No especificado')}
        - Historial Detallado de Rendimiento (Series, Reps, Pesos): {historial_detallado_texto}

    **TU PROCESO DE DECISIÓN Y TAREAS (EN ESTE ORDEN ESTRICTO):**

    1.  **ANÁLISIS DE CONFLICTO MUSCULAR (REGLA CRÍTICA):** Compara los grupos musculares del entrenamiento REALIZADO hoy con los del entrenamiento planeado para MAÑANA.
        - **CASO A (Conflicto):** Si hay solapamiento (ej: hoy se hizo espalda y mañana toca espalda), **NO debes planificar espalda de nuevo.** La salud y la recuperación son la máxima prioridad.
        - **CASO B (Sin Conflicto):** Si no hay solapamiento, el plan de mañana se mantiene.

    2.  **ACCIÓN A TOMAR BASADA EN EL ANÁLISIS:**
        - **SI ESTÁS EN EL CASO A (Conflicto):**
            a. **REORGANIZA:** El entrenamiento de mañana será el que **estaba planeado para hoy ({lo_que_tocaba_hoy}) pero no se hizo.**
            b. **JUSTIFICA:** Empieza tu respuesta explicando el cambio de forma clara y motivadora.
            c. **RE-PLANIFICA:** En la sección `### 🔄 Sugerencia de Re-planificación Semanal`, sugiere cómo queda el resto de la semana.

        - **SI ESTÁS EN EL CASO B (Sin Conflicto):**
            a. **MANTIENE EL PLAN:** El entrenamiento de mañana seguirá siendo **{lo_que_toca_manana}**.
            b. **APLICA SOBRECARGA PROGRESIVA:** Usa el "Historial de Rendimiento" para detallar los ejercicios de mañana con los pesos y repeticiones adecuados. **Sé explícito con los pesos a usar** (ej: "Press Banca: 3x8 con 82.5 kg").

    3.  **CREA EL PLAN DETALLADO:** Basándote en tu decisión, crea el plan detallado para mañana.
        - **Respeta el Equipamiento:** Los ejercicios deben ser 100% realizables con el material disponible.
        - **Considera las Sensaciones:** Ajusta la intensidad o el volumen si el usuario reportó dolor o cansancio.

    4.  **AÑADE LAS SECCIONES ADICIONALES:** Crea siempre el plan de dieta y el consejo del día.

    **FORMATO DE SALIDA:**
    Usa el formato Markdown habitual. Si hay una justificación, ponla al principio.
    ### 🏋️ Plan de Entrenamiento para Mañana
    ...
    ### 🥗 Plan de Dieta para Mañana
    ...
    ### 💡 Consejo del Día
    ...
    (Opcional si es necesario)
    ### 🔄 Sugerencia de Re-planificación Semanal
    ...
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al contactar con la IA para el plan diario: {e}")
        return None
