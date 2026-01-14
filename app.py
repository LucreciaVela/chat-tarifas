import streamlit as st
import pandas as pd
import unicodedata
import re
from difflib import get_close_matches

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(page_title="Chat Tarifas", page_icon="🚌")

ORIGEN_POR_DEFECTO = "CORDOBA"

# --------------------------------------------------
# UTILIDADES
# --------------------------------------------------
def normalizar(texto):
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z ]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()

# --------------------------------------------------
# CARGA CSV ROBUSTA
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
        st.error("❌ El CSV debe tener ORIGEN, DESTINO, EMPRESA y MODALIDAD")
        st.stop()

    # detectar tarifa (primera columna numérica)
    col_tarifa = df.select_dtypes(include="number").columns[0]
    df = df.rename(columns={col_tarifa: "TARIFA"})

    df["ORIGEN_N"] = df["ORIGEN"].apply(normalizar)
    df["DESTINO_N"] = df["DESTINO"].apply(normalizar)

    return df

df = cargar_datos()
DESTINOS = sorted(df["DESTINO_N"].unique())

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": "Hola 😊 Decime a qué destino querés viajar desde Córdoba."
        }
    ]

if "destino_pendiente" not in st.session_state:
    st.session_state.destino_pendiente = None

# --------------------------------------------------
# UI
# --------------------------------------------------
st.markdown("<h1 style='text-align:center'>🚌 Routy</h1>", unsafe_allow_html=True)

for m in st.session_state.mensajes:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --------------------------------------------------
# INPUT
# --------------------------------------------------
consulta = st.chat_input("Ej: Río Cuarto")

if consulta:
    st.session_state.mensajes.append({"role": "user", "content": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    texto = normalizar(consulta)

    # --------------------------------------------------
    # CONFIRMACIÓN PENDIENTE
    # --------------------------------------------------
    if st.session_state.destino_pendiente:
        if texto in {"SI", "SÍ"}:
            destino = st.session_state.destino_pendiente

            resultados = df[
                (df["ORIGEN_N"] == ORIGEN_POR_DEFECTO) &
                (df["DESTINO_N"] == destino)
            ]

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
                st.markdown(
                    f"🚌 **Tarifas para viajar de Córdoba a {destino.title()}:**"
                )
                st.dataframe(tabla, hide_index=True, use_container_width=True)

            st.session_state.mensajes.append({
                "role": "assistant",
                "content": "¿Querés consultar otro destino o puedo ayudarte en algo más?"
            })

            st.session_state.destino_pendiente = None

        else:
            st.session_state.mensajes.append({
                "role": "assistant",
                "content": "Perfecto 👍 Decime nuevamente a qué destino querés viajar."
            })
            st.session_state.destino_pendiente = None

    # --------------------------------------------------
    # NUEVA CONSULTA
    # --------------------------------------------------
    else:
        match = get_close_matches(texto, DESTINOS, n=1, cutoff=0.7)

        if not match:
            st.session_state.mensajes.append({
                "role": "assistant",
                "content": (
                    "🤔 No pude identificar el destino.\n\n"
                    "Probá escribir solo el nombre de la localidad, por ejemplo:\n"
                    "- Río Cuarto\n"
                    "- Carlos Paz"
                )
            })
        else:
            destino = match[0]
            st



