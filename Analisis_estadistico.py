import pandas as pd
import numpy as np
import sys
import math
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from Rutas import carpetas_op3_individual
from tqdm import tqdm
import time
import logging

# Constantes
PERCENTIL_SUPERIOR = 0.997
PERCENTIL_INFERIOR = 0.003
ANCHO = 560 / 96
ALTO = 420 / 96
DPI = 250
LIMITE_CARGABILIDAD = 100
PERCENTILES = [0.1, 1.0, 5.0]
PERCENTILES_REF = [1, 5]

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

# FUNCION AUXILIAR 1
def analisis_por_elemento(df_individual, horas_serie, lista_percentiles, lista_series):
    resultados_por_componente = []
    for serie in lista_series:
        df_temporal = (
            df_individual[df_individual['Serie'] == serie]
            .sort_values(by=['loading_percent'], ascending=False)
            .copy())
        df_temporal['tiempo_acumulado'] = df_temporal['duracion'].cumsum()
        df_temporal['tiempo_porcentual'] = (df_temporal['tiempo_acumulado'] * 100) / horas_serie
        resultados_serie = []
        for tiempo_percentil in lista_percentiles:
            df_aux = df_temporal[df_temporal['tiempo_porcentual'] > tiempo_percentil]
            valor_percentil = df_aux['loading_percent'].max()
            resultados_serie.append(valor_percentil)
        resultados_por_componente.append((serie, *resultados_serie))
    df_estadisticas = pd.DataFrame(
        resultados_por_componente,
        columns=['Serie', 'valor_p1', 'valor_p2', 'valor_p3'])
    valor_prom_p1 = df_estadisticas['valor_p1'].mean()
    valor_prom_p2 = df_estadisticas['valor_p2'].mean()
    valor_prom_p3 = df_estadisticas['valor_p3'].mean()
    return (valor_prom_p1, valor_prom_p2, valor_prom_p3)

# FUNCIÓN AUXILIAR

def aplicar_tema_light(ax, titulo, subtitulo, xlabel, ylabel):
    ax.set_facecolor('white')
    ax.grid(True, color='#dddddd', linewidth=0.7, linestyle='-')
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor('#cccccc')
        spine.set_linewidth(0.8)
    ax.set_title(titulo, fontsize=12, fontweight='bold', ha='center', color='black')
    ax.set_xlabel(xlabel, fontsize=7)
    ax.set_ylabel(ylabel, fontsize=7)
    if subtitulo:
        ax.set_title(titulo, fontsize=12, fontweight='bold', ha='center', color='black', pad=14)
        ax.text(0.5, 1.01, subtitulo, transform=ax.transAxes,
                fontsize=8, fontweight='bold', ha='center', va='bottom', color='black')

