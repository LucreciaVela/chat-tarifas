import streamlit as st
import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher
import urllib.parse

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Chat Tarifas", page_icon="🚌", layout="centered")

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

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv("tarifas_unificadas.csv")

    df.columns = [c.strip().upper() for c in df.columns]

    obligatorias = {"ORIGEN", "DESTINO", "EMPRESA", "MODALIDAD"}
    if not obligatorias.issubset(df.columns):
        st.error("❌ Faltan columnas obligatorias: ORIGEN, DESTINO, EMPRESA o MODALIDAD")
        st.stop()

    # detectar columna tarifa (numérica)
    columnas_numericas = df.select_dtypes(include="number").columns.tolist()
    if not columnas_numericas:
        st.error("❌ No se encontró ninguna columna numérica de tarifa")
        st.stop()

    tarifa_col = columnas_numericas[0]  # toma la primera numérica
    df = df.rename(columns={tarifa_col: "TARIFA"})

    df["ORIGEN_N"] = df["ORIGEN"].apply(normalizar)
    df["DESTINO_N"] = df["DESTINO"].apply(normalizar)

    return df

df = cargar_datos()

# --------------------------------------------------
# UI
# --------------------------------------------------
st.markdown("<h1 style='text-align:center'>🚌 Routy</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center'>Tu asistente para consultar tarifas interurbanas en Córdoba</p>", unsafe_allow_html=True)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": "¡Hola! 😊 Soy Routy. Decime a qué destino querés viajar y te muestro las tarifas."
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

    # saludos / despedidas
    if texto in ["HOLA", "BUEN DIA", "BUENAS", "GRACIAS", "NO GRACIAS"]:
        respuesta = "😊 ¡Gracias por escribir! ¿Querés consultar otro destino o puedo ayudarte en algo más?"
    else:
        # buscar destino
        destinos = df["DESTINO_N"].unique().tolist()
        destino_match = None

        for d in destinos:
            if d in texto or similar(d, texto):
                destino_match = d
                break

        if not destino_match:
            respuesta = "🤔 No pude identificar el destino. Probá escribir algo como *a Río Cuarto* o *de Córdoba a Villa María*."
        else:
            resultados = df[df["DESTINO_N"] == destino_match]

            # una tarifa por empresa (la más baja)
            tabla = (
                resultados
                .groupby(["EMPRESA", "MODALIDAD"], as_index=False)
                .agg({"TARIFA": "min"})
            )

            tabla["Tarifa ($)"] = tabla["TARIFA"].apply(
                lambda x: f"$ {int(round(x)):,}".replace(",", ".")
            )

            tabla = tabla[["EMPRESA", "MODALIDAD", "Tarifa ($)"]]

            with st.chat_message("assistant"):
                st.markdown(f"🚌 **Opciones para viajar a {destino_match.title()}:**")
                st.dataframe(tabla, hide_index=True)

                mensaje = f"Consulté las tarifas para viajar a {destino_match.title()} en Chat Tarifas 🚌"
                url = urllib.parse.quote(mensaje)
                whatsapp = f"https://wa.me/?text={url}"

                st.markdown(
                    f"""
                    **📤 Compartir consulta**
                    👉 [Enviar por WhatsApp]({whatsapp})  
                    👉 [Compartir en redes](https://www.addtoany.com/share)
                    """,
                    unsafe_allow_html=True
                )

            respuesta = "¿Querés consultar otro destino o puedo ayudarte en algo más?"

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)
