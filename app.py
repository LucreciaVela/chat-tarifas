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
# FUNCIONES DE NORMALIZACIÓN Y LENGUAJE
# ------------------------------------------------------------
def normalizar_texto(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9 ]", "", texto)
    return texto.strip()


def es_saludo(texto):
    saludos = [
        "HOLA", "BUEN DIA", "BUENOS DIAS",
        "BUENAS TARDES", "BUENAS NOCHES",
        "HEY", "QUE TAL"
    ]
    return any(s in texto for s in saludos)


def es_despedida(texto):
    despedidas = [
        "CHAU", "ADIOS", "HASTA LUEGO",
        "GRACIAS", "MUCHAS GRACIAS",
        "NOS VEMOS"
    ]
    return any(d in texto for d in despedidas)


def extraer_tramo(texto):
    texto_norm = normalizar_texto(texto)

    # Caso explícito: "de Córdoba a Carlos Paz"
    patrones = [
        r"DE (.+?) A (.+)",
        r"DESDE (.+?) A (.+)"
    ]

    for patron in patrones:
        match = re.search(patron, texto_norm)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    # Caso natural: "quiero ir a Río Cuarto" → se asume Córdoba
    match = re.search(r"A (.+)", texto_norm)
    if match:
        return "CORDOBA", match.group(1).strip()

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
# ENCABEZADO
# ------------------------------------------------------------
st.markdown(
    """
    <div style="text-align:center">
        <h1>🚌 Routy</h1>
        <h4>Tu asistente para consultar tarifas interurbanas en Córdoba</h4>
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
            "content": (
                "¡Hola! 😊 Soy Routy 🚌\n\n"
                "Puedo ayudarte a consultar tarifas de transporte interurbano.\n"
                "¿A dónde querés viajar?"
            )
        }
    ]

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ------------------------------------------------------------
# INPUT DEL USUARIO
# ------------------------------------------------------------
consulta = st.chat_input("Escribí tu consulta…")

if consulta:
    st.session_state.mensajes.append({"role": "user", "content": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    texto_norm = normalizar_texto(consulta)

    # ---------------- SALUDOS ----------------
    if es_saludo(texto_norm):
        respuesta = (
            "¡Hola! 😊\n\n"
            "Decime a qué destino querés viajar y te muestro las tarifas disponibles 🚌"
        )

    # ---------------- DESPEDIDAS ----------------
    elif es_despedida(texto_norm):
        respuesta = (
            "¡Gracias por consultar! 🙌\n\n"
            "Si necesitás averiguar otra tarifa, estoy acá para ayudarte 🚌🙂"
        )

    # ---------------- CONSULTA DE TARIFAS ----------------
    else:
        origen, destino = extraer_tramo(consulta)

        if not origen or not destino:
            respuesta = (
                "🤔 No pude identificar el destino.\n\n"
                "Podés decirme algo como:\n"
                "- *quiero ir a Río Cuarto*\n"
                "- *de Córdoba a Carlos Paz*"
            )
        else:
            resultados = df_tarifas[
                (df_tarifas["ORIGEN_NORM"].str.contains(origen)) &
                (df_tarifas["DESTINO_NORM"].str.contains(destino))
            ]

            if resultados.empty:
                respuesta = (
                    f"😕 No encontré tarifas para el tramo **{origen.title()} → {destino.title()}**.\n\n"
                    "¿Querés consultar otro destino?"
                )
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

                respuesta = (
                    f"🚌 Encontré estas opciones para viajar de **{origen.title()}** "
                    f"a **{destino.title()}**:\n\n"
                    "¿Querés consultar otro destino?"
                )

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

                st.session_state.mensajes.append(
                    {"role": "assistant", "content": respuesta}
                )
                st.stop()

    st.session_state.mensajes.append(
        {"role": "assistant", "content": respuesta}
    )
    with st.chat_message("assistant"):
        st.markdown(respuesta)