def graficas(df_slice_result, df_duraci, componente, ruta_graficas, post_analisis):
    df_individual = df_slice_result.copy()
    df_pre_grafica = df_individual[df_individual['Serie'] == 1].copy()
    df_fechas = df_pre_grafica[['Etapa', 'Bloque', 'Fecha']].copy()
    df_pre_grafica = df_pre_grafica[['Etapa', 'Bloque', 'Componente']].copy()
    # Años y quiebres para la serie temporal
    df_fechas['Fecha'] = pd.to_datetime(df_fechas['Fecha'])
    df_fechas = df_fechas.reset_index(drop=True)
    anios = df_fechas['Fecha'].dt.year.unique().tolist()
    cantidades = [len(df_fechas[df_fechas['Fecha'].dt.year == anio]) for anio in anios]
    quiebres = np.cumsum(np.array(cantidades))
    quiebres = np.insert(quiebres, 0, 0)[:-1]
    # Tablas pivot
    df_pivot_1 = df_individual.pivot_table(index=['Etapa','Bloque'], columns='Serie', values='loading_percent')
    df_pivot_2 = df_individual.pivot_table(index=['Etapa','Bloque'], columns='Serie', values='Flujo_mw')
    df_pivot_1['Cargab_prom'] = df_pivot_1.mean(axis=1)
    df_pivot_2['Flujo_prom'] = df_pivot_2.mean(axis=1)
    df_pre_grafica['Cargab'] = df_pivot_1['Cargab_prom'].values
    df_pre_grafica['Flujo'] = df_pivot_2['Flujo_prom'].values
    flujos = df_pivot_2['Flujo_prom'].tolist()
    df_pre_grafica = df_pre_grafica.reset_index(drop=True)
    df_pre_grafica = pd.merge(df_pre_grafica, df_duraci, on='Bloque', how='left')
    df_grafica_cargab = df_pre_grafica[['Etapa','Bloque','Cargab','duracion']].copy()
    df_grafica_flujos = df_pre_grafica[['Etapa','Bloque','Flujo','duracion']].copy()
    df_grafica_cargab = df_grafica_cargab.sort_values(by='Cargab', ascending=False)
    df_grafica_flujos = df_grafica_flujos.sort_values(by='Flujo',  ascending=False)
    df_grafica_cargab['Horas_Acum'] = df_grafica_cargab['duracion'].cumsum()
    df_grafica_flujos['Horas_Acum'] = df_grafica_flujos['duracion'].cumsum()
    df_grafica_cargab['Horas_Porcent'] = (df_grafica_cargab['Horas_Acum'] * 100) / df_grafica_cargab['duracion'].sum()
    df_grafica_flujos['Horas_Porcent'] = (df_grafica_flujos['Horas_Acum'] * 100) / df_grafica_flujos['duracion'].sum()
    df_grafica_cargab = df_grafica_cargab.reset_index(drop=True)
    df_grafica_flujos = df_grafica_flujos.reset_index(drop=True)
    # Configuraciones previas
    Nombre = componente
    ruta_graficas = ruta_graficas/Nombre
    ruta_graficas.mkdir(parents=True, exist_ok=True)
    lim_min = df_grafica_flujos['Flujo'].min()
    lim_max = df_grafica_flujos['Flujo'].max()
    margen = (lim_max - lim_min) * 0.05
    lim_max_ajs = lim_max + margen
    lim_min_ajs = lim_min
    # G.1) Curva de Duración de Cargabilidad
    # desempaquetado de percentiles
    p1, p2, p3 = post_analisis
    #lim eje y
    fin_y = math.ceil(df_pivot_1['Cargab_prom'].max())
    # graficamos
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO))
    ax.plot(df_grafica_cargab['Horas_Porcent'], df_grafica_cargab['Cargab'], color='blue', linewidth=2)
    ax.axvline(1, color = 'orangered', linestyle = '--', linewidth = 1, label = f'P_1% = {p2:.1f} %')
    ax.axvline(5, color = 'lime', linestyle = '--', linewidth = 1, label = f'P_5% = {p3:.1f} %')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, fin_y)
    ax.set_xticks(range(0, 101, 10))
    ax.tick_params(axis = 'both', labelsize = 7)
    ax.set_yticks(np.linspace(0, fin_y + 1, 10))
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:.0f}'))
    aplicar_tema_light(ax, titulo='Curva de duracion de carga %', subtitulo=Nombre,
                    xlabel='Tiempo Acumulado (%)', ylabel='Cargabilidad')
    ax.legend(title="Percentiles Críticos", loc='upper right', fontsize=7, shadow=True)
    plt.tight_layout()
    plt.savefig(f"{ruta_graficas}/{Nombre}_G1.png", dpi=DPI)
    plt.close()
    # G.2) Curva de Duración de Flujo
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO))
    ax.plot(df_grafica_flujos['Horas_Porcent'], df_grafica_flujos['Flujo'], color='orange', linewidth=1.75)
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 10))
    y_inicio = round(lim_min_ajs / 10) * 10
    y_fin    = round(lim_max_ajs / 10) * 10
    ax.set_yticks(np.linspace(y_inicio, y_fin, 10))
    ax.set_ylim(lim_min_ajs, lim_max_ajs)
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:.0f}'))
    aplicar_tema_light(ax, titulo='Curva de duracion de carga MW', subtitulo=Nombre,
                    xlabel='Tiempo Acumulado (%)', ylabel='Flujo [MW]')
    ax.tick_params(axis = 'both', labelsize = 7)
    plt.tight_layout()
    plt.savefig(f"{ruta_graficas}/{Nombre}_G2.png", dpi=DPI)
    plt.close()
    # G.3) Serie temporal de flujo
    fig, ax = plt.subplots(figsize=(ANCHO * 1.5, ALTO))
    ax.plot(np.arange(1, len(df_fechas['Fecha']) + 1, dtype=int), flujos, color='blue', linewidth=1.0)
    ax.set_xticks(quiebres)
    ax.set_xticklabels(anios)
    ax.set_ylim(lim_min_ajs, lim_max_ajs)
    aplicar_tema_light(ax, titulo='Serie temporal', subtitulo=Nombre,
                    xlabel='Periodo de estudio', ylabel='Flujos [MW]')
    ax.tick_params(axis = 'both', labelsize = 7)
    plt.tight_layout()
    plt.savefig(f"{ruta_graficas}/{Nombre}_G3.png", dpi=DPI)
    plt.close()
    # G.4) Distribución de frecuencia
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO))
    sns.histplot(df_grafica_flujos['Flujo'], bins=11, kde=False,
                color='greenyellow', edgecolor='green', stat='count', ax=ax)
    ax2 = ax.twinx()
    sns.kdeplot(df_grafica_flujos['Flujo'], color='black', linewidth=2, ax=ax2)
    ax2.set_yticks([])
    ax2.set_ylabel('')
    asimetria = df_grafica_flujos['Flujo'].skew()
    mensaje = f"Asimetria: {asimetria:.2f}\n" + ("Asimetría Positiva" if asimetria >= 0 else "Asimetría Negativa")
    ax.text(0.95, 0.95, mensaje, transform=ax.transAxes,
            ha='right', va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.6))
    plt.title(f'Distribución de Frecuencia de Flujos para {Nombre}')
    ax.set_xlabel('Flujo [MW]')
    ax.set_ylabel('Cantidad de Registros (Conteo)')
    ax.grid(True, color='#dddddd', linewidth=0.7, linestyle='-')
    ax.tick_params(axis = 'both', labelsize = 7)
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(f"{ruta_graficas}/{Nombre}_G4.png", dpi=DPI)
    plt.close()
    # G5) Boxplot para flujos
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO))
    sns.boxplot(
        y=df_pre_grafica['Flujo'],
        color='plum',
        width=0.3,
        fliersize=3,
        linewidth=1.0,
        ax=ax,)
    aplicar_tema_light(ax, titulo='Boxplot flujos [MW].', subtitulo=Nombre,
                    xlabel='Promedio escenarios.', ylabel='Flujo [MW]')
    ax.set_xticks([])
    ax.tick_params(axis = 'both', labelsize = 6)
    plt.tight_layout()
    plt.savefig(f"{ruta_graficas}/{Nombre}_G5.png", dpi=DPI)
    plt.close()

