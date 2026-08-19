import matplotlib
matplotlib.use('Agg')
import pandas as pd
import sys
import numpy as np
import pandapower as pp
from pathlib import Path
from typing import Optional,List, Tuple
from multiprocessing import Pool
from tqdm import tqdm
import gc
import copy
import time
import logging

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

# --- constantes ---
DEFAULT_EXPONENTE_N = 40
# --- Modulo de caso Base ---
"""
1) Definimos la configuracion de la simulacion (escenarios a simular)
1.1 Funcion para configurar una lista de escenarios especificos
1.2 Funcion para configurar todo el alcance del estudio
1.3 Funcion para validar los escenarios configurados
"""
_ruta_log_workers = None

def _init_worker():
    logging.getLogger('pandapower').setLevel(logging.CRITICAL)
    logging.getLogger('numba').setLevel(logging.CRITICAL)
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    if _ruta_log_workers:
        import time, random
        time.sleep(random.uniform(0, 0.5))  # evita colision al crear el archivo
        handler = logging.FileHandler(
            str(Path(_ruta_log_workers) / 'workers_errores.log'))
        handler.setLevel(logging.ERROR)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(process)d - %(message)s'))
        root_logger.setLevel(logging.ERROR)
        root_logger.addHandler(handler)
    import matplotlib
    matplotlib.use('Agg')

class Configuracion_Simulacion:
    def __init__(self, titulo_estudio:str='nombre_estudio'):
        self.lista_escenarios: List[Tuple[int, int, int]] = []
        self.nombre_estudio: str = titulo_estudio
    
    def configurar_lista_escenarios(self, escenarios: List[Tuple[int, int, int]]):
        for esc in escenarios:
            if not (isinstance(esc, tuple) and len(esc) == 3):
                raise ValueError(f"Escenario invalido: {esc}. Debe ser (etapa, serie, bloque)")
        self.lista_escenarios = escenarios
        logger.info(f"Configurados {len(escenarios)} escenarios.")
        return self.lista_escenarios
    
    def configurar_todo_el_alcance(self, datos_estudio: dict):
        escenarios = []
        for etapa in range(1, datos_estudio['numero_etapas'] + 1):
            for serie in range(1, datos_estudio['numero_series'] + 1):
                for bloque in range(1, datos_estudio['numero_bloques'] + 1):
                    escenarios.append((etapa, serie, bloque))
        self.lista_escenarios = escenarios
        logger.info(f"Configurado alcance completo: {len(escenarios)} escenarios")
        return escenarios
    
    def validar_escenarios(self, datos_estudio: dict):
        max_etapa = datos_estudio['numero_etapas']
        max_serie = datos_estudio['numero_series']
        max_bloque = datos_estudio['numero_bloques']
        for etapa, serie, bloque in self.lista_escenarios:
            if not (1 <= etapa <= max_etapa):
                raise ValueError(f"Etapa {etapa} fuera de rango [1, {max_etapa}]")
            if not (1 <= serie <= max_serie):
                raise ValueError(f"Serie {serie} fuera de rango [1, {max_serie}]")
            if not (1 <= bloque <= max_bloque):
                raise ValueError(f"Bloque {bloque} fuera de rango [1, {max_bloque}]")
        logger.info(f"Validacion exitosa: {len(self.lista_escenarios)} escenarios validos")

"""
2) Funciones de simulacion, tanto para caso base como contingencias

2.1 Gestor de topologia 
2.1.1 Se inicializa mediante (net, df_mline, df_mtrafo)
2.1.2 la funcion aplicar_topologia, cambia la topologia de la red segun la etapa, (ademas es 
    importante aclarar que no solo abarca cambios en el estado de los elemntos si no que tambien hace 
    cambios en los parametros de los elementos segun estos se modifiquen en df_mline o df_mtrafo esto
    para abarcar repotenciaciones de lineas o trafos)

2.2 Configurador de despacho y demanda
2.2.1 Se inicializa mediante (net, df_demanda, df_desp_TH, df_desp_ren, Slacks)
2.2.2 Carga los valores segun el escenario, mediante el uso de "x = self.df_y.loc[escenario].tolist()"
    en este caso carga los valores de "y" a "x" segun el escenario, una vez cargados, se saca de servicio
    aquellos que tengan valor 0

2.3 Funcion para simular flujo DC

2.4 Almacenador de resultados
2.4.1 Se definen las funciones para almacenar y crear los df de resultados tanto para el caso base como para contingencias
"""

class Gestor_Topologia:
    def __init__(self, net, df_mline: pd.DataFrame, df_mtrafo: pd.DataFrame):
        self.net = net
        # Si no hay modificaciones (o falló la carga previa), trabajamos con DataFrames vacíos
        # para evitar errores tipo "'NoneType' object is not subscriptable".
        self.df_mline = df_mline if df_mline is not None else pd.DataFrame(columns=['Etapa'])
        self.df_mtrafo = df_mtrafo if df_mtrafo is not None else pd.DataFrame(columns=['Etapa'])
        # para acelerar busquedas se opto por mapear lineas y trafos de la red
        self.map_lines = {name: idx for idx, name in net.line['name'].items()}
        self.map_trafos = {name: idx for idx, name in net.trafo['name'].items()}
        self.topologias_aplicadas = {} # acumulador de topologias aplicadas por etapa
    
    def aplicar_topologia_etapa(self, etapa: int):
        if etapa in self.topologias_aplicadas:
            # si la etapa ya fue aplicada debe estar en topologias_aplicadas por lo que no hace nada
            return
        # Si no hay columnas esperadas, no hay nada que aplicar.
        if 'Etapa' not in self.df_mline.columns and 'Etapa' not in self.df_mtrafo.columns:
            self.topologias_aplicadas[etapa] = True
            return
        # Aplica cambios si la etapa actual es menor o igual a la etapa de la modificaciones
        cambios_lineas = (self.df_mline[self.df_mline['Etapa'] <= etapa]
                          if 'Etapa' in self.df_mline.columns else self.df_mline.iloc[0:0])
        cambios_trafos = (self.df_mtrafo[self.df_mtrafo['Etapa'] <= etapa]
                          if 'Etapa' in self.df_mtrafo.columns else self.df_mtrafo.iloc[0:0])
        for _, row in cambios_lineas.iterrows():
            idx = self.map_lines.get(row['nombre_componente'])
            if idx is not None:
                self.net.line.at[idx, 'in_service'] = row['status']
                self.net.line.at[idx, 'r_ohm_per_km'] = row['r_(ohm/km)']
                self.net.line.at[idx, 'x_ohm_per_km'] = row['x_(ohm/km)']
                self.net.line.at[idx, 'c_nf_per_km'] = row['f_(nF/km)']
                self.net.line.at[idx, 'max_i_ka'] = row['I_mx_kA']
        for _, row in cambios_trafos.iterrows():
            idx = self.map_trafos.get(row['nombre_componente'])
            if idx is not None:
                self.net.trafo.at[idx, 'in_service'] = row['status']
                self.net.trafo.at[idx, 'vk_percent'] = row['Ucc_%_bnom']
                self.net.trafo.at[idx, 'vkr_percent'] = row['r_bnom_%']
                self.net.trafo.at[idx, 'sn_mva'] = row['sn_mva']
        self.topologias_aplicadas[etapa] = True

