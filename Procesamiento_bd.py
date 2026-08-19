import pandas as pd
from datetime import timedelta, datetime
from typing import Tuple
from numpy import pi
import logging
from haversine import haversine, Unit
from Lector_excels import distancias_usuario
from Menus import menu_distancias
from Configuracion_inicial import input_log
from pathlib import Path

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

def crear_fechas(parametros):
    """se crea el dataframe fechas segun la etapa, para todo el period de estudio
    Args:
        con la informacion de la funcion alcance se contruye df_fechas
    Returns:
        DataFrame: con las fechas por etapa
    """
    inicio = parametros['inicio']
    dias_etapa = parametros['dias_etapa']
    etapa_inicio = parametros['etapa_inicio']
    numero_etapas = parametros['numero_etapas']
    fecha_inicio = inicio + timedelta(days = dias_etapa * (etapa_inicio - 1))
    datos_etapas = []
    for etapa in range(1, numero_etapas + 1, 1):
        datos_etapas.append({'Fecha': fecha_inicio, 'Etapa': etapa})
        fecha_inicio += timedelta(days=dias_etapa)
        if fecha_inicio.month == 12 and fecha_inicio.day >= 26:
            fecha_inicio = datetime(fecha_inicio.year + 1, 1, 1)
    return pd.DataFrame(datos_etapas)

