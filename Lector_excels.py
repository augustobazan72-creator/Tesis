import pandas as pd
import numpy as np
from pathlib import Path
import logging
import os
import glob
from Configuracion_inicial import input_log

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

# FUNCION DE CONVERSION A LISTAS
def convertir_a_lista(lista_sucia:str)-> list:
    if lista_sucia:
        lista_limpia = []
        for elemento in lista_sucia:
            lista = [componente.strip().upper() for componente in elemento.split(',')]
            lista_limpia.extend(lista)
        return lista_limpia
    else:
        return []

# --- LECTURA Y LIMPIEZA EXCEL DE REFUERZOS ---
def lectura_excel_refuerzos(ruta, net) -> pd.DataFrame:
    esquema_ternas = {'LST': 1, 'LDT': 2, 'LDTI': 1, 'CDT': 1}
    # LEEMOS EL DF
    logger.info(f'Iniciando la lectura del archivo: "{ruta.name}".')
    encabezados = [
        'Nombre_refuerzo', 'id_bus_from', 'id_bus_to', 'Alternativa', 'Cartera', 'Tipo', 
        'sn[MVAR/km]', 'P[MW]', 'r[ohm/km]', 'x[ohm/km]', 'length_km', 'Elementos a monitorear',
        'En servicio', 'Latitud', 'Longitud'
    ]
    try:
        df = pd.read_excel(ruta, header=0, names=encabezados)
    except:
        e1=f'El archivo {ruta.name} no ha podido ser leido.'
        e2=f'Revise que el archivo {ruta.name} este en el formato adecuado.'
        logger.error(e1)
        raise ValueError(e2)
    # LIMPIAMOS LOS DATOS
    df['Nombre_refuerzo'] = df['Nombre_refuerzo'].str.upper().str.strip()
    df['Tipo'] = df['Tipo'].str.upper().str.strip()
    df['N.Ternas'] = df['Tipo'].map(esquema_ternas)
    esquema = {
        'Nombre_refuerzo': 'object',
        'id_bus_from': 'int64',
        'id_bus_to': 'int64',
        'Alternativa': 'object',
        'Cartera': 'object',
        'Tipo': 'object',
        'sn[MVAR/km]': 'float64',
        'P[MW]': 'float64',
        'r[ohm/km]': 'float64',
        'x[ohm/km]': 'float64',
        'length_km': 'float64',
        'Elementos a monitorear': 'object', 
        'En servicio': 'int64', 
        'Latitud': 'float64',
        'Longitud': 'float64',
        'N.Ternas': 'int64'
    }
    columnas_con_cero_por_defecto = ['r[ohm/km]', 'sn[MVAR/km]', 'length_km', 'N.Ternas', 'En servicio']
    for col, tipo_esperado in esquema.items():
        if tipo_esperado in ['int64', 'float64']:
            df[col] = pd.to_numeric(df[col], errors='coerce') 
            if df[col].isna().any(): 
                if col in columnas_con_cero_por_defecto:
                    n_nan = df[col].isna().sum()
                    df[col] = df[col].fillna(0.0)
                    logger.info(f"'{col}': Se corrigieron {n_nan} valores nulos con 0.0")
                else:
                    n_nan = df[col].isna().sum()
                    logger.info(f"'{col}': Se detectaron {n_nan} celdas vacias. Se mantendran como nulas.")
            if tipo_esperado == 'int64':
                df[col] = df[col].astype('Int64')
            else:
                df[col] = df[col].astype('float64')
        else:
            continue
    
    # VALIDAMOS BUSES EN EXCEL
    buses_validos = set(net.bus.index)
    buses_en_excel_from = set(df['id_bus_from'].dropna().unique())
    buses_en_excel_to = set(df['id_bus_to'].dropna().unique())
    buses_en_excel = buses_en_excel_from.union(buses_en_excel_to)
    buses_en_excel = {int(x) for x in buses_en_excel}
    error = buses_en_excel - buses_validos
    if len(error) != 0:
        e = f'Los siguientes IDs de bus fueron escritos en el Excel pero no existen en la red actual: {list(error)}'
        logger.error(e)
        raise ValueError(f"id de buses fuera de los existentes.")
    logger.info('Se realizo la lectura y validacion de buses exitosamente.')
    
    # VALIDAMOS DATOS (NO NEGATIVOS)
    for indice, fila in df.iterrows():
        if fila['Tipo'] not in ['BARRA']:
            if fila ['En servicio'] == 1:
                continue
            else:
                for col in ['sn[MVAR/km]', 'r[ohm/km]', 'length_km']:
                    criterio = fila[col] >= 0
                    if criterio:
                        continue
                    else:
                        e = f'La columna {col} contiene datos negativos en la posicion {indice}.'
                        logger.error(e)
                        raise ValueError(f'Corrija el dato ingresado (No puede ser negativo).')
                for col in ['P[MW]', 'x[ohm/km]']:
                    criterio = fila[col] > 0
                    if criterio:
                        continue
                    else:
                        e = f'La columna {col} contiene datos negativos en la posicion {indice}.'
                        logger.error(e)
                        raise ValueError(f'Corrija el dato ingresado (No puede ser negativo, cero o ausente).')
    logger.info('Se realizo la lectura y validacion de parametros electricos exitosamente.')
    
    # VALIDAMOS ELEMENTOS DE MONITOREO
    lista_monitoreo = df['Elementos a monitorear'].dropna().tolist()
    lista_monitoreo = set(convertir_a_lista(lista_monitoreo))
    lista_red = set(net.line['name'].tolist() + net.trafo['name'].tolist())
    comparacion = lista_monitoreo.difference(lista_red)
    if len(comparacion)>0:
        logger.error(f'Los elmenetos de monitoreo {comparacion} no existen en la red.')
        e = 'Elementos de monitoreo inexistentes en la red'
        raise ValueError (e)
    logger.info('Se realizo la validacion de los elementos de monitoreo exitosamente.')
    print(f"{'-'*60}")
    
    return df

