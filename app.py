import streamlit as st
import pandas as pd
import unicodedata
import re

# ------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------
st.set_page_config(
    page_title="Routy - Consulta Tarifaria",
    page_icon="🚌",
    layout="centered"
)

# ------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------
def normalizar_texto(texto):
    """
    Convierte a mayúsculas, elimina tildes y caracteres especiales
    """
    if pd.isna(texto):
        return ""
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9 ]", "", texto)
    return texto.strip()


def extraer_tramo(texto):
    """
    Intenta extraer origen y destino desde una frase tipo:
    'de Córdoba a Carlos Paz'
    """
    texto = normalizar_texto(texto)

    patrones = [
        r"DE (.+?) A (.+)",
        r"DESDE (.+?) A (.+)"
    ]

    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    return None, None


# ------------------------------------------------------------
# CARGA DE DATOS
# ------------------------------------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv(
        "tarifas_unificadas.csv",
        sep=";",
        encoding="utf-8"
    )

    df["ORIGEN_NORM"] = df["ORIGEN"].apply(normalizar_texto)
    df["DESTINO_NORM"] = df["DESTINO"].apply(normalizar_texto)

    return df


df_tarifas = cargar_datos()

# ------------------------------------------------------------
# INTERFAZ - ENCABEZADO
# ------------------------------------------------------------
st.markdown(
    """
    <div style="text-align:center">
        <h1>🚌 Routy</h1>
        <h4>Tu asistente para consultar tarifas interurbanas en Córdoba</h4>
        <p>Escribí algo como: <b>“de Córdoba a Carlos Paz”</b></p>
    </div>
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------
# ESTADO DEL CHAT
# ------------------------------------------------------------
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": "¡Hola! 😊 Soy Routy 🚌 ¿A dónde querés viajar hoy?"
        }
    ]

# Mostrar historial
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------------------------------------------------
# INPUT DEL USUARIO
# ------------------------------------------------------------
consulta = st.chat_input("Escribí tu consulta…")

if consulta:
    # Mostrar mensaje del usuario
    st.session_state.mensajes.append({"role": "user", "content": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    origen, destino = extraer_tramo(consulta)

    if not origen or not destino:
        respuesta = "🤔 No pude identificar el origen y destino. Probá escribir algo como **de Córdoba a Carlos Paz**."
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        with st.chat_message("assistant"):
            st.markdown(respuesta)
    else:
        # Filtrar datos
        resultados = df_tarifas[
            (df_tarifas["ORIGEN_NORM"].str.contains(origen)) &
            (df_tarifas["DESTINO_NORM"].str.contains(destino))
        ]

        if resultados.empty:
            respuesta = "¡Uy! 😕 No encuentro ese tramo, ¿podrías revisar si está bien escrito?"
            st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
            with st.chat_message("assistant"):
                st.markdown(respuesta)
        else:
            resumen = (
                resultados
                .groupby(["EMPRESA", "MODALIDAD"], as_index=False)
                .agg(
                    TARIFA_MINIMA=("TARIFA", "min"),
                    TARIFA_MAXIMA=("TARIFA", "max")
                )
                .sort_values("TARIFA_MINIMA")
            )

            respuesta = f"¡Hola! 🚌 Encontré estas opciones para tu viaje de **{origen.title()}** a **{destino.title()}**:"
            st.session_state.mensajes.append({"role": "assistant", "content": respuesta})

            with st.chat_message("assistant"):
                st.markdown(respuesta)
                st.dataframe(
                    resumen.rename(columns={
                        "EMPRESA": "Empresa",
                        "MODALIDAD": "Modalidad",
                        "TARIFA_MINIMA": "Tarifa mínima ($)",
                        "TARIFA_MAXIMA": "Tarifa máxima ($)"
                    }),
                    use_container_width=True
                )

