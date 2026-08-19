import pandas as pd
import numpy as np
import logging
from Configuracion_inicial import input_log
from pathlib import Path
from Menus import menu_costos_usuario
from Lector_excels import lector_costos

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

# -- FACTORES ACTUALIZACION ---
FACTOR_DOLAR = 1.3118
FACTOR_INFLACION = 0.62

# --- COSTOS POR REFUERZO ---

# COSTOS PRECARGADOS
def costos_lineas_trafos() -> pd.DataFrame:
    df = pd.DataFrame()
    df['Elemento'] = ['LST', 'LDT', 'LDTI', 'CDT', 'Bahia', 'Trafo']
    df['500'] = [409500, 567000, 498750, 0, 4400000, 0]
    df['230'] = [151515, 252000, 212121, 68182, 2600000, 0]
    df['115'] = [117000, 182000, 169000, 45500, 1928000, 0]
    df['69'] = [99000, 154000, 153000, 38500, 1527273, 0]
    df['500/230'] = [0, 0, 0, 0, 3600000, 13800000]
    df['230/115'] = [0, 0, 0, 0, 2267600, 3520000]
    df['115/069'] = [0, 0, 0, 0, 2156000, 3872000]
    df['230/069'] = [0, 0, 0, 0, 1623600, 1450000]
    return df