# CARGAR DISTANCIAS DESDE UN EXCEL
def distancias_usuario(ruta_distancias, net, df_mline) -> pd.DataFrame:
    logger.info('Actualizando la red base.')
    try:
        encabezados = ['nombre_linea', 'distancia_km']
        df_distancias = pd.read_excel(ruta_distancias, header=0, names=encabezados)
    except:
        e1=f'El archivo {ruta_distancias.name} no ha podido ser leido.'
        e2=f'Revise que el archivo {ruta_distancias.name} este en el formato adecuado.'
        logger.error(e1)
        raise ValueError(e2)
    df_distancias['nombre_linea'] = df_distancias['nombre_linea'].astype(str).str.upper().str.strip()
    lineas_excel = df_distancias['nombre_linea'].tolist()
    nombres_red_limpios = net.line['name'].tolist()
    for linea in lineas_excel:
        if linea not in nombres_red_limpios:
            logger.error(f'La linea "{linea}" no existe en la red. Revise la ortografía.')
            raise ValueError(f"No encontrado en net.line: {linea}")
    for lon in df_distancias['distancia_km']:
        if pd.isna(lon):
            logger.error('Existen lineas sin distancias, revisar el archivo excel, se les asignara un valor de 1 [km].')
            continue
        try:
            float(lon)
        except (ValueError, TypeError):
            logger.error(f'La distancia "{lon}" no es un numero valido.')
            raise ValueError(f"Distancia no numérica: {lon}")
    mapa_distancias = df_distancias.set_index('nombre_linea')['distancia_km'].to_dict()
    net.line['length_km'] = net.line['name'].map(mapa_distancias)
    net.line['length_km'] = net.line['length_km'].fillna(1)
    net.line['r_ohm_per_km'] /= net.line['length_km']
    net.line['x_ohm_per_km'] /= net.line['length_km']
    net.line['c_nf_per_km'] /= net.line['length_km']
    if not df_mline.empty:
        logger.info('Actualizando las modificaciones futuras de los circuitos.')
        df_mline = pd.merge(df_mline, df_distancias, how = 'left', left_on = 'nombre_componente', right_on = 'nombre_linea')
        n_sin_match = df_mline['distancia_km'].isna().sum()
        if n_sin_match > 0:
            logger.warning(f'{n_sin_match} circuito(s) en df_mline no tienen distancia en el archivo Excel. Sus parametros quedaran como NaN.')
        df_mline['r_(ohm/km)'] /= df_mline['distancia_km']
        df_mline['x_(ohm/km)'] /= df_mline['distancia_km']
        df_mline['f_(nF/km)'] /= df_mline['distancia_km']
        df_mline = df_mline[['nombre_componente', 'id_bus_origen', 'id_bus_destino', 'Fecha', 'Etapa', 'status',
                                    'r_(ohm/km)', 'x_(ohm/km)', 'f_(nF/km)', 'I_mx_kA']]
        print('Todas las longitudes se actualizaron correctamente')
        print(f'{'='*60}\n')
        del df_distancias
    else:
        logger.info('No se actualizaron distancias en modificaciones futuras.')
        logger.warning('No se cuentan con modificaiones futuras en las lineas (mcirc.csv -> vacio).')
    return df_mline

