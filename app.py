import pandas as pd
import streamlit as st
import plotly.express as px
import re
from io import BytesIO

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Indicadores de Acreditación HLS", page_icon="🏥", layout="wide"
)

# --- FUNCIONES DE AYUDA ---
def parse_meta_value(meta_string):
    if isinstance(meta_string, str):
        numero_match = re.search(r'\d+\.?\d*', meta_string)
        if numero_match:
            try:
                return float(numero_match.group(0)) / 100.0
            except (ValueError, TypeError): return None
    return None

def colorear_cumplimiento(val, meta, meta_string):
    if pd.isna(val) or meta is None:
        return ''
    if '≤' in meta_string or '<' in meta_string:
        color = 'green' if val <= meta else 'red'
    else:
        color = 'green' if val >= meta else 'red'
    return f'color: {color}'

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Datos')
    processed_data = output.getvalue()
    return processed_data

# --- CARGA Y PROCESAMIENTO DE DATOS ---
@st.cache_data
def cargar_datos():
    nombre_archivo = "SistemaIndicadores_Formulario.xlsm"
    df_indicadores = pd.read_excel(nombre_archivo, sheet_name="Indicadores")
    df_mediciones = pd.read_excel(nombre_archivo, sheet_name="BaseMediciones")
    df_completo = pd.merge(df_indicadores, df_mediciones, how="left", on=["Servicio", "Característica"])
    for col in ['Numerador', 'Denominador_y']:
        if col in df_completo.columns:
            df_completo[col] = pd.to_numeric(df_completo[col], errors='coerce').astype('Int64')
    return df_completo

df = cargar_datos()
def obtener_periodo(row):
    if row["Periodicidad"] == "TRIMESTRAL":
        if row["Mes"] == "Marzo": return "Trimestre I"
        elif row["Mes"] == "Junio": return "Trimestre II"
        elif row["Mes"] == "Septiembre": return "Trimestre III"
        elif row["Mes"] == "Diciembre": return "Trimestre IV"
        else: return None
    else:
        return row["Mes"]
df["Periodo"] = df.apply(obtener_periodo, axis=1)

# --- BARRA LATERAL ---
st.sidebar.header("Filtros del Dashboard:")

# Obtenemos la lista de años, la convertimos a enteros y la ordenamos
lista_años = sorted([int(año) for año in df["Año"].dropna().unique()], reverse=True)

año_seleccionado = st.sidebar.selectbox("Selecciona el Año:", options=lista_años)


# ... resto del código de la barra lateral ...
servicio_seleccionado = st.sidebar.selectbox("Selecciona el Servicio:", options=df["Servicio"].unique())
opciones_caracteristica = df[df["Servicio"] == servicio_seleccionado]["Característica"].unique()
caracteristica_seleccionada = st.sidebar.selectbox("Selecciona la Característica:", options=opciones_caracteristica)

# --- FILTRADO PRINCIPAL ---
df_info_indicador = df[(df["Servicio"] == servicio_seleccionado) & (df["Característica"] == caracteristica_seleccionada)]
df_para_grafico = df_info_indicador[df_info_indicador["Año"] == año_seleccionado].dropna(subset=['Periodo'])

# --- PÁGINA PRINCIPAL ---
st.title("🏥 Indicadores de Acreditación HLS")
st.markdown("---")

# --- TARJETAS DE KPIS ---
if not df_para_grafico.empty:
    info_indicador_kpi = df_info_indicador.iloc[0]
    meta_valor_kpi = parse_meta_value(info_indicador_kpi['Meta'])
    kpi1, kpi2 = st.columns(2)
    cumplimiento_anual = df_para_grafico['Porcentaje'].mean()
    cumple_meta = False
    if meta_valor_kpi is not None:
        meta_str = info_indicador_kpi['Meta']
        if '≤' in meta_str or '<' in meta_str:
            cumple_meta = cumplimiento_anual <= meta_valor_kpi
        else:
            cumple_meta = cumplimiento_anual >= meta_valor_kpi
    kpi1.metric(label=f"Cumplimiento Promedio {int(año_seleccionado)}", value=f"{cumplimiento_anual:.1%}", delta="Cumple Meta" if cumple_meta else "No Cumple Meta", delta_color="normal" if cumple_meta else "inverse")
    if len(df_para_grafico) > 1:
        ultimo_valor = df_para_grafico['Porcentaje'].iloc[-1]
        penultimo_valor = df_para_grafico['Porcentaje'].iloc[-2]
        kpi2.metric(label="Tendencia vs Periodo Anterior", value=f"{ultimo_valor:.1%}", delta=f"{(ultimo_valor - penultimo_valor):.1%}")