# WORKER (corre en proceso hijo)
def _procesar_elemento_worker(nombre : str, df_slice_cargab : pd.DataFrame, df_slice_result : pd.DataFrame,
    df_duraci : pd.DataFrame, horas_serie : float, lista_percentiles : list, lista_series : np.ndarray,
    fp : float, net_line_data : pd.DataFrame, net_trafo_data : pd.DataFrame, net_bus_data : pd.DataFrame,
    generar_graficas : bool, ruta_graficas : str) -> list:
    post_analisis = analisis_por_elemento(
        df_slice_cargab, horas_serie, lista_percentiles, lista_series)
    if generar_graficas:
        graficas( df_slice_result=df_slice_result, df_duraci=df_duraci, componente=nombre, ruta_graficas=ruta_graficas,
                post_analisis = post_analisis)
    if nombre in net_line_data['name'].values:
        linea_data = net_line_data[net_line_data['name'] == nombre].iloc[0]
        corriente_nom = linea_data['max_i_ka']
        barra = linea_data['from_bus']
        Un = net_bus_data.loc[barra, 'vn_kv']
        capacidad_nominal_mva = corriente_nom * np.sqrt(3) * Un / fp
    else:
        capacidad_nominal_mva = (
            net_trafo_data.loc[net_trafo_data['name'] == nombre, 'sn_mva'].values[0]) / fp
    max_registrado = df_slice_cargab['loading_percent'].max()
    return [nombre, *post_analisis, max_registrado, capacidad_nominal_mva]