def lector_costos(ruta_costos: str|Path)->tuple[pd.DataFrame, pd.DataFrame]:
    print(f'{'-'*80}')
    try:
        df_costos_ind = pd.read_excel(Path(ruta_costos), sheet_name = 0)
        df_costos_reactores = pd.read_excel(Path(ruta_costos), sheet_name = 1)
    except:
        e='No se pudo leer los costos, revise qeue el excel cunpla con las indicaciones.'
        logger.error(e)
        raise ValueError('El error se encuentra en el archivo excel.')
    
    # VALIDACION Y LIMPIEZA
    for col in df_costos_ind.columns.tolist()[1:]:
        df_costos_ind[col] = pd.to_numeric(df_costos_ind[col], errors='coerce')
        n_nan = df_costos_ind[col].isna().sum()
        df_costos_ind[col] = df_costos_ind[col].fillna(0.0)
        logger.info(f"'{col}': Se corrigieron {n_nan} valores nulos con 0.0")
        negativos = (df_costos_ind[col] >= 0).all()
        if negativos:
            continue
        else:
            e=f'La columna {col} tiene valores negativos [Costos Lineas/Trafos]'
            logger.error(e)
            raise ValueError('No existen costos negativos (Revise el excel de costos).')
    for col in df_costos_reactores.columns.tolist()[1:]:
        df_costos_reactores[col] = pd.to_numeric(df_costos_reactores[col], errors='coerce')
        n_nan = df_costos_reactores[col].isna().sum()
        df_costos_reactores[col] = df_costos_reactores[col].fillna(0.0)
        logger.info(f"'{col}': Se corrigieron {n_nan} valores nulos con 0.0")
        negativos = (df_costos_reactores[col] >= 0).all()
        if negativos:
            continue
        else:
            e=f'La columna {col} tiene valores negativos [Costos Reactores]'
            logger.error(e)
            raise ValueError('No existen costos negativos (Revise el excel de costos).')
    df_costos_reactores = df_costos_reactores.sort_values('Reactor_mvar')
    logger.info('Se realizo l validacion de costos (Lineas/Reactores/Trafos) correctamente.')
    print(f'{'-'*80}')
    return (df_costos_ind, df_costos_reactores)