st.markdown("---")
col1, col2 = st.columns(2)

# Columna 1: Tarjeta de Información
with col1:
    st.subheader("📋 Detalles del Indicador")
    if not df_info_indicador.empty:
        info_indicador = df_info_indicador.iloc[0]
        st.markdown(f"**Ámbito:** {info_indicador['Ámbito_x']}")
        st.markdown(f"**Indicador:** {info_indicador['Nombre del Indicador']}")
        st.markdown(f"**Numerador:** {info_indicador['Nominador']}")
        st.markdown(f"**Denominador:** {info_indicador['Denominador_x']}")
        st.markdown(f"**Meta:** {info_indicador['Meta']}")
        st.markdown(f"**Periodicidad:** {info_indicador['Periodicidad']}")
    
# Columna 2: Gráfico de Barras y Tabla de Datos
with col2:
    st.subheader(f"📊 Cumplimiento en {int(año_seleccionado)}")
    if not df_para_grafico.empty:
        orden_cronologico = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Trimestre I", "Trimestre II", "Trimestre III", "Trimestre IV"]
        df_para_grafico['Periodo'] = pd.Categorical(df_para_grafico['Periodo'], categories=orden_cronologico, ordered=True)
        df_para_grafico = df_para_grafico.sort_values('Periodo')
        fig_barras = px.bar(df_para_grafico, x="Periodo", y="Porcentaje", text_auto=".1%")
        fig_barras.update_layout(yaxis_range=[0,1.1])
        meta_valor_grafico = parse_meta_value(info_indicador['Meta'])
        if meta_valor_grafico is not None:
            fig_barras.add_hline(y=meta_valor_grafico, line_dash="dash", line_color="red", annotation_text="Meta", annotation_position="bottom right")
        st.plotly_chart(fig_barras, use_container_width=True)

        st.markdown("#### Datos Detallados")
        tabla_para_mostrar = df_para_grafico[['Periodo', 'Numerador', 'Denominador_y', 'Porcentaje']].rename(columns={'Denominador_y': 'Denominador'})
        st.dataframe(tabla_para_mostrar.style.applymap(lambda val: colorear_cumplimiento(val, meta_valor_grafico, info_indicador['Meta']), subset=['Porcentaje']).format({'Porcentaje': '{:.1%}'}), use_container_width=True, hide_index=True)
        
        col_descarga1, col_descarga2 = st.columns(2)
        with col_descarga1:
            st.download_button(label="📥 Descargar datos como Excel", data=to_excel(tabla_para_mostrar), file_name=f"datos_{caracteristica_seleccionada}_{año_seleccionado}.xlsx", mime="application/vnd.ms-excel")
        with col_descarga2:
            st.info("Para descargar como PDF, usa la opción 'Imprimir' de tu navegador (Ctrl+P) y elige 'Guardar como PDF'.", icon="💡")
    else:
        st.info("No hay datos de medición para este indicador en el año seleccionado.")

st.markdown("---")

# --- CÓDIGO RESTAURADO: GRÁFICO DE LÍNEA HISTÓRICO ---
st.subheader("📈 Evolución Histórica del Cumplimiento")
df_historico = df_info_indicador.dropna(subset=['Año', 'Periodo'])

if not df_historico.empty:
    orden_cronologico_hist = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre", "Trimestre I", "Trimestre II", "Trimestre III", "Trimestre IV"]
    df_historico['Periodo'] = pd.Categorical(df_historico['Periodo'], categories=orden_cronologico_hist, ordered=True)
    df_historico = df_historico.sort_values(by=['Año', 'Periodo'])
    df_historico['Año-Periodo'] = df_historico['Año'].astype(int).astype(str) + '-' + df_historico['Periodo'].astype(str)
    
    fig_linea = px.line(
        df_historico, x="Año-Periodo", y="Porcentaje",
        title=f"Evolución Histórica para {caracteristica_seleccionada}", markers=True
    )
    fig_linea.update_layout(yaxis_range=[0,1.1], xaxis_title="Periodo")
    meta_valor_hist = parse_meta_value(df_historico.iloc[0]['Meta'])
    if meta_valor_hist is not None:
        fig_linea.add_hline(y=meta_valor_hist, line_dash="dash", line_color="red", annotation_text="Meta", annotation_position="bottom right")
    st.plotly_chart(fig_linea, use_container_width=True)
else:
    st.info("No hay datos históricos disponibles para este indicador.")