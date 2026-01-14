import streamlit as st
import pandas as pd
import unicodedata
import re

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(
    page_title="Chat Tarifas",
    page_icon="🚌",
    layout="centered"
)

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================
def normalizar(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extraer_origen_destino(texto):
    texto_n = normalizar(texto)

    # Caso: "de cordoba a rio cuarto"
    match = re.search(r"de (.+?) a (.+)", texto_n)
    if match:
        return match.group(1), match.group(2)

    # Caso: "a rio cuarto" o "rio cuarto"
    match = re.search(r"a (.+)", texto_n)
    if match:
        return "cordoba", match.group(1)

    # Caso: solo destino
    return "cordoba", texto_n


def es_saludo(texto):
    return texto in ["hola", "buen dia", "buenos dias", "buenas", "buenas tardes"]


def es_despedida(texto):
    return texto in ["gracias", "chau", "adios", "hasta luego"]

# ============================================================
# CARGA DE DATOS
# ============================================================
@st.cache_data
def cargar_datos():
    df = pd.read_csv("tarifas_unificadas.csv", sep=";", encoding="utf-8")

    df.columns = [c.strip().upper() for c in df.columns]

    # ⚠️ AJUSTÁ ESTA LÍNEA SI TU COLUMNA SE LLAMA DISTINTO
    COLUMNA_TARIFA = [c for c in df.columns if "TARIFA" in c or "PRECIO" in c][0]

    df["ORIGEN_N"] = df["ORIGEN"].apply(normalizar)
    df["DESTINO_N"] = df["DESTINO"].apply(normalizar)
    df["TARIFA_USAR"] = df[COLUMNA_TARIFA]

    return df


df = cargar_datos()

# ============================================================
# INTERFAZ
# ============================================================
st.markdown(
    """
    <div style="text-align:center">
        <h1>🚌 Chat Tarifas</h1>
        <h4>Consulta de tarifas interurbanas de Córdoba</h4>
    </div>
    """,
    unsafe_allow_html=True
)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": "Hola 😊 ¿A qué destino querés viajar?"
        }
    ]

for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

consulta = st.chat_input("Escribí tu consulta…")

if consulta:
    st.session_state.mensajes.append({"role": "user", "content": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    texto_n = normalizar(consulta)

    if es_saludo(texto_n):
        respuesta = "¡Hola! 😊 Decime a qué destino querés viajar."
    elif es_despedida(texto_n):
        respuesta = "¡Gracias por consultar! Si necesitás otra tarifa, avisame 🚌"
    else:
        origen, destino = extraer_origen_destino(consulta)

        resultados = df[
            df["ORIGEN_N"].str.contains(origen) &
            df["DESTINO_N"].str.contains(destino)
        ]

        if resultados.empty:
            respuesta = "No encontré tarifas para ese destino. ¿Querés probar con otro?"
        else:
            with st.chat_message("assistant"):
                st.markdown(
                    f"🚌 Opciones para viajar de **{origen.title()}** a **{destino.title()}**:"
                )
                st.dataframe(
                    resultados[["EMPRESA", "MODALIDAD", "TARIFA_USAR"]]
                    .rename(columns={"TARIFA_USAR": "Tarifa ($)"}),
                    use_container_width=True
                )

            respuesta = "¿Querés consultar otro destino?"

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)