def validar_flujos(df, datos_estudio, net, nombre):
    # Parametros de referencia
    etapas_ref = np.arange(1, datos_estudio['numero_etapas']+1, 1, dtype=int)
    series_ref = np.arange(1, datos_estudio['numero_series']+1, 1, dtype=int)
    bloques_ref = np.arange(1, datos_estudio['numero_bloques']+1, 1, dtype=int)
    num_datos_ref = datos_estudio['numero_etapas'] * datos_estudio['numero_series'] * datos_estudio['numero_bloques']
    lista_elementos_ref = set(net.line['name'].tolist() + net.trafo['name'].tolist())
    # Parametros del df
    etapas_df = set(df['Etapa'].tolist())
    series_df = set(df['Serie'].tolist())
    bloques_df = set(df['Bloque'].tolist())
    num_datos_df = len(df)
    lista_elementos_df = set(df['Componente'].tolist())
    # Validaciones
    if not len(etapas_ref) == len(etapas_df):
        logger.warning(f'Referencia: [{len(etapas_ref)}] - dataframe_leido: [{len(etapas_df)}]')
        e = ('El archivo leido no cuenta con el numero de etapas correcto.')
        raise ValueError(e)
    if not len(series_ref) == len(series_df):
        logger.warning(f'Referencia: [{len(series_ref)}] - dataframe_leido: [{len(series_df)}]')
        e = ('El archivo leido no cuenta con el numero de series correcto.')
        raise ValueError(e)
    if not len(bloques_ref) == len(bloques_df):
        logger.warning(f'Referencia: [{len(bloques_ref)}] - dataframe_leido: [{len(bloques_df)}]')
        e = ('El archivo leido no cuenta con el numero de bloques correcto.')
        raise ValueError(e)
    if not (num_datos_ref*len(lista_elementos_ref)) == num_datos_df:
        logger.warning(f'Referencia: [{num_datos_ref}] - dataframe_leido: [{num_datos_df}]')
        e = ('El archivo leido no cuenta con el numero de escenarios correcto.')
        raise ValueError(e)
    if not lista_elementos_ref.issubset(lista_elementos_df):
        elementos_faltantes = lista_elementos_ref - lista_elementos_df
        logger.warning(f'Referencia: [{len(lista_elementos_ref)}] - dataframe_leido: [{len(lista_elementos_df)}]')
        logger.warning(f'Los elementos faltanrtes son: {elementos_faltantes}')
        e = ('El archivo leido no cuenta con el numero de elementos correcto.')
        raise ValueError(e)
    logger.info(f'Se valido correctamente el archivo de {nombre}.')

def lectura_flujos(ruta_estudio, datos_estudio, net, cargabilidades:bool=False):
    print(f'{'='*80}')
    print(f'LECTURA Y VALIDACION DEL ARCHIVO DE FLUJOS')
    print(f'{'='*80}')
    # PATRONES DE CARPETAS
    ruta_estudio = Path(ruta_estudio)
    ruta_condicion_n = ruta_estudio / "1. Condicion_n"
    patron_condicion_n = os.path.join(ruta_condicion_n, "LF(cond-n)_*.csv")
    # BUSQUEDA DE ARCHIVOS
    # CONDICION N
    archivos_encontrados = glob.glob(patron_condicion_n)
    if archivos_encontrados:
        ruta_archivo = archivos_encontrados[0]
        df_cargab_cb = pd.read_csv(ruta_archivo)
        if not cargabilidades:
            df_flujo = df_cargab_cb[['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente', 'Flujo_mw']].copy()
            logger.info(f"Se encontro el archivo: {os.path.basename(ruta_archivo)}")
            validar_flujos(df_flujo, datos_estudio, net,  nombre ='Flujos de potencia')
            print(f'{'='*80}')
            return None, df_flujo
        else:
            df_flujo = df_cargab_cb[['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente', 'Flujo_mw']].copy()
            df_cargabilidades = df_cargab_cb[['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente', 'loading_percent']].copy()
            logger.info(f"Se encontro el archivo: {os.path.basename(ruta_archivo)}")
            validar_flujos(df_flujo, datos_estudio, net, nombre ='Flujos de potencia')
            validar_flujos(df_cargabilidades, datos_estudio, net, nombre ='Cargabilidades')
            print(f'{'='*80}')
            return df_cargabilidades, df_flujo
        
    else:
        e = "No se encontro ningun archivo que empiece con: LF(cond-n)_*"
        df_cargab_cb = pd.DataFrame()
        logger.error(e)
    
    if df_cargab_cb.empty :
        e = f'La carpeta {ruta_estudio} no cuenta con el diagnostico de la red de transmision.'
        raise ValueError (e)

