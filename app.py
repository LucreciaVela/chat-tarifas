import streamlit as st
import pandas as pd
import unicodedata
import re

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Chat Tarifas",
    page_icon="🚌",
    layout="centered"
)

# ============================================================
# FUNCIONES DE TEXTO
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


def formatear_pesos(valor):
    return "$ {:,.2f}".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")


def es_saludo(texto):
    return texto in ["hola", "buen dia", "buenos dias", "buenas", "buenas tardes"]


def es_despedida(texto):
    return texto in ["gracias", "no gracias", "chau", "adios", "hasta luego"]


def extraer_origen_destino(texto):
    t = normalizar(texto)

    match = re.search(r"de (.+?) a (.+)", t)
    if match:
        return match.group(1), match.group(2)

    match = re.search(r"a (.+)", t)
    if match:
        return "cordoba", match.group(1)

    # solo destino
    return "cordoba", t

# ============================================================
# CARGA DE DATOS
# ============================================================
@st.cache_data
def cargar_datos():
    df = pd.read_csv("tarifas_unificadas.csv", sep=";", encoding="utf-8")
    df.columns = [c.strip().upper() for c in df.columns]

    # detectar columna tarifa
    col_tarifa = [c for c in df.columns if "TARIFA" in c or "PRECIO" in c][0]

    df["ORIGEN_N"] = df["ORIGEN"].apply(normalizar)
    df["DESTINO_N"] = df["DESTINO"].apply(normalizar)
    df["TARIFA_NUM"] = pd.to_numeric(df[col_tarifa], errors="coerce")

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
        {"role": "assistant", "content": "Hola 😊 ¿A qué destino querés viajar?"}
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
        respuesta = "¡Hola! 😊 ¿Querés consultar la tarifa de algún destino?"

    elif es_despedida(texto_n):
        respuesta = "¡Perfecto! 🙌 Si más tarde necesitás consultar otra tarifa, acá estoy."

    else:
        origen, destino = extraer_origen_destino(consulta)

        filtro = df[
            df["ORIGEN_N"].str.contains(origen) &
            df["DESTINO_N"].str.contains(destino)
        ]

        if filtro.empty:
            respuesta = "No encontré tarifas para ese destino. ¿Querés probar con otro?"

        else:
            resumen = (
                filtro
                .groupby("EMPRESA", as_index=False)
                .agg({"TARIFA_NUM": "min"})
                .sort_values("TARIFA_NUM")
            )

            resumen["Tarifa ($)"] = resumen["TARIFA_NUM"].apply(formatear_pesos)

            with st.chat_message("assistant"):
                st.markdown(
                    f"🚌 Tarifas para viajar de **{origen.title()}** a **{destino.title()}**:"
                )
                tabla = resumen[["EMPRESA", "Tarifa ($)"]].reset_index(drop=True)

st.dataframe(
    tabla,
    use_container_width=True,
    hide_index=True
)
import urllib.parse

mensaje_compartir = (
    f"Consulté las tarifas para viajar de {origen.title()} a {destino.title()} "
    f"en Chat Tarifas 🚌"
)

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
            respuesta = "¿Querés consultar otro destino o puedo ayudarte en algo más?"

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
    with st.chat_message("assistant"):
        st.markdown(respuesta)


