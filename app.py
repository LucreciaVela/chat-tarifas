import streamlit as st
import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher
import urllib.parse

# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------
st.set_page_config(
    page_title="Chat Tarifas",
    page_icon="🚌",
    layout="centered"
)

# --------------------------------------------------
# FUNCIONES DE TEXTO
# --------------------------------------------------
def normalizar(texto):
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def similar(a, b, umbral=0.8):
    return SequenceMatcher(None, a, b).ratio() >= umbral


def es_saludo(texto):
    return texto in {"HOLA", "BUEN DIA", "BUENOS DIAS", "BUENAS"}


def es_despedida(texto):
    return texto in {"GRACIAS", "NO GRACIAS", "CHAU", "ADIOS"}


def parece_consulta_tarifaria(texto):
    palabras = [
        "A ", "IR", "VIAJAR", "DESTINO",
        "TARIFA", "PRECIO",
        "RIO", "VILLA", "SAN", "CORDOBA"
    ]
    return any(p in texto for p in palabras)

# --------------------------------------------------
# CARGA DE DATOS (CSV ROBUSTO)
# --------------------------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv(
        "tarifas_unificadas.csv",
        sep=";",
        engine="python",
        encoding="utf-8",
        on_bad_lines="skip"
    )

    df.columns = [c.strip().upper() for c in df.columns]

    obligatorias = {"ORIGEN", "DESTINO", "EMPRESA", "MODALIDAD"}
    if not obligatorias.issubset(df.columns):
        st.error("❌ El CSV debe tener las columnas ORIGEN, DESTINO, EMPRESA y MODALIDAD")
        st.stop()

    # detectar columna de tarifa automáticamente (numérica)
    columnas_numericas = df.select_dtypes(include="number").columns.tolist()
    if not columnas_numericas:
        st.error("❌ No se encontró ninguna columna numérica de tarifa")
        st.stop()

    df = df.rename(columns={columnas_numericas[0]: "TARIFA"})

    df["ORIGEN_N"] = df["ORIGEN"].apply(normalizar)
    df["DESTINO_N"] = df["DESTINO"].apply(normalizar)

    return df


df = cargar_datos()

# --------------------------------------------------
# INTERFAZ
# --------------------------------------------------
st.markdown("<h1 style='text-align:center'>🚌 Routy</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center'>Consulta de tarifas interurbanas de Córdoba</p>",
    unsafe_allow_html=True
)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": "¡Hola! 😊 Soy Routy. ¿A qué destino querés viajar?"
        }
    ]

for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --------------------------------------------------
# INPUT
# --------------------------------------------------
consulta = st.chat_input("Escribí tu consulta...")

if consulta:
    st.session_state.mensajes.append({"role": "user", "content": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    texto = normalizar(consulta)

    if es_saludo(texto):
        respuesta = "¡Hola! 😊 ¿Querés consultar la tarifa de algún destino?"
    elif es_despedida(texto):
        respuesta = "¡Gracias por escribir! 🙌 Si necesitás consultar otra tarifa, acá estoy."
    elif not parece_consulta_tarifaria(texto):
        respuesta = (
            "🙂 Puedo ayudarte solo con consultas de **tarifas de transporte interurbano**.\n\n"
            "Decime a qué destino viajás y te muestro las opciones 🚌"
        )
    else:
        destinos = df["DESTINO_N"].unique().tolist()
        destino_match = None

        for d in destinos:
            if d in texto or similar(d, texto):
                destino_match = d
                break

        if not destino_match:
            respuesta = (
                "🤔 No pude identificar el destino.\n\n"
                "Probá escribir algo como:\n"
                "- *a Río Cuarto*\n"
                "- *viajar a Villa María*"
            )
        else:
            resultados = df[df["DESTINO_N"] == destino_match]

            tabla = (
                resultados
                .groupby(["EMPRESA", "MODALIDAD"], as_index=False)
                .agg({"TARIFA": "min"})
                .sort_values("TARIFA")
            )

            tabla["Tarifa ($)"] = tabla["TARIFA"].apply(
                lambda x: f"$ {int(round(x)):,}".replace(",", ".")
            )

            tabla = tabla[["EMPRESA", "MODALIDAD", "Tarifa ($)"]]

            with st.chat_message("assistant"):
                st.markdown(f"🚌 **Opciones para viajar a {destino_match.title()}:**")
                st.dataframe(tabla, hide_index=True, use_container_width=True)

                mensaje = f"Consulté tarifas para viajar a {destino_match.title()} en Chat Tarifas 🚌"
                url = urllib.parse.quote(mensaje)
                whatsapp = f"https://wa.me/?text={url}"

                st.markdown(
                    f"""
                    📲 **Compartir consulta**
                    👉 [Enviar por WhatsApp]({whatsapp})
                    """,
                    unsafe_allow_html=True
                )

            respuesta = "¿Querés consultar otro destino o puedo ayudarte en algo más?"

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)