# FUNCIÓN PRINCIPAL
def analisis_caso_base(df_cargabilidades : pd.DataFrame, df_flujos : pd.DataFrame, df_duraci : pd.DataFrame,
    net, datos_estudio : dict, parametros_red, rta_cn : str, generar_graficas : bool,
    ruta_graficas : str, nucleos: int, trafos_limpios: list, ) -> pd.DataFrame:
    # Validación de escenarios 
    escenarios_simulados = df_cargabilidades[['Etapa','Serie','Bloque']].drop_duplicates()
    escenarios_esperados = (
        datos_estudio['numero_etapas'] *
        datos_estudio['numero_series'] *
        datos_estudio['numero_bloques'])
    if len(escenarios_simulados) != escenarios_esperados:
        return pd.DataFrame()
    del escenarios_simulados
    inicio = time.time()
    print(f"{'='*80}")
    print('Iniciando Analisis Estadistico de cargabilidades del caso base.')
    print(f"{'='*80}")
    logger.info('Filtrando elementos con una cargabilidad menor al 90%.')
    # Elementos con cargabilidad >= 90% 
    df_filtrado = (
        df_cargabilidades[df_cargabilidades['loading_percent'] >= LIMITE_CARGABILIDAD]
        .drop_duplicates(subset=['Componente'], keep='first'))
    lista_elementos = df_filtrado['Componente'].tolist()
    del df_filtrado
    #  Separar transformadores y líneas 
    lineas, trafos =  [], []
    for elemento in lista_elementos:
        if str(elemento[0:3]) != str(elemento[6:9]):
            lineas.append(elemento)
        else: 
            trafos.append(elemento)
    #  Filtrar trafos de generacion por barras en las que hay generacion
    trafos_filtrados = list(set(trafos_limpios) & set(trafos))
    elementos_candidatos = lineas + trafos_filtrados
    # Preparar DataFrames base 
    df_duraci = (
        df_duraci
        .drop_duplicates(subset=['Bloque'])
        .drop(columns=['Etapa','Serie'])
        .copy())
    df_cargabilidades = pd.merge(df_cargabilidades, df_duraci, on='Bloque', how='left')
    df_resultado = pd.merge(
        df_cargabilidades, df_flujos,
        on=['Fecha','Etapa','Bloque','Serie','Componente'],
        how='left')
    del df_flujos
    numero_series = datos_estudio['numero_series']
    horas_serie = df_duraci['duracion'].sum() * datos_estudio['numero_etapas']
    lista_series = np.arange(1, numero_series + 1, dtype=int)
    # Extraer subsets de net 
    net_line_data = net.line[['name','max_i_ka','from_bus']].copy()
    net_trafo_data = net.trafo[['name','sn_mva']].copy()
    net_bus_data = net.bus[['vn_kv']].copy()
    fp = float(parametros_red.Fp)
    #  Pre-filtrado por elemento 
    cols_cargab = ['Etapa','Serie','Bloque','Componente','loading_percent','duracion']
    slices_cargab = {
        nombre: df_cargabilidades[df_cargabilidades['Componente'] == nombre][cols_cargab].reset_index(drop=True)
        for nombre in elementos_candidatos}
    slices_result = {
        nombre: df_resultado[df_resultado['Componente'] == nombre].reset_index(drop=True)
        for nombre in elementos_candidatos
    } if generar_graficas else {nombre: pd.DataFrame() for nombre in elementos_candidatos}
    del df_cargabilidades, df_resultado
    # Pool de workers 
    logger.info(f'Elementos criticos identificados (Condicion n) : {len(elementos_candidatos)}.')
    logger.info(f'Iniciando analisis estadistico (MP) para {len(elementos_candidatos)} elementos entre {nucleos} nucleos. ')
    args_fijos = dict(df_duraci = df_duraci, horas_serie = horas_serie, lista_percentiles = PERCENTILES,
        lista_series = lista_series, fp = fp, net_line_data = net_line_data, net_trafo_data = net_trafo_data,
        net_bus_data = net_bus_data, generar_graficas = generar_graficas, ruta_graficas = ruta_graficas)
    resultados = []
    with ProcessPoolExecutor(max_workers=nucleos) as executor:
        futures = {
            executor.submit(
                _procesar_elemento_worker,
                nombre,
                slices_cargab[nombre],
                slices_result[nombre],
                **args_fijos,
            ): nombre
            for nombre in elementos_candidatos}
        with tqdm(total=len(futures), file=sys.__stdout__, desc="Procesando elementos", unit="elem") as pbar:
            for future in as_completed(futures):
                nombre = futures[future]
                try:
                    resultado = future.result()
                    resultados.append(resultado)
                    pbar.set_postfix_str(f"{nombre}")
                except Exception as e:
                    logger.error(f"Error procesando {nombre}: {e}")
                    pbar.set_postfix_str(f"{nombre}")
                finally:
                    pbar.update(1)
    columnas = ['Nombre_Componente','P_0.1%','P_1%','P_5%','Cargabilidad_Max','Capacidad_Nominal_MW']
    df_analisis = (pd.DataFrame(resultados, columns=columnas).sort_values(by='P_1%', ascending=False)
                .reset_index(drop=True))
    nombre_archivo = 'Reporte_analisis_condicion_n.csv'
    df_analisis.to_csv(Path(rta_cn) / nombre_archivo, index=False)
    if generar_graficas:
        logger.info('Se generaron las graficas correctamente.')
    logger.info(f"Tiempo total: {(time.time()-inicio)/60:.2f} minutos")
    print(f"{'='*80}")
    return df_analisis