class Configurador_Despacho_Demanda:
    def __init__(self, net, df_demanda: pd.DataFrame, df_desp_TH: pd.DataFrame,
                df_desp_ren: pd.DataFrame, Slacks: pd.Series):
        self.net = net
        self.df_demanda = df_demanda
        self.df_desp_TH = df_desp_TH
        self.df_desp_ren = df_desp_ren
        self.Slacks = Slacks
    
    def configurar_escenario(self, etapa: int, serie: int, bloque: int):
        escenario = (etapa, serie, bloque)
        try:
            # Configurar cargas
            cargas = self.df_demanda.loc[escenario].tolist()
            self.net.load['p_mw'] = cargas
            self.net.load['in_service'] = self.net.load['p_mw'] != 0.0
            # Configurar generadores Hidro-Termicos
            gen_th = list(self.df_desp_TH.loc[escenario])
            self.net.gen['p_mw'] = gen_th
            self.net.gen['in_service'] = self.net.gen['p_mw'] != 0.0
            # Configurar generadores renovables
            gen_ren = list(self.df_desp_ren.loc[escenario])
            self.net.sgen['p_mw'] = gen_ren
            self.net.sgen['in_service'] = self.net.sgen['p_mw'] != 0.0
            # Configurar slack
            nombre_slack = self.Slacks[escenario]
            self.net.gen['slack'] = False
            self.net.gen.loc[self.net.gen['name'] == nombre_slack, 'slack'] = True
        except KeyError as e:
            logger.error(f"No se encontraron datos para {escenario}: {e}")
            raise

def simular_flujo_DC(net, check_conn=True):
    pp.rundcpp(net,
        trafo_model='t',
        trafo_loading='current',
        recycle=None,
        check_connectivity=check_conn,
        switch_rx_ratio=2,
        trafo3w_losses='hv',
        init='flat')