def costos_reactores():
    df = pd.DataFrame()
    df['Reactor_mvar'] = [9, 12, 15, 18, 21, 24, 27, 30, 45, 60, 63, 90, 105, 114, 135, 156, 189, 240]
    df['500'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5350000, 5550000, 5750000, 5950000, 6350000, 6650000, 7050000,
                9550000]
    df['230'] = [1722773, 1822773, 1872773, 1922773, 2222773, 2322773, 2422773, 2522773, 2922773, 3222773,
                3367773, 0, 0, 0, 0, 0, 0, 0]
    df['115'] = [1078400, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    return df

# --- ACTUALIZACION DE COSTOS ---
def factor_correccion(factor_dolar: float = FACTOR_DOLAR, factor_inflacion: float = FACTOR_INFLACION):
    factor_generalizado = (0.6*(factor_dolar)+0.4*(factor_inflacion + 1))
    return factor_generalizado

def actualizar_costos_factores (df: pd.DataFrame, factor_generalizado: float):
    columnas = df.columns.to_list()
    for col in columnas[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df[col] = df[col].fillna(0)
        df[col] *= factor_generalizado
    return df

def ruta_costos_usuario():
    menu_costos_usuario()
    while True:
        ruta = input_log(f'Ingrese la ruta del archivo excel con los costos (Respetando las indicaciones):')
        ruta = ruta.replace('"', '').replace("'", "")
        try:
            ruta_costos = Path(ruta)
            return ruta_costos
        except:
            e=rf'La direccion ingresada {ruta_costos} no es valida.'
            logger.error(e)
            logger.info('Ingrese nuevamente la ruta.')
            print(f'{'-'*80}')

# --- ACTUALIZAR COSTOS OPCION 2---
def actualizar_costos(df_costos_ind: pd.DataFrame, df_costos_reactores: pd.DataFrame
                            )->tuple[pd.DataFrame, pd.DataFrame]:
    print(f'{'-'*80}')
    print('1. Los costos ya se encuentran actualizados (Consideran el factor inflacion y factor dolar).')
    print('2. Los costos se tienen que actualizar.')
    print(f'{'-'*80}')
    while True:
        opcion = input_log('Elija una opcion[1-2]: ').strip()
        if opcion == '1':
            logger.info('Los costos ya estan actualizados.')
            return df_costos_ind, df_costos_reactores
        
        elif opcion == '2':
            logger.info('Se actualizaran los costos ingresados (Ingrese los datos de factor dolar y factor inflacion).')
            logger.info('Los valores por defecto estan actualizados para la fecha: 1/03/2026.')
            factor_dol = input_log(f'Ingrese el valor del factor dolar (Presione Enter para usar {FACTOR_DOLAR}):')
            if factor_dol.strip() == "":
                factor_dol = FACTOR_DOLAR
            else:
                try:
                    factor_dol = float(factor_dol)
                    if factor_dol > 0:
                        continue
                    else: 
                        logger.warning("El factor no puede ser negativo. Usando valor por defecto.")
                        factor_dol = FACTOR_DOLAR
                except ValueError:
                    logger.error("Entrada no valida. Usando valor por defecto.")
                    factor_dol = FACTOR_DOLAR
            factor_infl = input_log(f'Ingrese el valor del factor inflacion (Presione Enter para usar {FACTOR_INFLACION}):')
            if factor_infl.strip() == "":
                factor_infl = FACTOR_INFLACION
            else:
                try:
                    factor_infl = float(factor_infl)
                    if factor_infl > 0:
                        continue
                    else: 
                        logger.warning("El factor no puede ser negativo. Usando valor por defecto.")
                        factor_infl = FACTOR_INFLACION
                except ValueError:
                    logger.error("Entrada no valida. Usando valor por defecto.")
                    factor_infl = FACTOR_INFLACION
            factor_generalizado = factor_correccion(factor_dol, factor_infl)
            df_costos_ind = actualizar_costos_factores(df_costos_ind, factor_generalizado)
            df_costos_reactores = actualizar_costos_factores(df_costos_reactores, factor_generalizado)
            print(f'{'-'*60}')
            return df_costos_ind, df_costos_reactores
        else:
            logger.error('Opcion no valida. Elija una opcion entre [1-2].')

# --- Configuracion de los costos ---
def costos(rta_econ: str|Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    print(f'{'='*80}')
    print('CONFIGURACION COSTOS ANALISIS ECONOMICO.')
    print(f'{'='*80}')
    print('1. Usar costos predeterminados.')
    print('2. Ingresar costos.')
    print(f'{'-'*80}')
    while True:
        opcion = input_log('Elija una opcion[1-2]: ').strip()
        
        if opcion == '1':
            print(f'{'-'*80}')
            logger.info('Costos actualizados para 1/03/2026')
            df_costos_ind = costos_lineas_trafos()
            df_costos_reactores = costos_reactores()
            df_costos_ind, df_costos_reactores = actualizar_costos(df_costos_ind, df_costos_reactores)
            df_costos_reactores = df_costos_reactores.sort_values('Reactor_mvar')
            ruta_salida = Path(rta_econ)/'Costos.xlsx'
            with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
                df_costos_ind.to_excel(writer, sheet_name='Lineas_Trafos', index=False)
                df_costos_reactores.to_excel(writer, sheet_name='Reactores', index=False)
            logger.info(rf'Los costos se guardaron en {rta_econ}.')
            print(f'{'='*80}')
            return df_costos_ind, df_costos_reactores
        
        elif opcion == '2':
            ruta_costos = ruta_costos_usuario()
            df_costos_ind, df_costos_reactores = lector_costos(ruta_costos)
            df_costos_ind, df_costos_reactores = actualizar_costos(df_costos_ind, df_costos_reactores)
            ruta_salida = Path(rta_econ)/'Costos.xlsx'
            with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
                df_costos_ind.to_excel(writer, sheet_name='Lineas_Trafos', index=False)
                df_costos_reactores.to_excel(writer, sheet_name='Reactores', index=False)
            logger.info(rf'Los costos se guardaron en {rta_econ}.')
            print(f'{'='*80}')
            return df_costos_ind, df_costos_reactores
        
        else:
            logger.error('Opción no valida. Intente de nuevo.')


def calculo_inversion(costo_proyecto: list, df_costos_ind: pd.DataFrame, df_costos_reactores: pd.DataFrame,
                ruta_refuerzos: str | Path, nombre_propuesta:str):
    print(f'{'='*80}')
    print(f'ESTIMACION DE COSTOS POR PROYECTO PARA LA ALTERNATIVA: {nombre_propuesta}')
    print(f'{'='*80}')
    # COPIAMOS PARA EVITAR MUTAR LOS DF ORIGINALES
    df_costos_ind = df_costos_ind.copy()
    df_costos_reactores = df_costos_reactores.copy()
    # CONSTRUIMOS EL DF CON LOS PROYECTOS DE LA ALTERNATIVA
    df_costos = pd.DataFrame(costo_proyecto, columns = ['nombre_ref', 'long[km] o cap[MW]', 'u_hv', 'u_lv',
                                                'suceptancia', 'tipo'])
    # LIMPIAMOS LAS TENSIONES PARA ARMAR LOS INDICADORES
    df_costos['u_hv'] = df_costos['u_hv'].apply(lambda x: str(int(float(x))))
    df_costos['u_lv'] = df_costos['u_lv'].apply(lambda x: str(int(float(x))))
    # CONSTRUIMOS LOS INDICADORES DE TENSION
    def build_identificador(fila):
        if fila['u_lv'] == '0':
            return str(fila['u_hv'])
        lv_str = fila['u_lv'].zfill(3) if int(fila['u_lv']) < 100 else fila['u_lv']
        hv_str = fila['u_hv'].zfill(3) if int(fila['u_hv']) < 100 else fila['u_hv']
        return hv_str + '/' + lv_str
    df_costos['identificador'] = df_costos.apply(build_identificador, axis=1)
    # SEPARAMOS LOS COSTOS DE TRAFOS Y LINEAS
    df_costos_ind.set_index('Elemento', inplace = True)
    df_costos_ind.columns = df_costos_ind.columns.astype(str)
    identificador_trafos = []
    identificador_lineas = []
    for col in df_costos_ind.columns.tolist():
        try:
            x = int(float(col))
            identificador_lineas.append(col)
        except:
            identificador_trafos.append(col)
    indices = df_costos_ind.index.tolist()
    # COSTOS LINEAS
    df_costos_lineas = df_costos_ind[identificador_lineas].copy()
    df_costos_lineas.drop(index = (indices[-1:]), inplace= True)
    # COSTOS TRAFOS
    df_costos_trafos = df_costos_ind[identificador_trafos].copy()
    df_costos_trafos.drop(index = (indices[:-2]), inplace= True)
    
    # CALCULO DE COSTOS SEGUN ELEMENTO Y TIPO
    def asignacion_costos(fila, df_costos_trafos, df_costos_lineas):
        if fila['tipo'] == 'TRAFO':
            try:
                costo = df_costos_trafos.loc['Trafo', fila['identificador']]
                costo_bahia = df_costos_trafos.loc['Bahia', fila['identificador']]
                return costo, costo_bahia, 1
            except:
                lv_str = fila['u_lv'].zfill(3) if int(fila['u_lv']) < 100 else fila['u_lv']
                hv_str = fila['u_hv'].zfill(3) if int(fila['u_hv']) < 100 else fila['u_hv']
                identificador_invertido = lv_str + '/' + hv_str
                costo = df_costos_trafos.loc['Trafo', identificador_invertido]
                costo_bahia = df_costos_trafos.loc['Bahia', identificador_invertido]
                return costo, costo_bahia, 1
        else:
            costo = df_costos_lineas.loc[fila['tipo'], fila['identificador']]
            costo_bahia = df_costos_lineas.loc['Bahia', fila['identificador']]
            return costo, costo_bahia, fila['long[km] o cap[MW]']
    columnas_nuevas = ['Costo (Ind)', 'Costo (Bahia)', 'col_aux']
    df_costos[columnas_nuevas] = df_costos.apply(lambda r: asignacion_costos(r, df_costos_trafos, df_costos_lineas), 
        axis=1, result_type='expand')
    df_costos['Costo (Elemento)'] = df_costos['Costo (Ind)'] * df_costos['col_aux']
    # CALCULO DE REACTORES (TAMAÑO Y COSTO)
    df_costos_reactores.set_index('Reactor_mvar', inplace = True)
    df_costos_reactores = df_costos_reactores.sort_index()
    df_costos_reactores.columns = df_costos_reactores.columns.astype(str)
    def mvar_reactores (fila):
        if str(fila['tipo']).upper() == 'TRAFO':
            return 0, 0
        else:
            condicion_no_reactor = (fila['suceptancia']* 0.6) < 9
            if condicion_no_reactor:
                return 0, 0
            else:
                condicion_reactor = (fila['suceptancia']* 0.6/2) > 9
                if condicion_reactor:
                    return (fila['suceptancia']* 0.6/2), (fila['suceptancia']* 0.6/2)
                else:
                    return (fila['suceptancia']* 0.6), 0
    columnas_nuevas = ['Reactor_i_mvar', 'Reactor_k_mvar']
    df_costos[columnas_nuevas] = df_costos.apply(lambda r: mvar_reactores(r), axis=1, result_type='expand')
    
    indices_comerciales = df_costos_reactores.index.to_numpy()
    def costo_reactores(fila):
        u_nom = str(int(fila['u_hv']))
        if (fila['Reactor_i_mvar'] == 0 and fila['Reactor_k_mvar'] == 0):
            return 0, 0
        elif (fila['Reactor_i_mvar'] > 0 and fila['Reactor_k_mvar'] == 0):
            idx_reactor_i = np.searchsorted(indices_comerciales, fila['Reactor_i_mvar'], side='left')
            if idx_reactor_i < len(df_costos_reactores):
                indice_exacto = indices_comerciales[idx_reactor_i]
                valor_reactor_i = df_costos_reactores.loc[indice_exacto, u_nom]
                return valor_reactor_i, 0
            else:
                valor_reactor_i = df_costos_reactores.iloc[-1][u_nom]
                return valor_reactor_i, 0
        else:
            idx_reactor_i = np.searchsorted(indices_comerciales, fila['Reactor_i_mvar'], side='left')
            if idx_reactor_i < len(df_costos_reactores):
                indice_exacto = indices_comerciales[idx_reactor_i]
                valor_reactor_i = df_costos_reactores.loc[indice_exacto, u_nom]
            else:
                valor_reactor_i = df_costos_reactores.iloc[-1][u_nom]
            idx_reactor_k = np.searchsorted(indices_comerciales, fila['Reactor_k_mvar'], side='left')
            if idx_reactor_k < len(df_costos_reactores):
                indice_exacto = indices_comerciales[idx_reactor_k]
                valor_reactor_k = df_costos_reactores.loc[indice_exacto, u_nom]
            else:
                valor_reactor_k = df_costos_reactores.iloc[-1][u_nom]
            return valor_reactor_i, valor_reactor_k
    columnas_nuevas = ['Costo_reactor_i', 'Costo_reactor_k']
    df_costos[columnas_nuevas] = df_costos.apply(lambda r: costo_reactores(r), axis=1, result_type='expand')
    
    # COSTO FINAL
    df_costos['Costo_final_$'] = df_costos['Costo (Elemento)'] + df_costos['Costo (Bahia)'] + df_costos['Costo_reactor_i'] + df_costos['Costo_reactor_k']
    df_costos = df_costos[['nombre_ref', 'long[km] o cap[MW]', 'suceptancia', 'tipo', 'identificador', 'Costo (Ind)', 
                        'Costo (Bahia)', 'Costo (Elemento)', 'Reactor_i_mvar', 'Reactor_k_mvar', 'Costo_reactor_i', 'Costo_reactor_k'
                        ,'Costo_final_$']].copy()
    df_costos.rename(columns={'nombre_ref':'Refuerzo', 'suceptancia':'Qo_MVAR', 'tipo':'Tipo', 'identificador':'Etiqueta',
                            'Costo (Ind)': 'Costo_$(unitario)', 'Costo (Elemento)':'Costo_$(Elemento)', 'Costo (Bahia)':'Costo_$(Bahia)', 
                            'Costo_reactor_i': 'Costo_Reactor_i($)', 'Costo_reactor_k': 'Costo_Reactor_k($)', 'Costo_final_$': 'Costo_total_$'},
                        inplace=True)
    df_costos.to_csv((Path(ruta_refuerzos)/f'Reporte_costos_{nombre_propuesta}.csv'), index = False)
    logger.info('Se estimo correctamente los costos por proyecto.')
    logger.info('Se guardo el reporte de costos correctamente.')
    print(f"{'='*80}")
    return df_costos