def analisis_contingencias(indice_severidad:pd.DataFrame, ruta_contingencias, ruta_Pip, config_sim_contingencias):
    print(f"{'='*80}")
    print('Iniciando Analisis Estadistico de indices de severidad (Contingencias).')
    print(f"{'='*80}")
    if indice_severidad.empty:
        logger.info('No se realizo el alcance completo, por lo que no se puede hacer el analisis de inidces de severidad.')
        print(f"{'='*80}")
        return pd.DataFrame(), pd.DataFrame() 
    indice_severidad = indice_severidad.sort_values(by='Ind_Sev', ascending=False).reset_index(drop=True)
    contingencias = indice_severidad['contingencia'].tolist()
    pips = {}
    for contingencia in contingencias:
        try:
            nombre_pip = f'PIp_{contingencia}.csv'
            pips[contingencia] = pd.read_csv((Path(ruta_Pip)/nombre_pip))
        except:
            logger.warning(f'No se encontro: {nombre_pip} en la carpeta de resultados.')
            continue
    def convertir(escenario_ind):
        etapa, serie, bloque = [int(x) for x in escenario_ind]
        escenario = f'E_{etapa}_S_{serie}_B_{bloque}'
        return escenario
    esc_pip, graf_pip, esc_nus, graf_nus, mx = [], [], [], [], []
    for llave, valor in pips.items():
        contingencia = llave
        df = valor[['Etapa','Serie','Bloque','PIp_Total', 'num_sobrecargas', 'max_cargab']].copy()
        df = df.set_index(['Etapa','Serie','Bloque'])
        # maxima cargabilidad
        max_cargab = df['max_cargab'].max()
        mx.append(max_cargab)
        # Escenarios
        id_pip = df['PIp_Total'].idxmax()
        graf_pip.append(id_pip)
        pip = convertir(id_pip)
        esc_pip.append(pip)
        id_nus = df['num_sobrecargas'].idxmax()
        graf_nus.append(id_nus)
        nus = convertir(id_nus)
        esc_nus.append(nus)
    indice_severidad['Esc_pip_mx'] = esc_pip
    indice_severidad['Esc_max_num_sbc'] = esc_nus
    indice_severidad['max_cargab'] = mx
    # para el reporte ordenamos y limpiamos nombres (no afecta a los demas ya que se crea una copia y se modifica la copia no el 
    # df de indice de severidad original)
    archivo_severidad = ruta_contingencias / f'Ranking(cont)_{config_sim_contingencias.nombre_estudio}.csv'
    df_is_ordenado = indice_severidad[['contingencia', 'Ind_Sev','max', 'Esc_pip_mx', 'max_cargab','Esc_max_num_sbc']]
    df_is_ordenado.rename(columns={'contingencia':'Contingencia','max':'PIp_max', 'max_cargab':'Max_cargab_generada',
                                'Esc_max_num_sbc':'Esc_mayor_num_sbc'}, inplace = True)
    df_is_ordenado.to_csv(archivo_severidad, index=False)
    df_is = indice_severidad.query('Ind_Sev >= 1').copy()
    logger.info(f'Las 5 contingencias mas severas son:\n{df_is.head(5)}')
    print(f'{'='*80}')
    # Para el graficador
    df_is = indice_severidad.query('Ind_Sev >= 1').copy()
    cont_crit = df_is['contingencia'].size
    del df_is
    top_contingencias = {'contingencias': contingencias[:cont_crit], 'escenario_pip': graf_pip[:cont_crit], 'escenario_nus':graf_nus[:cont_crit]}
    return top_contingencias, df_is_ordenado

def percentiles_cb(df_cargabilidades: pd.DataFrame, nombre: str, numero_series: int, horas_serie: int):
    df = df_cargabilidades[df_cargabilidades['Componente'] == nombre].copy()
    resultados_por_componente = [] # Lista de resultados general
    for serie in range(1, numero_series + 1, 1):
        df_temporal = (
            df[df['Serie'] == serie]
            .sort_values(by=['loading_percent'], ascending=False).copy())
        df_temporal['tiempo_acumulado'] = df_temporal['duracion'].cumsum()
        df_temporal['tiempo_porcentual'] = (df_temporal['tiempo_acumulado'] * 100) / (horas_serie)
        resultados_serie = [] # Lista de resultados por serie
        for tiempo_percentil in PERCENTILES_REF:
            df_aux = df_temporal[df_temporal['tiempo_porcentual'] > tiempo_percentil]
            valor_percentil = df_aux['loading_percent'].max()
            resultados_serie.append(valor_percentil)
        resultados_por_componente.append((serie, *resultados_serie))
    df_estadisticas = pd.DataFrame(resultados_por_componente, columns=['Serie', 'valor_p1', 'valor_p2'])
    valor_prom_p1 = df_estadisticas['valor_p1'].mean()
    valor_prom_p2 = df_estadisticas['valor_p2'].mean()
    return (valor_prom_p1, valor_prom_p2)

