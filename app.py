import streamlit as st
import pandas as pd
import unicodedata
import re
from difflib import SequenceMatcher

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(
    page_title="Routy - Consulta Tarifaria",
    page_icon="🚌",
    layout="centered"
)

# ============================================================
# FUNCIONES DE TEXTO Y LENGUAJE NATURAL
# ============================================================
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
        "QUE TAL", "HEY"
    ]
    return any(s in texto for s in saludos)


def es_despedida(texto):
    despedidas = [
        "CHAU", "ADIOS", "GRACIAS",
        "MUCHAS GRACIAS", "NOS VEMOS", "HASTA LUEGO"
    ]
    return any(d in texto for d in despedidas)


def palabras_similares(p1, p2, umbral=0.8):
    return SequenceMatcher(None, p1, p2).ratio() >= umbral


PALABRAS_RUIDO = [
    "TERMINAL", "CENTRO", "CIUDAD", "BARRIO",
    "PROVINCIA", "CORDOBA", "CBA", "PCIA",
    "DE", "DEL", "LA", "EL"
]


def limpiar_localidad(texto):
    texto = normalizar_texto(texto)
    tokens = texto.split()
    tokens = [t for t in tokens if t not in PALABRAS_RUIDO]
    return tokens


def coincide_destino(tokens_fila, tokens_usuario):
    for t_usuario in tokens_usuario:
        if not any(
            t_usuario == t_fila or palabras_similares(t_usuario, t_fila)
            for t_fila in tokens_fila
        ):
            return False
    return True


def extraer_tramo(texto):
    texto_norm = normalizar_texto(texto)

    patrones = [
        r"DE (.+?) A (.+)",
        r"DESDE (.+?) A (.+)"
    ]

    for patron in patrones:
        match = re.search(patron, texto_norm)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    match = re.search(r"A (.+)", texto_norm)
    if match:
        return "CORDOBA", match.group(1).strip()

    return None, None

# ============================================================
# CARGA DE DATOS
# ============================================================
@st.cache_data
def cargar_datos():
    df = pd.read_csv(
        "tarifas_unificadas.csv",
        sep=";",
        encoding="utf-8"
    )

    df.columns = [c.strip().upper() for c in df.columns]

    columnas = {
        "EMPRESA": ["EMPRESA", "EMPRESA PRESTADORA"],
        "MODALIDAD": ["MODALIDAD", "TIPO SERVICIO"],
        "ORIGEN": ["ORIGEN", "LOCALIDAD ORIGEN"],
        "DESTINO": ["DESTINO", "LOCALIDAD DESTINO"],
        "TARIFA": ["TARIFA", "PRECIO", "IMPORTE"]
    }

    for col_std, posibles in columnas.items():
        for p in posibles:
            if p in df.columns:
                df[col_std] = df[p]
                break

    obligatorias = ["EMPRESA", "MODALIDAD", "ORIGEN", "DESTINO", "TARIFA"]
    for col in obligatorias:
        if col not in df.columns:
            st.error(f"❌ Falta la columna obligatoria: {col}")
            st.stop()

    df["ORIGEN_TOKENS"] = df["ORIGEN"].apply(limpiar_localidad)
    df["DESTINO_TOKENS"] = df["DESTINO"].apply(limpiar_localidad)

    return df


df_tarifas = cargar_datos()

# ============================================================
# INTERFAZ
# ============================================================
st.markdown(
    """
    <div style="text-align:center">
        <h1>🚌 Routy</h1>
        <h4>Tu asistente para consultar tarifas interurbanas en Córdoba</h4>
    </div>
    """,
    unsafe_allow_html=True
)

if "mensajes" not in st.session_state:
    st.session_state.mensajes = [
        {
            "role": "assistant",
            "content": (
                "¡Hola! 😊 Soy Routy 🚌\n\n"
                "Puedo ayudarte a consultar tarifas interurbanas.\n"
                "¿A dónde querés viajar?"
            )
        }
    ]

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

consulta = st.chat_input("Escribí tu consulta…")

if consulta:
    st.session_state.mensajes.append({"role": "user", "content": consulta})
    with st.chat_message("user"):
        st.markdown(consulta)

    texto_norm = normalizar_texto(consulta)

    if es_saludo(texto_norm):
        respuesta = (
            "¡Hola! 😊\n\n"
            "Decime a qué destino querés viajar y te muestro las tarifas 🚌"
        )

    elif es_despedida(texto_norm):
        respuesta = (
            "¡Gracias por consultar! 🙌\n\n"
            "Si necesitás averiguar otra tarifa, acá voy a estar 🚌🙂"
        )

    else:
        origen, destino = extraer_tramo(consulta)

        if not destino:
            respuesta = (
                "🤔 No pude identificar el destino.\n\n"
                "Podés escribir algo como:\n"
                "- *a Río Cuarto*\n"
                "- *de Córdoba a Villa María*"
            )
        else:
            tokens_destino_usuario = limpiar_localidad(destino)
            tokens_origen_usuario = limpiar_localidad(origen)

            mask_destino = df_tarifas["DESTINO_TOKENS"].apply(
                lambda x: coincide_destino(x, tokens_destino_usuario)
            )

            mask_origen = df_tarifas["ORIGEN_TOKENS"].apply(
                lambda x: coincide_destino(x, tokens_origen_usuario)
            )

            resultados = df_tarifas[mask_origen & mask_destino]

            if resultados.empty:
                respuesta = (
                    f"😕 No encontré tarifas para **{destino.title()}**.\n\n"
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

                with st.chat_message("assistant"):
                    st.markdown(
                        f"🚌 Opciones para viajar de **{origen.title()}** a **{destino.title()}**:"
                    )
                    st.dataframe(
                        resumen.rename(columns={
                            "EMPRESA": "Empresa",
                            "MODALIDAD": "Modalidad",
                            "TARIFA_MINIMA": "Tarifa mínima ($)",
                            "TARIFA_MAXIMA": "Tarifa máxima ($)"
                        }),
                        use_container_width=True
                    )

                respuesta = "¿Querés consultar otro destino?"

    st.session_state.mensajes.append(
        {"role": "assistant", "content": respuesta}
    )
    with st.chat_message("assistant"):
        st.markdown(respuesta)