class Almacenador_Resultados:
    def __init__(self, net):
        self.net = net
        # Resultados sin contingencias
        self.resultados_lineas_loading = []
        self.resultados_lineas_flujo = []
        self.resultados_trafos_loading = []
        self.resultados_trafos_flujo = []
        # Resultados con contingencias
        self.resultados_contingencias_lineas_loading = []
        self.resultados_contingencias_lineas_flujo = []
        self.resultados_contingencias_trafos_loading = []
        self.resultados_contingencias_trafos_flujo = []
    
    def guardar_resultados(self, etapa: int, serie: int, bloque: int, 
                        nombre_contingencia: Optional[str] = None):
        if nombre_contingencia is None:
            self._guardar_caso_base(etapa, serie, bloque)
        else:
            self._guardar_contingencia(etapa, serie, bloque, nombre_contingencia)
    
    def _guardar_caso_base(self, etapa: int, serie: int, bloque: int):
        self.resultados_lineas_loading.append((etapa, serie, bloque,
            self.net.res_line['loading_percent'].values.copy()))
        self.resultados_lineas_flujo.append((etapa, serie, bloque,
            self.net.res_line['p_from_mw'].values.copy()))
        self.resultados_trafos_loading.append((etapa, serie, bloque,
            self.net.res_trafo['loading_percent'].values.copy()))
        self.resultados_trafos_flujo.append((etapa, serie, bloque,
            self.net.res_trafo['p_hv_mw'].values.copy()))
    
    def _guardar_contingencia(self, etapa: int, serie: int, bloque: int, nombre_contingencia: str):
        self.resultados_contingencias_lineas_loading.append((etapa, serie, bloque, nombre_contingencia,
            self.net.res_line['loading_percent'].values.copy()))
        self.resultados_contingencias_lineas_flujo.append((etapa, serie, bloque, nombre_contingencia,
            self.net.res_line['p_from_mw'].values.copy()))
        self.resultados_contingencias_trafos_loading.append((etapa, serie, bloque, nombre_contingencia,
            self.net.res_trafo['loading_percent'].values.copy()))
        self.resultados_contingencias_trafos_flujo.append((etapa, serie, bloque, nombre_contingencia,
            self.net.res_trafo['p_hv_mw'].values.copy()))
    
    def construir_dataframes(self, df_fechas: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        line_names = self.net.line['name'].values
        trafo_names = self.net.trafo['name'].values
        df_loading_line = self._construir_df_caso_base(
            self.resultados_lineas_loading, line_names, 'loading_percent')
        df_flujo_line = self._construir_df_caso_base(
            self.resultados_lineas_flujo, line_names, 'Flujo_mw')
        df_loading_trafo = self._construir_df_caso_base(
            self.resultados_trafos_loading, trafo_names, 'loading_percent')
        df_flujo_trafo = self._construir_df_caso_base(
            self.resultados_trafos_flujo, trafo_names, 'Flujo_mw')
        df_carga = pd.concat([df_loading_line, df_loading_trafo], ignore_index=True)
        df_flujo = pd.concat([df_flujo_line, df_flujo_trafo], ignore_index=True)
        # Agregar fechas
        df_carga = pd.merge(df_carga, df_fechas, on='Etapa', how='left')
        df_flujo = pd.merge(df_flujo, df_fechas, on='Etapa', how='left')
        # Reordenar columnas
        df_carga = df_carga[['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente', 'loading_percent']]
        df_flujo = df_flujo[['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente', 'Flujo_mw']]
        # Reemplazar NaN con cero
        df_carga['loading_percent'] = df_carga['loading_percent'].fillna(0.0)
        df_flujo['Flujo_mw'] = df_flujo['Flujo_mw'].fillna(0.0)
        return df_carga, df_flujo
    
    def construir_dataframes_contingencias(self, df_fechas: pd.DataFrame, nombre_cont:str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        line_names = self.net.line['name'].values
        trafo_names = self.net.trafo['name'].values
        df_loading_line = self._construir_df_contingencias(
            self.resultados_contingencias_lineas_loading, line_names, 'loading_percent', nombre_cont)
        df_flujo_line = self._construir_df_contingencias(
            self.resultados_contingencias_lineas_flujo, line_names, 'flujo_mw', nombre_cont)
        # Construir DataFrames para transformadores
        df_loading_trafo = self._construir_df_contingencias(
            self.resultados_contingencias_trafos_loading, trafo_names, 'loading_percent', nombre_cont)
        df_flujo_trafo = self._construir_df_contingencias(
            self.resultados_contingencias_trafos_flujo, trafo_names, 'flujo_mw', nombre_cont)
        # Combinar
        df_carga = pd.concat([df_loading_line, df_loading_trafo], ignore_index=True)
        df_flujo = pd.concat([df_flujo_line, df_flujo_trafo], ignore_index=True)
        if df_carga.empty or df_flujo.empty:
            logger.warning("Dataframes de contingencias vacios ya que no hay contingencias")
            return pd.DataFrame(), pd.DataFrame()
        # Agregar fechas
        df_carga = pd.merge(df_carga, df_fechas, on='Etapa', how='left')
        df_flujo = pd.merge(df_flujo, df_fechas, on='Etapa', how='left')
        # Reordenar columnas
        df_carga = df_carga[['Fecha', 'Etapa', 'Bloque', 'Serie', 
                            'Nombre_Contingencia', 'Componente', 'loading_percent']]
        df_flujo = df_flujo[['Fecha', 'Etapa', 'Bloque', 'Serie', 
                            'Nombre_Contingencia', 'Componente', 'flujo_mw']]
        # Reemplazar NaN con cero
        df_carga['loading_percent'] = df_carga['loading_percent'].fillna(0.0)
        df_flujo['flujo_mw'] = df_flujo['flujo_mw'].fillna(0.0)
        return df_carga, df_flujo
    
    def limpiar_resultados(self):
        self.resultados_lineas_loading = []
        self.resultados_lineas_flujo = []
        self.resultados_trafos_loading = []
        self.resultados_trafos_flujo = []
        self.resultados_contingencias_lineas_loading = []
        self.resultados_contingencias_lineas_flujo = []
        self.resultados_contingencias_trafos_loading = []
        self.resultados_contingencias_trafos_flujo = []
    
    @staticmethod
    def _construir_df_caso_base(resultados: List[tuple], nombres: np.ndarray,
                                nombre_columna: str) -> pd.DataFrame:
        n_elementos = len(nombres)
        bloques_df = []
        for etapa, serie, bloque, vals in resultados:
            if len(vals) != n_elementos:
                logger.warning(
                    f"Inconsistencia en datos: esperados {n_elementos} elementos, "
                    f"recibidos {len(vals)} en etapa={etapa}, bloque={bloque}, serie={serie}")
                continue
            bloques_df.append(pd.DataFrame({
                'Etapa': np.repeat(etapa, n_elementos),
                'Bloque': np.repeat(bloque, n_elementos),
                'Serie': np.repeat(serie, n_elementos),
                'Componente': nombres,
                nombre_columna: vals}))
        if not bloques_df:
            return pd.DataFrame(columns=['Etapa', 'Bloque', 'Serie', 'Componente', nombre_columna])
        return pd.concat(bloques_df, ignore_index=True)
    
    @staticmethod
    def _construir_df_contingencias(data_list, nombres_componentes, nombre_valores, nombre_cont) -> pd.DataFrame:
        n_elems = len(nombres_componentes)
        bloques_df = []
        for etapa, serie, bloque, nombre_cont_tuple, vals in data_list:
            if len(vals) != n_elems:
                continue
            bloques_df.append(pd.DataFrame({
                'Etapa': np.repeat(etapa, n_elems),
                'Bloque': np.repeat(bloque, n_elems),
                'Serie': np.repeat(serie, n_elems),
                'Nombre_Contingencia': nombre_cont,
                'Componente': nombres_componentes,
                nombre_valores: vals}))
        if not bloques_df:
            return pd.DataFrame(columns=['Etapa', 'Bloque', 'Serie',
                                        'Nombre_Contingencia', 'Componente', nombre_valores])
        return pd.concat(bloques_df, ignore_index=True)

class almacenador_reportes_red:
    def __init__(self):
        self.datos_topologia = []
        self.datos_demanda = []
        self.datos_despacho = []
        self.contador_escenarios = 0
    
    def guardar_estado(self, net, etapa: int, serie: int, bloque: int):
        # Topologia
        df_lineas = net.line[['name', 'in_service']].assign(
            Etapa=etapa, Serie=serie, Bloque=bloque, Tipo='Linea'
        ).rename(columns={'name': 'Nombre', 'in_service': 'In_Service'})
        df_trafos = net.trafo[['name', 'in_service']].assign(
            Etapa=etapa, Serie=serie, Bloque=bloque, Tipo='Transformador'
        ).rename(columns={'name': 'Nombre', 'in_service': 'In_Service'})
        self.datos_topologia.append(pd.concat([df_lineas, df_trafos], ignore_index=True))
        # Demanda
        df_dem = net.load[['name', 'p_mw', 'in_service']].assign(
            Etapa=etapa, Serie=serie, Bloque=bloque
        ).rename(columns={
            'name': 'Nombre_Carga', 'p_mw': 'Demanda_MW', 'in_service': 'In_Service'})
        self.datos_demanda.append(df_dem)
        # Despacho generadores sincronos
        slack_gen = net.gen['slack'].values if 'slack' in net.gen.columns else False
        df_gen = net.gen[['name', 'p_mw', 'in_service']].assign(
            Etapa=etapa, Serie=serie, Bloque=bloque,
            Tipo_Generador='Generador_Sincrono',
            Slack=slack_gen
        ).rename(columns={'name': 'Nombre_Generador', 'p_mw': 'Despacho_MW', 'in_service': 'In_Service'})
        # Despacho generadores estaticos
        slack_sgen = net.sgen['slack'].values if 'slack' in net.sgen.columns else False
        df_sgen = net.sgen[['name', 'p_mw', 'in_service']].assign(
            Etapa=etapa, Serie=serie, Bloque=bloque,
            Tipo_Generador='Generador_Estatico',
            Slack=slack_sgen
        ).rename(columns={'name': 'Nombre_Generador', 'p_mw': 'Despacho_MW', 'in_service': 'In_Service'})
        self.datos_despacho.append(pd.concat([df_gen, df_sgen], ignore_index=True))
        self.contador_escenarios += 1
    
    def exportar_csv(self, ruta_reporte, nombre_topologia='Topologia_por_Escenario.csv',
            nombre_demanda='Demanda_por_Escenario.csv', nombre_despacho='Despacho_por_Escenario.csv'):
        if not self.datos_topologia:
            logger.warning("No hay datos para exportar")
        ruta_salida = Path(ruta_reporte)
        df_topologia = pd.concat(self.datos_topologia, ignore_index=True)
        df_topologia = df_topologia.sort_values(['Etapa', 'Serie', 'Bloque', 'Tipo', 'Nombre'])
        df_topologia.to_csv(ruta_salida / nombre_topologia, index=False)
        df_demanda = pd.concat(self.datos_demanda, ignore_index=True)
        df_demanda = df_demanda.sort_values(['Etapa', 'Serie', 'Bloque', 'Nombre_Carga'])
        df_demanda.to_csv(ruta_salida / nombre_demanda, index=False)
        df_despacho = pd.concat(self.datos_despacho, ignore_index=True)
        df_despacho = df_despacho.sort_values(['Etapa', 'Serie', 'Bloque', 'Tipo_Generador', 'Nombre_Generador'])
        df_despacho.to_csv(ruta_salida / nombre_despacho, index=False)
    
    def limpiar(self):
        self.datos_topologia = []
        self.datos_demanda = []
        self.datos_despacho = []
        self.contador_escenarios = 0

def simulacion_secuencial(net, config_sim, df_mtrafo, df_mline, df_desp_TH, df_desp_ren, df_fechas,
                        Slacks, df_demanda, ruta_caso_base, generar_reportes_red, ruta_reporte)->Tuple[pd.DataFrame, pd.DataFrame]:
    inicio = time.time()
    logger.info('Iniciando simulacion del caso base. (Lista de escenarios)')
    net_copy = copy.deepcopy(net)
    gestor_topologia = Gestor_Topologia(net_copy, df_mline, df_mtrafo)
    config_dd = Configurador_Despacho_Demanda(net_copy, df_demanda, df_desp_TH, df_desp_ren, Slacks)
    almacenador = Almacenador_Resultados(net_copy)
    total = len(config_sim.lista_escenarios)
    almacenador_red = None
    if generar_reportes_red == True:
        almacenador_red=almacenador_reportes_red()
    for idx, (etapa, serie, bloque) in enumerate(config_sim.lista_escenarios, 1):
        try:
            gestor_topologia.aplicar_topologia_etapa(etapa)
            config_dd.configurar_escenario(etapa, serie, bloque)
            simular_flujo_DC(net_copy)
            almacenador.guardar_resultados(etapa, serie, bloque)
            if almacenador_red is not None:
                almacenador_red.guardar_estado(net_copy, etapa, serie, bloque)
            # Mostrar progreso cada escenario o al final
            if idx % 1 == 0 or idx == total:
                progreso = (idx / total) * 100
                logger.info(f"Progreso: {idx}/{total} ({progreso:.1f}%) - (E:{etapa}, S:{serie}, B:{bloque})")
        except Exception as e:
            logger.error(f"Error en (E:{etapa}, S:{serie}, B:{bloque}): {e}")
            raise
    df_carga, df_flujo = almacenador.construir_dataframes(df_fechas)
    df_resultado = pd.merge(df_carga, df_flujo, on=['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente'], how='left')
    ruta_salida = Path(ruta_caso_base)
    df_resultado.to_csv(ruta_salida / f"{config_sim.nombre_estudio}_flw_crgb.csv", index=False)
    del df_resultado
    if generar_reportes_red and almacenador_red is not None:
        almacenador_red.exportar_csv(ruta_reporte)
    tiempo_total = time.time() - inicio
    logger.info(f"Simulacion finalizada")
    logger.info(f"Tiempo total: {tiempo_total/60:.2f} minutos")
    return (df_carga, df_flujo)

def _simular_etapa_mp(args):
    (net, etapa, df_mline, df_mtrafo, df_demanda, df_desp_TH, 
    df_desp_ren, Slacks, series_range, bloques_range, reporte_topologia) = args
    net_copy = copy.deepcopy(net)
    gestor = Gestor_Topologia(net_copy, df_mline, df_mtrafo)
    configurador = Configurador_Despacho_Demanda(net_copy, df_demanda, df_desp_TH, df_desp_ren, Slacks)
    almacenador = Almacenador_Resultados(net_copy)
    gestor.aplicar_topologia_etapa(etapa)
    if reporte_topologia:
        almacenador_red = almacenador_reportes_red()
    else:
        almacenador_red = None
    for serie in range(series_range[0], series_range[1] + 1):
        for bloque in range(bloques_range[0], bloques_range[1] + 1):
            try:
                configurador.configurar_escenario(etapa, serie, bloque)
                simular_flujo_DC(net_copy)
                almacenador.guardar_resultados(etapa, serie, bloque)
                if reporte_topologia == True:
                    almacenador_red.guardar_estado(net_copy, etapa, serie, bloque)
            except Exception as e:
                logger.error(f"Error en (E:{etapa}, S:{serie}, B:{bloque}): {e}")
    reporte_data = {
            'topologia': almacenador_red.datos_topologia if reporte_topologia and almacenador_red else [],
            'demanda': almacenador_red.datos_demanda if reporte_topologia and almacenador_red else [],
            'despacho': almacenador_red.datos_despacho if reporte_topologia and almacenador_red else []}
    gc.collect()
    return {
            'etapa': etapa,
            'resultados_lineas_loading': almacenador.resultados_lineas_loading,
            'resultados_lineas_flujo': almacenador.resultados_lineas_flujo,
            'resultados_trafos_loading': almacenador.resultados_trafos_loading,
            'resultados_trafos_flujo': almacenador.resultados_trafos_flujo,
            'reporte_red': reporte_data}

def limpiar_net_para_mp(net):
    atributos_internos = ['_ppc', '_pd2ppc_lookups', '_options', '_fbus', '_bus_lookup', '_pd2ppci_lookups']
    for attr in atributos_internos:
        if hasattr(net, attr):
            setattr(net, attr, None)
    return net

def simulacion_paralelo(net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas,
    nucleos, ruta_caso_base, ruta_reporte, config_sim, reporte_topologia, reportes_cn_flujos)-> Tuple[pd.DataFrame, pd.DataFrame]:
    global _ruta_log_workers
    _ruta_log_workers = ruta_caso_base
    inicio = time.time()
    etapas = datos_estudio['numero_etapas']
    series = datos_estudio['numero_series']
    bloques = datos_estudio['numero_bloques']
    logger.info(f"Alcance: Etapas: {etapas} - Series: {series} - Bloques: {bloques}")
    if reporte_topologia:
        almacenador_red = almacenador_reportes_red()
    net = limpiar_net_para_mp(net)
    # Preparar argumentos
    args_list = []
    for etapa in range(1, etapas + 1):
        args_list.append((
            net, etapa, df_mline, df_mtrafo, df_demanda,
            df_desp_TH, df_desp_ren, Slacks,
            (1, series), (1, bloques),reporte_topologia))
    # Ejecutar en paralelo
    logger.info(f"Iniciando simulaciones (MP) en {nucleos} nucleos para {etapas} etapas.")
    with Pool(processes=nucleos, initializer=_init_worker) as pool:
        resultados = list(tqdm(
            pool.imap_unordered(_simular_etapa_mp, args_list),
            total=etapas,
            desc='Progreso Etapas',
            unit='etapa',
            file=sys.__stdout__,
            position=0,
            leave=True))
    # Consolidar resultados
    almacenador_consolidado = Almacenador_Resultados(net)
    for res in sorted(resultados, key=lambda x: x['etapa']):
        almacenador_consolidado.resultados_lineas_loading.extend(res['resultados_lineas_loading'])
        almacenador_consolidado.resultados_lineas_flujo.extend(res['resultados_lineas_flujo'])
        almacenador_consolidado.resultados_trafos_loading.extend(res['resultados_trafos_loading'])
        almacenador_consolidado.resultados_trafos_flujo.extend(res['resultados_trafos_flujo'])
        if reporte_topologia:
            almacenador_red.datos_topologia.extend(res['reporte_red']['topologia'])
            almacenador_red.datos_demanda.extend(res['reporte_red']['demanda'])
            almacenador_red.datos_despacho.extend(res['reporte_red']['despacho'])
    # Guardar resultados
    df_carga, df_flujo = almacenador_consolidado.construir_dataframes(df_fechas)
    if reportes_cn_flujos:
        df_resultado = pd.merge(df_carga, df_flujo, on=['Fecha', 'Etapa', 'Bloque', 'Serie', 'Componente'], how='left')
        ruta_salida = Path(ruta_caso_base)
        df_resultado.to_csv(ruta_salida / f"LF(cond-n)_{config_sim.nombre_estudio}.csv", index=False)
    if reporte_topologia == True:
        almacenador_red.exportar_csv(ruta_reporte)
        almacenador_red.limpiar()
    tiempo_total = time.time() - inicio
    logger.info(f"Simulacion finalizada - Tiempo total: {tiempo_total/60:.2f} minutos")
    return (df_carga, df_flujo)

# --- Modulo de contingencias ---
"""
1) Definimos la configuracion de la simulacion de contingencias (cuantos escenarios y cuantas
contingencias), ademas definimos funciones para:
1.1 Generar el alcance completo de escenarios y contingencias
1.2 Verificar la existancia de los elementos en contingencia y de la existencia de los escenarios
"""
class Configuracion_Simulacion_Contingencias:
    def __init__(self, nombre_estudio: str = "contingencias", exponente_n: int = DEFAULT_EXPONENTE_N):
        self.nombre_estudio = nombre_estudio
        self.lista_escenarios: List[Tuple[int, int, int]] = []
        self.lista_contingencias: List[str] = []
        self.exponente_n: int = exponente_n
        self.total_simulaciones: int = 0
    
    def configurar_modo_1(self, escenarios: List[Tuple[int, int, int]], 
                        contingencias: List[str], datos_estudio: dict, net):
        self._validar_escenarios(escenarios, datos_estudio)
        self._validar_contingencias(net, contingencias)
        self.lista_escenarios = escenarios
        self.lista_contingencias = contingencias
        self.total_simulaciones = len(escenarios) * len(contingencias)
        logger.info(f"Escenarios a simular: {len(escenarios)} escenarios x "
            f"{len(contingencias)} contingencias = {self.total_simulaciones} simulaciones")
        return (self.lista_escenarios, self.lista_contingencias)
    
    def configurar_modo_2(self, contingencias: List[str], datos_estudio: dict, net):
        self._validar_contingencias(net, contingencias)
        self.lista_escenarios = self._generar_alcance_completo(datos_estudio)
        self.lista_contingencias = contingencias
        self.total_simulaciones = len(self.lista_escenarios) * len(contingencias)
        logger.info(f"Escenarios a simular: {len(self.lista_escenarios)} escenarios x "
            f"{len(contingencias)} contingencias = {self.total_simulaciones} simulaciones")
        return (self.lista_escenarios, self.lista_contingencias)
    
    def configurar_modo_3(self, escenarios: List[Tuple[int, int, int]], datos_estudio: dict, net):
        self._validar_escenarios(escenarios, datos_estudio)
        self.lista_escenarios = escenarios
        self.lista_contingencias = self._obtener_todas_contingencias(net)
        self.total_simulaciones = len(escenarios) * len(self.lista_contingencias)
        logger.info(f"Modo 3 configurado (Alcance de contingencias completo): {len(escenarios)} escenarios x "
            f"{len(self.lista_contingencias)} contingencias = {self.total_simulaciones} simulaciones")
        return (self.lista_escenarios, self.lista_contingencias, self.estrategia_simulacion)
    
    def configurar_modo_4(self, net, datos_estudio: dict):
        self.lista_escenarios = self._generar_alcance_completo(datos_estudio)
        self.lista_contingencias = self._obtener_todas_contingencias(net)
        self.total_simulaciones = len(self.lista_escenarios) * len(self.lista_contingencias)
        logger.info(f"Escenarios a simular: {len(self.lista_escenarios)} escenarios x "
            f"{len(self.lista_contingencias)} contingencias = {self.total_simulaciones} simulaciones")
        return (self.lista_escenarios, self.lista_contingencias)
    
    def _generar_alcance_completo(self, datos_estudio: dict) -> List[Tuple[int, int, int]]:
        escenarios = []
        for etapa in range(1, datos_estudio['numero_etapas'] + 1):
            for serie in range(1, datos_estudio['numero_series'] + 1):
                for bloque in range(1, datos_estudio['numero_bloques'] + 1):
                    escenarios.append((etapa, serie, bloque))
        return escenarios
    
    def _obtener_todas_contingencias(self, net) -> List[str]:
        contingencias_lineas = net.line['name'].tolist()
        contingencias_trafos = net.trafo['name'].tolist()
        contingencias = contingencias_lineas + contingencias_trafos
        logger.info(f"Elementos encontrados: {len(contingencias_lineas)} lineas + "
                f"{len(contingencias_trafos)} trafos = {len(contingencias)} total")
        return contingencias
    
    def _validar_escenarios(self, escenarios: List[Tuple[int, int, int]], datos_estudio: dict):
        max_etapa = datos_estudio['numero_etapas']
        max_serie = datos_estudio['numero_series']
        max_bloque = datos_estudio['numero_bloques']
        for esc in escenarios:
            if not (isinstance(esc, tuple) and len(esc) == 3):
                # isinstance verifica que "esc" es una tupla y len que la longitud de la tupla sea 3
                raise ValueError(f"Escenario invalido: {esc}. Debe ser (etapa, serie, bloque)")
            etapa, serie, bloque = esc
            # para la validacion de limites usamos (x_min <= x <= x_max) si "x" cumple devuelve True
            if not (1 <= etapa <= max_etapa):
                raise ValueError(f"Etapa {etapa} fuera de rango [1, {max_etapa}]")
            if not (1 <= serie <= max_serie):
                raise ValueError(f"Serie {serie} fuera de rango [1, {max_serie}]")
            if not (1 <= bloque <= max_bloque):
                raise ValueError(f"Bloque {bloque} fuera de rango [1, {max_bloque}]")
        logger.info(f"Validacion exitosa: {len(escenarios)} escenarios validos")
    
    def _validar_contingencias(self, net, contingencias: List[str]):
        if not contingencias:
            raise ValueError("No se ingresaron contingencias para validar.")
        contingencias_disponibles = net.line['name'].tolist() + net.trafo['name'].tolist()
        contingencias_invalidas = []
        for cont in contingencias:
            if cont not in contingencias_disponibles:
                contingencias_invalidas.append(cont)
        if contingencias_invalidas:
            raise ValueError(
                f"Las siguientes contingencias no existen en la red: {contingencias_invalidas}. "
                f"Total disponibles: {len(contingencias_disponibles)}")
        logger.info(f"Validacion exitosa: {len(contingencias)} contingencias validas")

"""
2) Definimos las funciones para la simulacion de contingencias
2.1 Segun la estrategia recomendada, se ejecuta una simulacion secuencias o con MP
2.2 Se identifica las contingencias, Id y tipo de elemento (para no mezclar id de trafos con id de lineas)
2.3 Calculo de Pip e Indice de severidad
2.4 Funcion MP para simular contingencias por nucleo
2.5 Funcion principal de simulacion de contingencias con MP
2.5.1 Preparacion de argumentos y ejecucion de la simulacion de contingencias con MP
2.5.2 Ejecucion de la simulacion 
2.5.3 Guardado de resultados (Is)
2.6 Funcion principal de simulacion de contingencias secuencial
"""

def  identificacion_contingencia(net, config_sim_contingencias):
    lista_contingencias = config_sim_contingencias.lista_contingencias
    lista_id_contingencia = []
    for cont in lista_contingencias:
        idx_line = net.line[net.line['name'] == cont].index
        if not idx_line.empty:
            lista_id_contingencia.append((idx_line[0], 'line', cont))
            continue
        idx_trafo = net.trafo[net.trafo['name'] == cont].index
        if not idx_trafo.empty:
            lista_id_contingencia.append((idx_trafo[0], 'trafo', cont))
            continue
        logger.warning(f"Elemento '{cont}' no encontrado en la red")
    return lista_id_contingencia

def calculo_indice_severidad(usecircpp_ct, nombre_cont, ruta_Pip, horas_serie, horas_etapa,
                            expon_n: int) -> pd.DataFrame:
    df_fechas = (usecircpp_ct.groupby(['Etapa', 'Bloque', 'Serie'], sort=False)
                [['Fecha', 'Nombre_Contingencia']].first().reset_index())
    df_cargabilidades = usecircpp_ct[['Etapa', 'Bloque', 'Serie', 'Componente', 'loading_percent']].copy()
    del usecircpp_ct
    df_cargabilidades['Sobrecarga'] = df_cargabilidades['loading_percent'] >= 100
    df_cargabilidades['PIp_Ind'] = (df_cargabilidades['loading_percent'] / 100) ** expon_n
    df_suma_pip = df_cargabilidades.groupby(['Etapa', 'Bloque', 'Serie'])['PIp_Ind'].sum().reset_index()
    df_suma_pip['PIp_Total'] = df_suma_pip['PIp_Ind'] ** (1/expon_n)
    df_conteo = df_cargabilidades.groupby(['Etapa', 'Bloque', 'Serie'])['Sobrecarga'].sum().reset_index()
    df_conteo = df_conteo.rename(columns={'Sobrecarga': 'num_sobrecargas'})
    idx_max = df_cargabilidades.groupby(['Etapa', 'Bloque', 'Serie'])['loading_percent'].idxmax()
    df_extremos = df_cargabilidades.loc[idx_max, ['Etapa', 'Bloque', 'Serie', 'Componente', 'loading_percent']]
    df_extremos = df_extremos.rename(columns={'Componente': 'comp_mx_cargab', 'loading_percent': 'max_cargab'})
    del df_cargabilidades, idx_max
    dftot = df_suma_pip.merge(df_conteo, on=['Etapa', 'Bloque', 'Serie'], how='left')
    del df_suma_pip, df_conteo
    dftot = dftot.merge(df_extremos, on=['Etapa', 'Bloque', 'Serie'], how='left')
    del df_extremos
    dftot = dftot.merge(df_fechas, on=['Etapa', 'Bloque', 'Serie'], how='left')
    del df_fechas
    dftot['num_sobrecargas'] = dftot['num_sobrecargas'].astype(int)
    dftot = dftot[['Fecha', 'Etapa', 'Bloque', 'Serie', 'PIp_Total', 'Nombre_Contingencia', 'num_sobrecargas',
                    'comp_mx_cargab', 'max_cargab']].sort_values(by=['Etapa', 'Bloque', 'Serie'])
    try:
        nombre_pip = f'PIp_{nombre_cont}.csv'
        dftot.to_csv(Path(ruta_Pip) / nombre_pip, index=False)
    except Exception as e:
        logger.error(f"Error guardando PIp para contingencia '{nombre_cont}': {e}")
    try:
        Pip_max = dftot['PIp_Total'].max()
        df_is = pd.merge(dftot, horas_etapa, how='left', on='Bloque')
        df_is['Ponderado'] = df_is['PIp_Total'] * df_is['duracion']
        res_series = df_is.groupby('Serie')['Ponderado'].sum().reset_index()
        res_series['IS'] = res_series['Ponderado'] / horas_serie
        ind_sev = res_series['IS'].mean()
        return pd.DataFrame({
            'Ind_Sev': [ind_sev],
            'max': [Pip_max],
            'contingencia': [nombre_cont]})
    except Exception as e:
        logger.error(f"Error calculando indice de severidad para '{nombre_cont}': {e}")
        return pd.DataFrame({
            'Ind_Sev': [np.nan],
            'max': [np.nan],
            'contingencia': [nombre_cont]})

def _simular_contingencia_mp(args) -> pd.DataFrame:
    (net, id_cont, tipo_cont, nombre_cont, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, etapas, series,
    bloques, df_fechas, expon_n, horas_serie, horas_etapa, reportes_cont_flujos, ruta_Pip, ruta_res_cont) = args
    net_copy = copy.deepcopy(net)
    gestor = Gestor_Topologia(net_copy, df_mline, df_mtrafo)
    configurador = Configurador_Despacho_Demanda(net_copy, df_demanda, df_desp_TH, df_desp_ren, Slacks)
    almacenador = Almacenador_Resultados(net_copy)
    almacenador.limpiar_resultados()
    df_carga_lista = []
    df_flujo_lista = []
    for etapa in range(1, etapas + 1):
        try:
            gestor.aplicar_topologia_etapa(etapa)
            for serie in range(1, series + 1):
                for bloque in range(1, bloques + 1):
                    try:
                        configurador.configurar_escenario(etapa, serie, bloque)
                        if tipo_cont == 'line':
                            prev_status = net_copy.line.at[id_cont, 'in_service']
                            net_copy.line.at[id_cont, 'in_service'] = False
                        elif tipo_cont == 'trafo':
                            prev_status = net_copy.trafo.at[id_cont, 'in_service']
                            net_copy.trafo.at[id_cont, 'in_service'] = False
                        try:
                            simular_flujo_DC(net_copy)
                            almacenador.guardar_resultados(etapa, serie, bloque, nombre_cont)
                        except Exception as e:
                            logger.error(f"Error en flujo DC para contingencia '{nombre_cont}' "
                                    f"(E:{etapa}, S:{serie}, B:{bloque}): {e}")
                        finally:
                            if tipo_cont == 'line':
                                net_copy.line.at[id_cont, 'in_service'] = prev_status
                            elif tipo_cont == 'trafo':
                                net_copy.trafo.at[id_cont, 'in_service'] = prev_status
                    except Exception as e:
                        logger.error(f"Error configurando escenario para contingencia '{nombre_cont}' "
                                f"(E:{etapa}, S:{serie}, B:{bloque}): {e}")
        except Exception as e:
            logger.error(f"Error aplicando topologia etapa {etapa} para contingencia '{nombre_cont}': {e}")
        # Construir y vaciar por etapa
        df_c, df_f = almacenador.construir_dataframes_contingencias(df_fechas, nombre_cont)
        if not df_c.empty:
            df_carga_lista.append(df_c)
        if not df_f.empty:
            df_flujo_lista.append(df_f)
        almacenador.limpiar_resultados()
        gc.collect()
    # Concatenar resultados de todas las etapas
    if not df_carga_lista or not df_flujo_lista:
        return pd.DataFrame({'Ind_Sev': [np.nan], 'max': [np.nan], 'contingencia': [nombre_cont]})
    usecircpp = pd.concat(df_carga_lista, ignore_index=True)
    cirflowpp = pd.concat(df_flujo_lista, ignore_index=True)
    del df_carga_lista, df_flujo_lista
    try:
        if reportes_cont_flujos:
            nombre_carga = f'Loading_ctg_{nombre_cont}.csv'
            nombre_flujo = f'LF_ctg_{nombre_cont}.csv'
            usecircpp.to_csv(Path(ruta_res_cont) / nombre_carga, index=False)
            cirflowpp.to_csv(Path(ruta_res_cont) / nombre_flujo, index=False)
    except Exception as e:
        logger.error(f"Error guardando archivos para contingencia '{nombre_cont}': {e}")
    del cirflowpp
    calculo_pip_is = calculo_indice_severidad(usecircpp, nombre_cont, ruta_Pip,
                                            horas_serie, horas_etapa, expon_n)
    del usecircpp
    gc.collect()
    return calculo_pip_is

def _generar_args(net, id_contingencias,df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
                Slacks, etapas, series,bloques, df_fechas, expon_n, horas_serie, horas_etapa,
                reportes_cont_flujos, ruta_Pip, ruta_res_cont):
    for id_cont, tipo_cont, nombre_cont in id_contingencias:
        yield ( net, id_cont, tipo_cont, nombre_cont, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
                        Slacks, etapas, series,bloques, df_fechas, expon_n, horas_serie, horas_etapa,
                        reportes_cont_flujos, ruta_Pip, ruta_res_cont)

def simular_contingencias_multiprocessing(config_sim_contingencias, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                                        df_desp_ren, Slacks, datos_estudio, df_fechas, ruta_res_cont,
                                        ruta_Pip, df_duraci, nucleos, reportes_cont_flujos) -> pd.DataFrame:
    global _ruta_log_workers
    _ruta_log_workers = ruta_res_cont
    inicio = time.time()
    etapas = datos_estudio['numero_etapas']
    series = datos_estudio['numero_series']
    bloques = datos_estudio['numero_bloques']
    horas_serie = df_duraci['duracion'].sum()
    horas_etapa = df_duraci.drop_duplicates(['Bloque'], keep='first')[['Bloque', 'duracion']].copy()
    expon_n = config_sim_contingencias.exponente_n
    logger.info(f"Alcance: Etapas: {etapas} - Series: {series} - Bloques: {bloques}")
    id_contingencias = identificacion_contingencia(net, config_sim_contingencias)
    total_contingencias = len(id_contingencias)
    if not id_contingencias:
        logger.error("No se generaron argumentos para procesar")
        return pd.DataFrame()
    net = limpiar_net_para_mp(net)
    args_gen = _generar_args(
        net, id_contingencias, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
        Slacks, etapas, series, bloques, df_fechas, expon_n, horas_serie, horas_etapa,
        reportes_cont_flujos, ruta_Pip, ruta_res_cont)
    logger.info(f"Iniciando simulaciones (MP) en {nucleos} nucleos para {total_contingencias} contingencias.")
    resultados_validos = [] # almacenda resultados de indices de severidad
    with Pool(processes=nucleos, initializer=_init_worker) as pool:
        for resultado in tqdm(
                pool.imap_unordered(_simular_contingencia_mp, args_gen, chunksize=1),
                total=total_contingencias,
                desc="Progreso Contingencias",
                unit="ctg",
                file=sys.__stdout__,
                position=0,
                leave=True):
            if resultado is not None and not resultado.empty:
                resultados_validos.append(resultado)
    if resultados_validos:
        Ind_Sev_Total = pd.concat(resultados_validos, ignore_index=True)
        tiempo_total = time.time() - inicio
        logger.info("Simulacion de contingencias finalizada.")
        logger.info(f"Tiempo total: {tiempo_total/60:.2f} minutos")
        return Ind_Sev_Total
    else:
        logger.error("No se obtuvieron resultados validos de ninguna contingencia")
        return pd.DataFrame()

def _simular_contingencia_mp_escenarios_indiv(args) -> Tuple[str, bool]:
    (net, id_cont, tipo_cont, nombre_cont, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
        Slacks, lista_escenarios, df_fechas, ruta_res_cont, nombre_estudio, reportes_cont_flujos) = args
    net_copy=copy.deepcopy(net)
    gestor = Gestor_Topologia(net_copy, df_mline, df_mtrafo)
    configurador = Configurador_Despacho_Demanda(net_copy, df_demanda, df_desp_TH, df_desp_ren, Slacks)
    almacenador = Almacenador_Resultados(net_copy)
    almacenador.limpiar_resultados()
    for (etapa, serie, bloque) in lista_escenarios:
        try:
            gestor.aplicar_topologia_etapa(etapa)
            configurador.configurar_escenario(etapa, serie, bloque)
            if tipo_cont == 'line':
                prev_status = net_copy.line.at[id_cont, 'in_service']
                net_copy.line.at[id_cont, 'in_service'] = False
            elif tipo_cont == 'trafo':
                prev_status = net_copy.trafo.at[id_cont, 'in_service']
                net_copy.trafo.at[id_cont, 'in_service'] = False
            try:
                simular_flujo_DC(net_copy)
                almacenador.guardar_resultados(etapa, serie, bloque, nombre_cont)
            except Exception as e:
                logger.error(f"Error en flujo DC para contingencia '{nombre_cont}'"
                        f"(E:{etapa}, S:{serie}, B:{bloque}): {e}")
            finally:
                if tipo_cont == 'line':
                    net_copy.line.at[id_cont, 'in_service'] = prev_status
                elif tipo_cont == 'trafo':
                    net_copy.trafo.at[id_cont, 'in_service'] = prev_status
        except Exception as e:
            logger.error(f"Error configurando escenario para contingencia '{nombre_cont}' "
                    f"(E:{etapa}, S:{serie}, B:{bloque}): {e}")
        
    try:
        usecircpp, cirflowpp = almacenador.construir_dataframes_contingencias(df_fechas, nombre_cont)
        if not usecircpp.empty and not cirflowpp.empty:
            if reportes_cont_flujos:
                nombre_carga = f'Crgb_ctg_{nombre_cont}_{nombre_estudio}.csv'
                nombre_flujo = f'Fljcir_ctg_{nombre_cont}_{nombre_estudio}.csv'
                usecircpp.to_csv(Path(ruta_res_cont) / nombre_carga, index=False)
                cirflowpp.to_csv(Path(ruta_res_cont) / nombre_flujo, index=False)
            almacenador.limpiar_resultados()
            return (nombre_cont, True)
        else:
            logger.warning(f"No se generaron resultados para contingencia '{nombre_cont}'")
            almacenador.limpiar_resultados()
            return (nombre_cont, False)
    except Exception as e:
        logger.error(f"Error guardando archivos para contingencia '{nombre_cont}': {e}")
        almacenador.limpiar_resultados()
        return (nombre_cont, False)

def simular_escenarios_contingencias_especificos(config_sim_contingencias, net, df_mline, df_mtrafo,
                                        df_demanda, df_desp_TH, df_desp_ren, Slacks, 
                                        df_fechas, ruta_res_cont, nucleos,generar_reportes_resultados):
    global _ruta_log_workers
    _ruta_log_workers = ruta_res_cont
    inicio = time.time()
    lista_escenarios = config_sim_contingencias.lista_escenarios
    nombre_estudio = config_sim_contingencias.nombre_estudio
    # Prints de inicio de la simulacion de contingencias
    logger.info(f"Contingencias: {len(config_sim_contingencias.lista_contingencias)}")
    logger.info(f"Escenarios: {len(config_sim_contingencias.lista_escenarios)}")
    logger.info(f"Total simulaciones: {len(config_sim_contingencias.lista_contingencias)* len(config_sim_contingencias.lista_escenarios)}")
    # Preparamos los argumentos para la simulacion en MP
    id_contingencias = identificacion_contingencia(net, config_sim_contingencias)
    net = limpiar_net_para_mp(net)
    args_list = []
    for id_cont, tipo_cont, nombre_cont in id_contingencias:
        args_list.append(
            (net, id_cont, tipo_cont, nombre_cont, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
        Slacks, lista_escenarios, df_fechas, ruta_res_cont, nombre_estudio, generar_reportes_resultados))
    if not args_list:
        logger.error("No se generaron argumentos para procesar")
        return pd.DataFrame()
    logger.info(f"Iniciando simulaciones (MP) en {nucleos} nucleos para {len(args_list)} contingencias...")
    with Pool(processes=nucleos, initializer=_init_worker) as pool:
        resultados = list(tqdm(
            pool.imap_unordered(_simular_contingencia_mp_escenarios_indiv, args_list),
            total=len(args_list),
            desc="Progreso Contingencias",
            unit="ctg",
            position=0,
            leave=True))
    contingencias_exitosas = [r[0] for r in resultados if r[1]]
    contingencias_fallidas = [r[0] for r in resultados if not r[1]]
    tiempo_total = time.time() - inicio
    # Prints de finalizacion
    logger.info("Simulacion de contingencias por lista de escenarios finalizada")
    logger.info(f"Contingencias procesadas exitosamente: {len(contingencias_exitosas)}/{len(args_list)}")
    if contingencias_fallidas:
        logger.info(f"Contingencias con errores: {len(contingencias_fallidas)}")
        logger.info(f"  → {', '.join(contingencias_fallidas[:5])}" + 
            (f" y {len(contingencias_fallidas)-5} más..." if len(contingencias_fallidas) > 5 else ""))
    logger.info(f"Tiempo total: {tiempo_total/60:.2f} minutos")

def caso_base_completo (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio,
                    df_fechas, nucleos, ruta_caso_base, ruta_reporte, config_sim, reporte_topologia,
                    reportes_cn_flujo)->Tuple[pd.DataFrame, pd.DataFrame]:
    print(f"{'='*80}")
    print("SIMULACION RED BASE (Condicion n).")
    print(f"{'='*80}")
    config_sim.configurar_todo_el_alcance(datos_estudio)
    df_cargabilidades, df_flujos = simulacion_paralelo(net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
                    Slacks, datos_estudio, df_fechas, nucleos, ruta_caso_base, ruta_reporte, config_sim,
                    reporte_topologia, reportes_cn_flujo)
    print(f"{'='*80}")
    return df_cargabilidades, df_flujos

def caso_base_escenarios (net, config_sim, df_mtrafo, df_mline, df_desp_TH, df_desp_ren, df_fechas,
                        Slacks, df_demanda, ruta_caso_base, generar_reportes_red, ruta_reporte, escenarios)->Tuple[pd.DataFrame, pd.DataFrame]:
    print(f"{'='*80}")
    print("SIMULACION RED BASE (Condicion n) (Escenarios especificos).")
    print(f"{'='*80}")
    config_sim.configurar_lista_escenarios(escenarios)
    df_cargabilidades, df_flujos = simulacion_secuencial(net, config_sim, df_mtrafo, df_mline, df_desp_TH, df_desp_ren, df_fechas,
                        Slacks, df_demanda, ruta_caso_base, generar_reportes_red, ruta_reporte)
    return df_cargabilidades, df_flujos

def contingencias_transmision(config_sim_contingencias, net, df_mline, df_mtrafo,df_demanda, df_desp_TH,
                                df_desp_ren, Slacks, datos_estudio, df_fechas, ruta_rep_cont,
                                ruta_Pip, df_duraci, nucleos, reportes_cont_flujos, trafos_limpios):
    print(f"{'='*80}")
    print("SIMULACION RED BASE(CONDICION N-1).")
    print(f"{'='*80}")
    contingencias = net.line['name'].tolist() + trafos_limpios
    config_sim_contingencias.configurar_modo_2(contingencias, datos_estudio, net)
    indice_severidad = simular_contingencias_multiprocessing(config_sim_contingencias, net, df_mline, df_mtrafo,df_demanda, df_desp_TH,
                                df_desp_ren, Slacks, datos_estudio, df_fechas, ruta_rep_cont,
                                ruta_Pip, df_duraci, nucleos, reportes_cont_flujos)
    print(f"{'='*80}")
    return indice_severidad

def contingencias_refuerzos(config_sim_contingencias, net, df_mline, df_mtrafo,df_demanda, df_desp_TH, df_desp_ren,
                            Slacks, datos_estudio, df_fechas, ruta_Pip, df_duraci, nucleos, contingencias):
    print(f"{'='*80}")
    print("SIMULACION RED BASE(CONDICION N-1).")
    print(f"{'='*80}")
    ruta_rep_cont = None
    config_sim_contingencias.configurar_modo_2(contingencias, datos_estudio, net)
    indice_severidad = simular_contingencias_multiprocessing(config_sim_contingencias, net, df_mline, df_mtrafo,df_demanda, df_desp_TH,
                                df_desp_ren, Slacks, datos_estudio, df_fechas, ruta_rep_cont,
                                ruta_Pip, df_duraci, nucleos, False)
    print(f"{'='*80}")
    return indice_severidad

def contingencias_op5(escenarios, contingencias, config_sim_contingencias, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                                    df_desp_ren, Slacks, datos_estudio, df_fechas, rta_ctg_fp, rta_ctg_pip, df_duraci,
                                    nucleos, reportes_cont_flujos, trafos_limpios):
    print(f"{'='*80}")
    print("SIMULACION RED BASE(CONDICION N-1).")
    print(f"{'='*80}")
    if not contingencias:
        contingencias = net.line['name'].tolist() + trafos_limpios
    if not escenarios:
        config_sim_contingencias.configurar_modo_2(contingencias, datos_estudio, net)
        _ = simular_contingencias_multiprocessing(config_sim_contingencias, net, df_mline, df_mtrafo,df_demanda, df_desp_TH,
                                    df_desp_ren, Slacks, datos_estudio, df_fechas, rta_ctg_fp,
                                    rta_ctg_pip, df_duraci, nucleos, reportes_cont_flujos)
        print(f"{'='*80}")
    else:
        config_sim_contingencias.configurar_modo_2(escenarios, contingencias, datos_estudio, net)
        simular_escenarios_contingencias_especificos(config_sim_contingencias, net, df_mline, df_mtrafo,
                                        df_demanda, df_desp_TH, df_desp_ren, Slacks, 
                                        df_fechas, rta_ctg_fp, nucleos, reportes_cont_flujos)
        print(f"{'='*80}")