def constantes(df_duraci: dict, etapas):
    df_duracion = (df_duraci.drop_duplicates(subset=['Bloque']).drop(columns=['Etapa','Serie']).copy()) # Hrs/bloq
    horas_serie = df_duracion['duracion'].sum() * etapas
    return horas_serie

def indice_cond_n(df: pd.DataFrame, df_duraci:pd.DataFrame, expon_n: int, horas_serie: int):
    # CALCULO PIP POR ESCENARIO
    df_cargabilidades = df[['Etapa', 'Bloque', 'Serie', 'loading_percent']].copy()
    df_cargabilidades['Sobrecarga'] = df_cargabilidades['loading_percent'] >= 100
    df_cargabilidades['PIp_Ind'] = (df_cargabilidades['loading_percent'] / 100) ** expon_n
    df_suma_pip = df_cargabilidades.groupby(['Etapa', 'Bloque', 'Serie'])['PIp_Ind'].sum().reset_index()
    df_suma_pip['PIp_Total'] = df_suma_pip['PIp_Ind'] ** (1/expon_n)
    # NUMERO DE VIOLACIONES
    df_conteo = df_cargabilidades.groupby(['Etapa', 'Bloque', 'Serie'])['Sobrecarga'].sum().reset_index()
    df_conteo = df_conteo.rename(columns={'Sobrecarga': 'num_sobrecargas'})
    numero_violaciones = df_conteo['num_sobrecargas'].sum()
    # CALCULO DEL IS
    df_duracion = (df_duraci.drop_duplicates(subset=['Bloque']).drop(columns=['Etapa','Serie']).copy()) # Hrs/bloq
    df_is = pd.merge(df_suma_pip, df_duracion, how='left', on='Bloque')
    df_is['Ponderado'] = df_is['PIp_Total'] * df_is['duracion']
    res_series = df_is.groupby('Serie')['Ponderado'].sum().reset_index()
    res_series['IS'] = res_series['Ponderado'] / horas_serie
    ind_sev = res_series['IS'].mean()
    return [ind_sev, numero_violaciones]

def graf_flujos(nombre : str, df : pd.DataFrame, ruta_graficas: str|Path, anio: int, id: str):
    fig, ax = plt.subplots(figsize=(ANCHO, ALTO))
    x_flujo = np.sort(df['Transferencia_Total'].values)
    n_puntos = len(x_flujo)
    eje_y_prob = np.linspace(0, 100, n_puntos)
    percentil_0 = x_flujo.min()
    percentil_003 = np.percentile(x_flujo, PERCENTIL_INFERIOR * 100)
    percentil_0997 = np.percentile(x_flujo, PERCENTIL_SUPERIOR * 100)
    percentil_100 = x_flujo.max()
    ax.fill_between(x_flujo, eje_y_prob, color='skyblue', alpha=0.8)
    ax.plot(x_flujo, eje_y_prob, color='skyblue', linewidth=1.5)
    ax.axvline(x=percentil_0, color='blue', linestyle='--', linewidth=1, label=f'P_0% = {percentil_0:.1f} MW')
    ax.axvline(x=percentil_003, color='red', linestyle='--', linewidth=1, label=f'P_0.03% = {percentil_003:.1f} MW')
    ax.axvline(x=percentil_0997, color='red', linestyle='--', linewidth=1, label=f'P_99.7% = {percentil_0997:.1f} MW')
    ax.axvline(x=percentil_100, color='blue', linestyle='--', linewidth=1, label=f'P_100% = {percentil_100:.1f} MW')
    ax.legend(title="Percentiles Criticos", loc='upper left', fontsize=7, shadow=True)
    valor_min = math.floor(x_flujo.min()) * 0.9
    valor_max = math.ceil(x_flujo.max()) * 1.1
    ax.set_xlim(valor_min, valor_max)
    ax.set_ylim(0, 100)
    tit = f'Probabilidad Acumulada de Flujo: {nombre}' if id == 'flujos' else f'Probabilidad Acumulada para {nombre}'
    sub_t = f'Todas las series simuladas para el año: {anio}'
    x = 'Transferencia Total [MW]' if id == 'flujos' else 'Total [MW]'
    nombre_fig = f'Flujo_{nombre}_{anio}.png' if id == 'flujos' else f'Probabilidad_acumulada_[{nombre} - {anio}].png'
    aplicar_tema_light(ax=ax, titulo=tit, subtitulo=sub_t, xlabel=x, ylabel='Probabilidad [%]')
    ax.set_yticks(range(0, 101, 10))
    plt.tight_layout()
    plt.savefig(Path(ruta_graficas)/f"{nombre_fig}", dpi=DPI)
    plt.close()