def modificacion_circuitos(df_mcirc: pd.DataFrame, df_fechas: pd.DataFrame, df_barras: pd.DataFrame,
                        datos_estudio: dict, net,config, ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Se cargan las modificaciones futuras de circuitos, se identifica la etapa del cambio de estatus y se convierten
    los parametros en base 100 [mva] porcentual a parametros reconocibles por el pandapower, la asignacion de si
    esta activo o no se hace en el gestor de topologia (Solo identifica la etapa del cambio de estatus)
    Args:
        df_mcirc (pd.DataFrame): Dataframe con todas las modificaciones de los circuitos (Se genera con el SDDP)
        df_fechas (pd.DataFrame): Dataframe que relaciona las fechas con las etapas
        df_barras (pd.DataFrame): Dataframe con la informacion de los buses
        net (_type_): Objeto pandapower
        config (_type_): Configuracion de la red hecha por el usuario
    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Dataframes especificos de lineas y trafos con toda la informacion
        necesaria y ya procesada para su uso en el cambio de topologia
    """
    df_mcirc = df_mcirc.copy()
    df_fechas= df_fechas.copy()
    if df_mcirc.empty:
        # devolvemos df vacios para evitar que el programa se detenga
        logger.info('No se procesaron modificaciones futuras (mcirc -> vacio))')
        return pd.DataFrame(), pd.DataFrame()
    # Ordenamos df_mcirc
    df_mcirc['fecha'] = pd.to_datetime(df_mcirc['fecha'])
    df_mcirc.sort_values(by='fecha', inplace=True)
    df_mcirc = pd.merge_asof(
        df_mcirc,
        df_fechas,
        left_on='fecha',
        right_on='Fecha',
        direction='forward')
    df_mcirc['status'] = df_mcirc['estatus'] == 0 # asigna True a los 0 y False a los valores diferentes
    df_mcirc.drop(columns=['fecha', 'estatus'], inplace=True)
    # Identificacmos niveles de tension 
    df_mcirc = df_mcirc.merge(
        df_barras[['id_bus_sddp', 'U_kV']],
        left_on='id_bus_origen',
        right_on='id_bus_sddp',
        how='left'
    ).rename(columns={'U_kV': 'u_hv_kv'}).drop(columns='id_bus_sddp')
    df_mcirc = df_mcirc.merge(
        df_barras[['id_bus_sddp', 'U_kV']],
        left_on='id_bus_destino',
        right_on='id_bus_sddp',
        how='left'
    ).rename(columns={'U_kV': 'u_lv_kv'}).drop(columns='id_bus_sddp')
    # Separamos lineas de trafos
    df_mline = df_mcirc[df_mcirc['u_hv_kv'] == df_mcirc['u_lv_kv']].copy()
    df_mtrafo = df_mcirc[df_mcirc['u_hv_kv'] != df_mcirc['u_lv_kv']].copy()
    # --- Lineas ---
    df_mline['r_(ohm/km)'] = df_mline['r_b100_%']*df_mline['u_hv_kv']*df_mline['u_hv_kv']/(100*net.sn_mva)
    df_mline['x_(ohm/km)'] = df_mline['x_b100_%']*df_mline['u_hv_kv']*df_mline['u_hv_kv']/(100*net.sn_mva)
    df_mline['f_(nF/km)'] = df_mline['mvar']/(df_mline['u_hv_kv']*df_mline['u_hv_kv'])*(1E9/(2*pi*net.f_hz))
    df_mline['f_(nF/km)'] = df_mline['f_(nF/km)'].fillna(0)
    df_mline['I_mx_kA'] = df_mline['cap_nom_mw']/(df_mline['u_hv_kv']*(3**0.5)*config.Fp)
    df_mline.drop(columns=['r_b100_%','x_b100_%','mvar','u_hv_kv','u_lv_kv','cap_nom_mw','Prob(%)','LimFE(MW)',
                        '(Tmn)','(Tmx)','phsmin','phsmax'], inplace=True)
    # --- Transformadores ---
    df_mtrafo['Ucc_%_bnom']=(((df_mtrafo['r_b100_%']**2)+(df_mtrafo['x_b100_%']**2))**0.5)*((df_mtrafo['cap_nom_mw']/config.Fp)/net.sn_mva)
    df_mtrafo['r_bnom_%']=df_mtrafo['r_b100_%']*df_mtrafo['cap_nom_mw']/net.sn_mva
    df_mtrafo['sn_mva'] = df_mtrafo['cap_nom_mw'] / config.Fp
    df_mtrafo.drop(columns=['r_b100_%','x_b100_%','cap_nom_mw','Prob(%)','LimFE(MW)','(Tmn)','(Tmx)',
                            'phsmin','phsmax','mvar'], inplace=True)
    logger.info(f'Se procesaron modificaciones en {len(df_mtrafo)} transformadores y {len(df_mline)} lineas.')
    return df_mtrafo, df_mline

def procesar_despachos(df_gerter, df_gerhid, df_gergnd, df_demxbael,df_duraci, net) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Conversion de datos despachos y demanda de energia a potencia, para la asignacion de despachos y cargas en los 
    escenarios de simulacion
    Args:
        df_gerter (_type_): Dataframe con la infromacion de los despachos de termoelectricas
        df_gerhid (_type_): Dataframe con la infromacion de los despachos de hidros
        df_gergnd (_type_): Dataframe con la infromacion de los despachos de renovables
        df_demxbael (_type_): Dataframe con la infromacion de la demanda por barra
        df_duraci (_type_): Dataframe con la duracion en horas por bloque
        net (_type_): Objeto pandapower
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]: Devueve dataframes con la informacion de los 
        despachos y demanda en MW, ademas devuelve una lista pd.series con la informacion de que generadores son 
        los slacks por escenario
    """
    df_duraci = df_duraci.drop(columns=['Serie']).set_index(['Etapa', 'Bloque'])
    nombre_duracion = df_duraci.columns[0]
    def convertir_energia_a_potencia(df, indices, nombres_columnas: list = None) -> pd.DataFrame:
        df_indexed = df.set_index(indices)
        df_con_duracion = df_indexed.join(df_duraci)
        # Convertir: (MWh / horas) * 1000 = MW
        df_mw = df_con_duracion.div(df_con_duracion[nombre_duracion], axis=0).mul(1000).drop(columns=nombre_duracion)
        df_mw.columns = df_mw.columns.str.rstrip()
        if nombres_columnas is not None: # Reordenar columnas si se especifica
            df_mw = df_mw[nombres_columnas]
        return df_mw
    indices_gen = ['Etapa', 'Serie', 'Bloque']
    # --- Procesamiento de generacion termica e hidro ---
    df_desp_TH = df_gerter.set_index(indices_gen)
    if not df_gerhid.empty:
        df_desp_TH = df_desp_TH.join(df_gerhid.set_index(indices_gen))
    df_desp_TH = convertir_energia_a_potencia(df_desp_TH.reset_index(), indices_gen, list(net.gen['name']))
    # --- Procesamiento de renovables ---
    if not df_gergnd.empty:
        df_desp_ren = convertir_energia_a_potencia(df_gergnd, indices_gen, list(net.sgen['name']))
    else:
        df_desp_ren = pd.DataFrame()
    # --- Identificacion de Slacks ---
    Slacks = df_desp_TH.idxmax(axis=1)
    # --- Procesamiento de cargas ---
    df_demanda = convertir_energia_a_potencia(
        df_demxbael, indices_gen, list(net.load['name']))
    print(f"{'='*80}\n")
    return df_desp_TH, df_desp_ren, Slacks, df_demanda

#--- CALCULO DE DISTANCIAS EN LINEAS ---
# METODO HAVERSINE
def calculo_haversine(net, df_coord, df_mline) -> pd.DataFrame:
    print(f'1. Calculo de las longitudes de las lineas segun el teorema de Haversine (Las distancias calculadas son una aproximacion).')
    if not df_coord.empty:
        # red base
        logger.info('Actualizando la red base.')
        df_distancias = net.line[['name', 'from_bus', 'to_bus']].copy()
        df_distancias['id_lineas'] = net.line.index.copy()
        df_distancias = pd.merge(df_distancias, df_coord, how='left', left_on = 'from_bus', right_on='id')
        df_distancias.drop(columns = ['from_bus', 'bus'], inplace=True)
        df_distancias.rename(columns={'latitud':'lat_from','longitud':'lon_from' }, inplace=True)
        df_distancias = pd.merge(df_distancias, df_coord, how='left', left_on = 'to_bus', right_on='id')
        df_distancias.drop(columns = ['to_bus', 'bus'], inplace=True)
        df_distancias.rename(columns={'latitud':'lat_to','longitud':'lon_to' }, inplace=True)
        def calcular_km_linea(row):
            punto_inicio = (row['lat_from'], row['lon_from'])
            punto_fin = (row['lat_to'], row['lon_to'])
            return haversine(punto_inicio, punto_fin, unit=Unit.KILOMETERS)
        try :
            df_distancias['longitud_km'] = df_distancias[['lat_from', 'lon_from', 'lat_to', 'lon_to']].apply(calcular_km_linea, axis=1)
            distancias_map = df_distancias.set_index('id_lineas')['longitud_km'].to_dict()
            net.line['length_km'] = net.line.index.map(distancias_map)
            net.line['r_ohm_per_km'] /= net.line['length_km']
            net.line['x_ohm_per_km'] /= net.line['length_km']
            net.line['c_nf_per_km'] /= net.line['length_km']
            # df de modificaciones en los circuitos
            logger.info('Actualizando las modificaciones futuras de los circuitos.')
            df_mline = pd.merge(df_mline, df_distancias, how='left', left_on = 'nombre_componente', right_on='name')
            del df_distancias
            n_sin_match = df_mline['longitud_km'].isna().sum() # Lineas con modificaciones que no tienen distancia calculada
            # en df_distancias (este df nace del net.line que debe tener tanto las lineas presentes y futuras)
            if n_sin_match > 0:
                logger.error(f'{n_sin_match} circuito(s) en df_mline no tienen distancia calculada. Sus parametros quedaran como NaN.')
            df_mline['r_(ohm/km)'] /= df_mline['longitud_km']
            df_mline['x_(ohm/km)'] /= df_mline['longitud_km']
            df_mline['f_(nF/km)'] /= df_mline['longitud_km']
            df_mline = df_mline[['nombre_componente', 'id_bus_origen', 'id_bus_destino', 'Fecha', 'Etapa', 'status',
                                'r_(ohm/km)', 'x_(ohm/km)', 'f_(nF/km)', 'I_mx_kA']]
            logger.info('Todas las longitudes se actualizaron correctamente')
            print(f'{'='*60}\n')
            return df_mline
        except Exception as e:
            logger.error(f'Error al calcular distancias: {e}. Verifique que las coordenadas esten en Grados Decimales (WGS84).')
            # No cortamos el flujo del programa: mantenemos df_mline sin cambios
            return df_mline
    else:
        logger.warning(f'El archivo dbus.csv no tiene coordenadas por lo que se asumira 1[Km] para todas las lineas .')
        return df_mline

def verificacion_ruta_distancias():
    while True:
        print(f'2. Importar longitudes desde un archivo.xlsx')
        logger.info('El archivo de distancias ".xlsx" debe tener los siguientes encabezados:')
        logger.info('nombre_linea | longitud [km]')
        print(f'{'-'*60}')
        ruta = input("Ingresa la ruta completa o el nombre del archivo (con .xlsx): ")
        ruta = ruta.replace('"', '').replace("'", "")
        try:
            ruta_distancias = Path(ruta)
            return ruta_distancias
        except:
            e=rf'La direccion ingresada {ruta_distancias} no es valida.'
            logger.error(e)
            logger.info('Ingrese nuevamente la ruta.')

# FUNCION PRINCIPAL DE DISTANCIAS LINEAS
def distancias_lineas(net, df_coord, df_mline) -> pd.DataFrame:
    while True:
        menu_distancias()
        opcion = input_log('Seleccione una opcion (1-2) o pulse ENTER para usar 1 [Km]: ')
        print(f'{'-'*80}')
        if opcion == '1':
            df_mline = calculo_haversine(net, df_coord, df_mline)
            return df_mline
        elif opcion == '2':
            ruta_distancias = verificacion_ruta_distancias()
            df_mline = distancias_usuario(ruta_distancias, net, df_mline)
            return df_mline
        elif opcion.strip().lower() == '':
            logger.info(f'Se asumiran longitudes de 1 [Km] por linea (Por defecto).')
            print(f'{'='*80}\n')
            return df_mline
        else:
            print('Opcion no valida. Intente de nuevo.')