def lectura_escenarios(ruta_escenarios):
    print(f'{'='*80}')
    print(f'LECTURA DE ESCENARIOS CRITICOS')
    print(f'{'='*80}')
    # RUTAS DE CARPETA DE ESCENARIOS
    escenarios_p1 = Path(ruta_escenarios)/'Reporte_escenarios_criticos_p1.csv'
    escenarios_p2 = Path(ruta_escenarios)/'Reporte_escenarios_criticos_p2.csv'
    # PARA LA NORMLIZACION DE COLUMNAS
    enteros = {'Etapa': int, 'Serie': int, 'Bloque': int, 'Año': int}
    # ESCENARIOS CRITICOS P1
    try:
        encabezados = ['Escenarios criticos', 'Etapa', 'Serie', 'Serie', 'Bloque', 'Año']
        df_p1 = pd.read_csv(escenarios_p1, usecols = encabezados)
        df_p1 = df_p1.astype(enteros)
        df_p1['Escenarios criticos'] = df_p1['Escenarios criticos'].astype(str)
        logger.info('Se leyo correctamente el archivo "Reporte_escenarios_criticos_p1.csv".')
    except:
        logger.warning('No se leyo correctamente el archivo "Reporte_escenarios_criticos_p1.csv".')
        logger.info('Revise que se haya ingresado una carpeta con el analisis de escenarios criticos ' + 
                    'realizado correctamente.')
        df_p1 = pd.DataFrame()
    
    # ESCENARIOS CRITICOS P2
    strings = {'Interconexion' : str, 'Lectura' : str}
    encabezados = ['Interconexion', 'Lectura', 'Año', 'Etapa', 'Serie', 'Bloque']
    try:
        df_p2 = pd.read_csv(escenarios_p2, usecols = encabezados, encoding = 'utf-8')
        df_p2['Escenarios criticos'] = df_p2['Interconexion'] +'_'+ df_p2['Lectura'] +'_'+ df_p2['Año'].astype(str)
        df_p2 = df_p2.astype(enteros)
        df_p2 = df_p2.astype(strings)
        logger.info('Se leyo correctamente el archivo "Reporte_escenarios_criticos_p2.csv".')
    except:
        logger.warning('No se leyo correctamente el archivo "Reporte_escenarios_criticos_p2.csv".')
        logger.info('Revise que se haya ingresado una carpeta con el analisis de escenarios criticos' + 
                    'realizado correctamente.')
        df_p2 = pd.DataFrame()
    print(f'{'='*80}')
    return df_p1, df_p2

def lector_pareo():
    while True:
        ruta = input_log('Ingrese la ruta del archivo. xlsx que continenel pareo:\n')
        ruta = ruta.replace('"', '').replace("'", "")
        if not Path(ruta).is_file():
            e = 'La ruta ingresada no es un archivo, ingrese nuevamente la direccion del archivo.'
            logger.warning(e)
            print('-'*80)
        else:
            break
    try:
        pareo_syn = pd.read_excel(Path(ruta), sheet_name= "Gen. Syn.", dtype= str)
        pareo_sta = pd.read_excel(Path(ruta), sheet_name= "Gen. Sta.", dtype= str)
        pareo_cargas = pd.read_excel(Path(ruta), sheet_name= "Cargas", dtype= str)
    except:
        e_1 = 'Hubo un problema al leer las hojas del archivo excel.'
        e_2 = 'Revise que el archivo sea un xslx, los nombres de las hojas y los encabezados.'
        logger.error(e_1)
        logger.info(e_2)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # FUNCION DE LIMPIEZA
    def funcion_limpieza(df):
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].str.strip()
        return df
    pareo_syn = funcion_limpieza(pareo_syn)
    pareo_syn['P_min_MW'] = pareo_syn['P_min_MW'].astype(float)
    pareo_sta = funcion_limpieza(pareo_sta)
    pareo_cargas = funcion_limpieza(pareo_cargas)
    print('='*80)
    return pareo_syn, pareo_sta, pareo_cargas