def analisis_escenarios(df_desp_TH: pd.DataFrame, df_desp_ren: pd.DataFrame, df_demanda: pd.DataFrame,
                        rta_esc: str|Path, lista_years: list, df_fechas: pd.DataFrame):
    print(f"{'='*80}")
    print('ANALISIS DE ESCENARIOS CRITICOS (P1).')
    print(f"{'='*80}")
    
    etapas, series, bloques, valor_mw, tiempo, escenarios_criticos = [], [], [], [], [], []
    # Funciones auxiliares
    def years(df_viejo: pd.DataFrame, df_fechas: pd.DataFrame):
        if df_viejo.empty:
            df = pd.DataFrame()
        else:
            df = df_viejo.copy()
            df.reset_index(inplace= True)
            df = pd.merge(df, df_fechas, on='Etapa', how='left')
            df['años'] = df['Fecha'].dt.year
            df.set_index(['Etapa', 'Serie', 'Bloque'], inplace=True)
            df.drop(columns=['Fecha'], inplace = True)
        return df
    def analisis_df(df: pd.DataFrame, year: int, nombre_df: str):
        val_q_sup = df['Transferencia_Total'].quantile(q=PERCENTIL_SUPERIOR, interpolation='nearest')
        val_q_inf = df['Transferencia_Total'].quantile(q=PERCENTIL_INFERIOR, interpolation='nearest')
        valor_mw.append(val_q_sup)
        valor_mw.append(val_q_inf)
        tiempo.append(year)
        tiempo.append(year)
        escenarios_criticos.append(f"Max_{nombre_df}_{year}")
        escenarios_criticos.append(f"Min_{nombre_df}_{year}")
        idx_sup = (df['Transferencia_Total'] - val_q_sup).abs().idxmin()
        idx_inf = (df['Transferencia_Total'] - val_q_inf).abs().idxmin()
        puntos_interes = [idx_sup, idx_inf]
        for idx in puntos_interes:
            etapa_val, serie_val, bloque_val = idx
            etapas.append(int(etapa_val))
            series.append(int(serie_val))
            bloques.append(int(bloque_val))

    # Inicio del procesamiento de escenarios criticos
    df_dem = years(df_demanda, df_fechas)
    df_renovables = years(df_desp_ren, df_fechas)
    df_sincronas = years(df_desp_TH, df_fechas)
    if df_renovables.empty:
        dict_df = {'Demanda': df_dem, 'Generacion_Sincrona': df_sincronas}
        logger.info('No se cuenta con generacion renovable en el sistema.')
    else:
        dict_df = {'Demanda': df_dem, 'Generacion_Sincrona': df_sincronas, 'Generacion_Variable': df_renovables}
    rutas_anio = {}
    for id, year in enumerate(lista_years, start = 1):
        ruta_yyyy, ruta_diagramas, ruta_graficas = carpetas_op3_individual(rta_esc, id, year)
        rutas_anio[str(year)] = [ruta_yyyy, ruta_diagramas, ruta_graficas]
        for nombre, df in dict_df.items():
            df_aux = df[df['años'] == year].copy()
            df_aux.drop(columns=['años'], inplace=True)
            df_aux['Transferencia_Total'] = df_aux.sum(axis=1)
            analisis_df(df_aux, year, nombre)
            graf_flujos(nombre, df_aux, ruta_graficas, year, id='DD')
            logger.info(f'Analisis de {nombre} para el año {year} terminado.')
            del df_aux
    df_escenarios = pd.DataFrame()
    df_escenarios['Escenarios criticos'] = escenarios_criticos
    df_escenarios['Etapa'] = etapas
    df_escenarios['Serie'] = series
    df_escenarios['Bloque'] = bloques
    df_escenarios['MW'] = valor_mw
    df_escenarios['Año'] = tiempo
    lista_escenarios = list(zip(etapas, series, bloques, tiempo, escenarios_criticos))
    ruta_salida = Path(rta_esc) / 'Reporte_escenarios_criticos_p1.csv'
    logger.info('Reporte de escenarios criticos generado correctamente')
    df_escenarios.to_csv(ruta_salida, index=False)
    print(f"{'-'*80}")
    return rutas_anio, lista_escenarios, df_escenarios

