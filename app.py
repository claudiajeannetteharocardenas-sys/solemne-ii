import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

st.title("Tráfico Aereo Mensual")
st.subheader("Estadísticas históricas de tráfico aéreo nacional e internacional con relación a Chile (2022 - actualidad)")

# Configuración de la API
URL_API = "https://datos.gob.cl/api/3/action/datastore_search"
ID_RECURSO = "23a54a1b-6234-4bfb-b45b-84fa147dc2ec"

@st.cache_data(show_spinner="Obteniendo registros de vuelos...")
def cargar_registros_paginados(limite=32000):
    desplazamiento = 0
    registros = []

    while True:
        # Solicitar página de registros
        respuesta = requests.get(
            URL_API,
            params={
                "resource_id": ID_RECURSO,
                "limit": limite,
                "offset": desplazamiento
            },
            timeout=30
        )

        respuesta.raise_for_status()
        pagina = respuesta.json()['result']['records']

        # Si no hay más registros, terminar
        if not pagina:
            break

        registros.extend(pagina)
        desplazamiento += limite

    return pd.DataFrame(registros)

def grafico_pasajeros_por_mes(df):
    # Promedio de pasajeros agrupado por mes
    por_mes = df.groupby('Mes')['PASAJEROS'].mean().sort_index()

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(por_mes.index, por_mes.values, marker='o')

    # Etiqueta sobre cada punto
    for x, y in zip(por_mes.index, por_mes.values):
     ax.annotate(f'{y:.0f}M', (x, y), textcoords="offset points", xytext=(0, 8), ha='center')
      
    ax.set_xlabel('Mes')
    ax.set_ylabel('Pasajeros (promedio)')
    ax.set_xticks(range(1, 13))
    
    plt.tight_layout()
    return fig

def grafico_top10_destinos_pie(df):
     # Total de pasajeros por destino
    por_destino = df.groupby('DEST_1_N')['PASAJEROS'].sum().sort_values(ascending=False)
        
    topn = por_destino.head(10)
    otros = por_destino.iloc[10:].sum()
    datos = pd.concat([topn, pd.Series({'Otros': otros})])
    fig, ax = plt.subplots(figsize=(6, 6))

    # Colores para top N + gris para "Otros"
    colores = plt.cm.tab10.colors[:10] + ('lightgray',)
    ax.pie(datos.values, labels=datos.index, autopct='%1.1f%%', colors=colores)

    plt.tight_layout()
    return fig

def grafico_top5_aerolineas(df):
    # Top 5 aerolíneas por total de pasajeros
    top5 = df.groupby('Operador')['PASAJEROS'].sum().sort_values(ascending=False).head(5)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(top5.index[::-1], top5.values[::-1] / 1e6)
    ax.set_xlabel('Pasajeros (millones)')

    # Etiqueta al final de cada barra
    for bar, val in zip(bars, top5.values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, f'{val/1e6:.1f}M', va='center')

    # Margen extra para que no se corten las etiquetas
    ax.set_xlim(0, top5.max()/1e6 * 1.15)
    plt.tight_layout()
    return fig

def grafico_evolucion_anual(df):
    # Total de pasajeros agrupado por año
    por_anio = df.groupby('Ano')['PASAJEROS'].sum().sort_index()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(por_anio.index, por_anio.values / 1e6)

    # Etiqueta sobre cada barra
    for x, y in zip(por_anio.index, por_anio.values / 1e6):
        ax.text(x, y + 0.2, f'{y:.1f}M', ha='center')

    ax.set_xlabel('Año')
    ax.set_ylabel('Pasajeros (millones)')
    ax.set_xticks(por_anio.index)

    plt.tight_layout()
    return fig


try:
    df = cargar_registros_paginados()

    # Convertir columnas numéricas
    df['PASAJEROS'] = pd.to_numeric(df['PASAJEROS'], errors='coerce')
    df['Mes'] = pd.to_numeric(df['Mes'], errors='coerce')
    df['ruta'] = df['ORIG_1'] + '-' + df['DEST_1']  # Columna de ruta origen-destino

    st.caption(f"{len(df)} registros cargados · Fuente: Junta de Aeronáutica Civil (JAC) — datos.gob.cl")

    # Filtros
    filtro1, filtro2 = st.columns(2)

    with filtro1:
        tipos = ['Todos'] + sorted(df['NAC'].unique().tolist())
        tipo = st.radio('Tipo de vuelo', tipos, horizontal=True)

    with filtro2:
        anios = sorted(df['Ano'].unique().tolist())
        anios_seleccionados = st.multiselect('Filtrar por año', anios, default=anios)

    # Aplicar filtros
    if tipo == 'Todos':
        df_filtrado = df
    else:
        df_filtrado = df[df['NAC'] == tipo]

    if anios_seleccionados:
        df_filtrado = df_filtrado[df_filtrado['Ano'].isin(anios_seleccionados)]

    # Pestañas de gráficos
    tab1, tab2, tab3, tab4 = st.tabs(['Pasajeros por mes', 'Top 10 destinos', 'Top 5 aerolíneas', 'Evolución anual'])

    with tab1:
        st.subheader("Promedio de pasajeros por mes")
        st.caption("Promedio de pasajeros transportados por mes.")
        st.pyplot(grafico_pasajeros_por_mes(df_filtrado))

    with tab2:
        st.subheader("Top 10 destinos más viajados")
        st.caption("Distribución porcentual de pasajeros por destino.")
        st.pyplot(grafico_top10_destinos_pie(df_filtrado))

    with tab3:
        st.subheader("Top 5 aerolíneas por pasajeros transportados")
        st.caption("Total de pasajeros por aerolínea.")
        st.pyplot(grafico_top5_aerolineas(df_filtrado))

    with tab4:
        st.subheader("Evolución anual de pasajeros")
        st.caption("Total de pasajeros transportados por año.")
        st.pyplot(grafico_evolucion_anual(df_filtrado))

    # Métricas en barra lateral
    st.sidebar.metric("Total aerolíneas", df['Operador'].nunique())
    st.sidebar.metric("Total destinos", df['DEST_1_N'].nunique())
    st.sidebar.metric("Total rutas", df['ruta'].nunique())

except Exception as e:
    st.error("Error al obtener los datos. Intenta recargar la página.")
    st.exception(e)
