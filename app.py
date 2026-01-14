import streamlit as st
import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher
import urllib.parse

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Chat Tarifas", page_icon="🚌")

# --------------------------------------------------
# UTILIDADES TEXTO
# --------------------------------------------------
def normalizar(texto):
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()

def similares(a, b, umbral=0.82):
    return SequenceMatcher(None, a, b).ratio() >= umbral

# --------------------------------------------------
# CARGA DATOS
# --------------------------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv("tarifas_unificadas.csv", sep=";", encoding="utf-8")

    columnas_obligatorias = {"ORIGEN", "DESTINO", "EMPRESA", "MODALIDAD", "TARIFA"}
    if not columnas_obligatorias.issubset(df.columns):
        faltan = columnas_obligatorias - set(df.columns)
        st.error(f"❌ Falta la columna obligatoria: {', '.join(faltan)}")
        st.stop()

    df["ORIGEN_N"] = df["ORIGEN"].apply(normalizar)
    df["DESTINO_N"] = df["DESTINO"].apply(normalizar)

    return df

df = cargar_datos()

# --------------------------------------------------
# UI ENCABEZADO
# --------------------------------------------------
st.title("🚌 Routy")
st.caption("Tu asistente para consultar tarifas interurbanas en Córdoba")

# --------------------------------------------------
# SESIÓN CHAT
# --------------------------------------------------
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": "¡Hola! 😊 Soy Routy. ¿A dónde querés viajar?"
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

    # -----------------------------
    # SALUDOS / DESPEDIDAS
    # -----------------------------
    if texto in {"HOLA", "BUEN DIA", "BUENAS", "NO GRACIAS", "GRACIAS"}:
        respuesta = "😊 ¡Perfecto! ¿Querés consultar otro destino o puedo ayudarte en algo más?"
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        with st.chat_message("assistant"):
            st.markdown(respuesta)
        st.stop()

    # -----------------------------
    # EXTRAER DESTINO
    # -----------------------------
    destino_usuario = texto.replace("A ", "").replace("IR A ", "").strip()

    destinos_unicos = df["DESTINO_N"].unique()
    destino_match = None

    for d in destinos_unicos:
        if d in destino_usuario or similares(d, destino_usuario):
            destino_match = d
            break

    if not destino_match:
        respuesta = "🤔 No pude identificar el destino. Probá escribir por ejemplo: *a Río Cuarto*."
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        with st.chat_message("assistant"):
            st.markdown(respuesta)
        st.stop()

    # -----------------------------
    # FILTRAR DATOS
    # -----------------------------
    resultados = df[df["DESTINO_N"] == destino_match]

    if resultados.empty:
        respuesta = "😕 No encontré tarifas para ese destino."
        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
        with st.chat_message("assistant"):
            st.markdown(respuesta)
        st.stop()

    # UNA TARIFA POR EMPRESA (la más baja)
    tabla = (
        resultados
        .groupby(["EMPRESA", "MODALIDAD"], as_index=False)
        .agg({"TARIFA": "min"})
        .sort_values("TARIFA")
    )

    tabla["TARIFA"] = tabla["TARIFA"].apply(
        lambda x: f"$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    tabla = tabla.rename(columns={"TARIFA": "Tarifa ($)"})

    # -----------------------------
    # MOSTRAR RESULTADO
    # -----------------------------
    with st.chat_message("assistant"):
        st.markdown(f"🚌 **Opciones para viajar a {destino_match.title()}:**")
        st.dataframe(tabla, hide_index=True, use_container_width=True)

        mensaje_compartir = f"Consulté tarifas para viajar a {destino_match.title()} en Chat Tarifas 🚌"
        mensaje_url = urllib.parse.quote(mensaje_compartir)
        whatsapp_link = f"https://wa.me/?text={mensaje_url}"

        st.markdown(
            f"""
            📲 **Compartir consulta:**

            👉 [Enviar por WhatsApp]({whatsapp_link})  
            👉 [Compartir en redes](https://www.addtoany.com/share)
            """,
            unsafe_allow_html=True
        )

        cierre = "¿Querés consultar otro destino o puedo ayudarte en algo más?"
        st.markdown(cierre)
        st.session_state.mensajes.append({"role": "assistant", "content": cierre})