def analisis_flujos(df_flujos: pd.DataFrame, interconexiones: dict, rta_esc: str|Path,
                    rutas_anio: dict, lista_years: list):
    print(f"{'='*80}")
    print('ANALISIS DE ESCENARIOS CRITICOS (P2).')
    print(f"{'='*80}")
    lista_res = []
    for nombre, elementos in interconexiones.items():
        if isinstance(elementos, list):
            lista_sucia = set(elementos)
        else:
            lista_sucia = set(elementos.split(','))
        lista_limpia = [x.strip().upper() for x in lista_sucia]
        nombre_interfaz = "_".join(lista_limpia) # Identificador visual del corredor
        try:
            # Filtrado de los elementos de la interfaz
            df_aux = df_flujos[df_flujos['Componente'].isin(lista_limpia)].copy()
            df_aux['Fecha'] = pd.to_datetime(df_aux['Fecha'])
            for anio in lista_years:
                # filtramos cada año seleccionado por el usuario
                df_aux['years'] = df_aux['Fecha'].dt.year
                df = df_aux[df_aux['years'] == anio].copy()
                # Agrupamos por escenario para obtener la transferencia TOTAL
                df_escenarios = df.groupby(['Etapa', 'Bloque', 'Serie']).agg(
                    Transferencia_Total=('Flujo_mw', 'sum')
                ).reset_index()
                df_escenarios.sort_values(by='Transferencia_Total', inplace=True)
                # graficamos 
                id = 'Flujos'
                ruta = Path(rutas_anio[str(anio)][2])
                graf_flujos(nombre, df_escenarios, ruta, anio, id)
                # Identificamos escenarios extremos usamos Percetiles
                transferencia = df_escenarios['Transferencia_Total'].copy()
                val_q_sup = transferencia.quantile(q=PERCENTIL_SUPERIOR, interpolation='nearest')
                val_q_inf = transferencia.quantile(q=PERCENTIL_INFERIOR, interpolation='nearest')
                idx_sup = (transferencia - val_q_sup).abs().idxmin()
                idx_inf = (transferencia - val_q_inf).abs().idxmin()
                extremos = [('MAX', idx_sup), ('MIN', idx_inf)]
                for tipo, idx in extremos:
                    fila_esc = df_escenarios.loc[idx]
                    # Buscamos los valores de cada linea durante ese escenario
                    escenario_mask = (
                        (df['Etapa'] == fila_esc['Etapa']) & 
                        (df['Bloque'] == fila_esc['Bloque']) & 
                        (df['Serie'] == fila_esc['Serie']))
                    df_detalle = df[escenario_mask]
                    # Construimos la fila del reporte
                    registro = {
                        'Interconexion': nombre,
                        'Lectura': tipo,
                        'Año': anio,
                        'Etapa': fila_esc['Etapa'],
                        'Serie': fila_esc['Serie'],
                        'Bloque': fila_esc['Bloque'],
                        'Total_MW': fila_esc['Transferencia_Total'],
                        'Elementos': nombre_interfaz,}
                    for elemento in lista_limpia:
                        valor_linea = df_detalle[df_detalle['Componente'].str.upper() == elemento]['Flujo_mw']
                        registro[elemento] = valor_linea.iloc[0] if not valor_linea.empty else 0
                    lista_res.append(registro)
                logger.info(f'Se concluyo el analisis para {nombre} [{anio}].')
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.warning(f'No se encontro el elemento: {e}. Verifique los nombres en la lista.')
            continue
    # Generacion del DataFrame final
    df_res = pd.DataFrame(lista_res)
    df_res.to_csv((Path(rta_esc)/'Reporte_escenarios_criticos_p2.csv'), index=False, encoding='utf-8')
    logger.info('El reporte de escenarios criticos (P2) se genero correctamente.')
    # Extraemos los escenarios para los diagramas
    lista_nombre = df_res['Interconexion'].to_list()
    lista_identificador = df_res['Lectura'].to_list()
    lista_etapas = df_res['Etapa'].to_list()
    lista_series = df_res['Serie'].to_list()
    lista_bloques = df_res['Bloque'].to_list()
    lista_anios = df_res['Año'].to_list()
    lista_id = list(zip(lista_nombre, lista_identificador, lista_anios))
    lista_esc = list(zip(lista_etapas, lista_series, lista_bloques))
    lista_completa = list(zip(lista_id, lista_esc))
    print(f"{'-'*80}")
    return lista_completa, df_res