import pandapower as pp
import pandas as pd
import numpy as np
from dataclasses import dataclass
from pathlib import Path
import logging
from Configuracion_inicial import input_log

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

## --- Modelado para la red ---
# Modelado Pandapower
def crear_red():
    """Cracion de la red en pandapower con los atributos definidos en el objeto red y creacion de 
    .busgeodata qeu contendra toda la informacion de las coordenadas de las barras

    Args:
        config (_type_): Parametros para la creacion de la red
    """
    
    @dataclass
    class red:
        nombre: str
        F_Hz : float
        Sn_mva : float
        Fp: float
        Fp_gen : float
        Fp_sgen : float
        @classmethod
        def bolivia (cls):
            nombre="Bolivia"
            frecuencia=50.0
            S_base_mva=100.0
            factor_potencia=0.95
            fp_gen=0.85
            fp_sgen=0.95
            return cls(nombre = nombre, F_Hz = frecuencia, Sn_mva = S_base_mva, Fp = factor_potencia,
                Fp_gen = fp_gen, Fp_sgen=fp_sgen)
    
    print(f"{'='*80}")
    print("CONSTRUCCION RED PANDAPOWER.")
    print(f"{'='*80}")
    while True:
        parametros_base = input_log('Usar la configuracion de red de Bolivia (S/N):').strip().lower()
        print(f'{'-'*80}')
        if parametros_base == 's':
            config_red = red.bolivia()
            logger.info(f'Frecuencia: {config_red.F_Hz} [Hz].')
            logger.info(f'Potencia base: {config_red.Sn_mva} [MVA].')
            logger.info(f'Factor de potencia de transmision (Lineas/ Trafos): {config_red.Fp}')
            logger.info(f'Factor de potencia de generadores sincronos: {config_red.Fp_gen}')
            logger.info(f'Factor de potencia de generadores renovables: {config_red.Fp_sgen}')
            net = pp.create_empty_network(name = config_red.nombre, f_hz = config_red.F_Hz,
                                            sn_mva = config_red.Sn_mva)
            net.bus_geodata = pd.DataFrame(columns=['x', 'y'])
            print(f'{'-'*80}')
            return(net, config_red)
        
        elif parametros_base == 'n':
            nombre=input_log("Ingrese el nombre de la red:").strip().capitalize()
            frecuencia=input_log("Frecuencia:").strip()
            S_base_mva=input_log("Potencia base:").strip()
            factor_potencia=input_log('Factor de potencia de transmision (Lineas/ Trafos):').strip()
            fp_gen=input_log('Factor de potencia de generadores sincronos:').strip()
            fp_sgen=input_log('Factor de potencia de generadores renovables:').strip()
            try:
                config_red = red(nombre = nombre, F_Hz = float(frecuencia), Sn_mva = float(S_base_mva),
                                Fp = float(factor_potencia), Fp_gen = float(fp_gen), Fp_sgen = float(fp_sgen))
                net = pp.create_empty_network(name = config_red.nombre, f_hz = config_red.F_Hz,
                                            sn_mva = config_red.Sn_mva)
                net.bus_geodata = pd.DataFrame(columns=['x', 'y'])
                return(net, config_red)
            except:
                logger.error('Los valores ingresados deben ser numeros')
        
        else:
            logger.warning('Elija una opcion entre S-N.')
            print(f'{'-'*80}')

# --- Creacion de elementos de la red ---
# --- Modelo para barras ---
@dataclass
class barras:
    # Datos extraidos del sddp
    name : str
    vn_kv : float
    zone : str
    indice_sddp: int
    coordenadas: tuple
    # Datos automaticos
    in_service : bool=True
    type : str='b'

def agregar_barras(net, df_dbus, df_coord):
    """Se lee el archivo df_dbus y se generan las barras en la red, sin importar si traen o no coordenadas
    Args:
        net (_type_): Objeto pandapower donde se crean las barras
        df_dbus (_type_): Dataframe que contine la informacion necesaria para la creacion de las barras
        df_coord (_type_): Dataframe con las coordenadas por barras
    Returns:
        _type_: Devuelve un dataframe con la informacion de las barras, util para funciones futuras
    """
    df_barras = (
        df_dbus[['nombre_bus','zona','id_bus_sddp']].drop_duplicates(subset=['id_bus_sddp'])
        .reset_index(drop=True))
    if df_coord.empty:
        df_barras['latitud'] = None
        df_barras['longitud'] = None
    else:
        df_barras = pd.merge(df_barras, df_coord, left_on='id_bus_sddp', right_on='id', how='left')
    df_barras['U_kV'] = df_barras['nombre_bus'].str.extract(r'(\d+)').astype(float)
    barras_exitosas = 0
    barras_fallidas = 0
    barras_con_coords = 0
    barras_sin_coords = 0
    if not hasattr(net, 'bus_geodata'):
        net.bus_geodata = pd.DataFrame(columns=['x', 'y'])
    for _, fila in df_barras.iterrows():
        try:
            lon = fila.get('longitud')
            lat = fila.get('latitud')
            if pd.isna(lon) or pd.isna(lat):
                coordenadas = None
            else:
                coordenadas = (float(lon), float(lat))
            barra = barras(
                name=fila['nombre_bus'],
                vn_kv=float(fila['U_kV']),
                zone=fila['zona'],
                indice_sddp=int(fila['id_bus_sddp']),
                coordenadas=coordenadas)
            bus_idx = pp.create_bus(
                net,
                name=barra.name,
                vn_kv=barra.vn_kv,
                zone=barra.zone,
                index=barra.indice_sddp,
                in_service=barra.in_service,
                type=barra.type,
                geodata=barra.coordenadas)
            if barra.coordenadas is not None:
                lon, lat = barra.coordenadas
                net.bus_geodata.loc[bus_idx, 'x'] = lon
                net.bus_geodata.loc[bus_idx, 'y'] = lat
                barras_con_coords += 1
            else:
                barras_sin_coords += 1
            barras_exitosas += 1
        except Exception as e:
            barras_fallidas += 1
            logger.error(
                f"Error al crear barra '{fila['nombre_bus']}' "
                f"(ID: {fila['id_bus_sddp']}): {e}")
    if barras_fallidas > 0:
        logger.warning(
            f"Se crearon {barras_exitosas} barras exitosamente "
            f"({barras_con_coords} con coordenadas, {barras_sin_coords} sin coordenadas), "
            f"pero {barras_fallidas} fallaron.")
    else:
        logger.info(
            f"Se agregaron {len(net.bus)} barras a la red exitosamente "
            f"({barras_con_coords} con coordenadas, {barras_sin_coords} sin coordenadas).")
    return df_barras

## --- Modelo para lineas ---
@dataclass
class lineas:
    # Datos extraidos del sddp
    name : str
    from_bus : int
    to_bus : int
    r_ohm_per_km : float
    x_ohm_per_km : float
    c_nf_per_km : float
    max_i_ka : float
    in_service : bool
    indice_sddp : int
    # Datos automaticos
    length_km : float=1
    max_loading_percent : float=100.0
    g_us_per_km : float=0
    type : str='ol'
    df : float=1.0
    parallel : int=1

## --- Modelo para trafos ---
@dataclass
class transformadores:
    # Datos extraidos del sddp
    name : str
    hv_bus : int
    lv_bus : int
    sn_mva : float
    vn_hv_kv : float
    vn_lv_kv : float
    vk_percent : float
    vkr_percent : float
    indice_sddp : int
    in_service : bool
    # Datos automaticos
    pfe_kw : float = 0
    i0_percent : float = 0
    shift_degree : float = 0
    max_loading_percent : float = 100
    parallel : int = 1

def agregar_trafos_lineas(net, df_dcirc, df_barras, parametros_red):
    """Se generan los trafos y lineas en la red
    Args:
        net (_type_): Objeto pandapower en donde se guardan los elementos
        df_dcirc (_type_): Dataframe con la informacion de lineas y trafos
        df_barras (_type_): Dataframe con informacion sobre las barras
        config (_type_): Configuracion de los parametros de la red
    """
    ## ----- Circuitos -----
    #--- Separamos lineas y trafos en distintas bases de datos
    df_dcirc = pd.merge(df_dcirc, df_barras[['id_bus_sddp','U_kV']], how='left', left_on='id_bus_origen', right_on='id_bus_sddp')
    df_dcirc = df_dcirc.rename(columns={'U_kV':'u_hv_kv'})
    df_dcirc=df_dcirc.drop(columns=['id_bus_sddp'])
    df_dcirc = pd.merge(df_dcirc, df_barras[['id_bus_sddp','U_kV']], how='left', left_on='id_bus_destino', right_on='id_bus_sddp')
    df_dcirc = df_dcirc.rename(columns={'U_kV':'u_lv_kv'})
    df_dcirc=df_dcirc.drop(columns=['id_bus_sddp'])
    df_dcirc['estatus'] = np.where(df_dcirc['estado']==0,True,False)
    df_line = df_dcirc[df_dcirc['u_hv_kv']==df_dcirc['u_lv_kv']].copy()
    df_trafo = df_dcirc[df_dcirc['u_hv_kv']!=df_dcirc['u_lv_kv']].copy()
    ## ----- Lineas -----
    # --- Preparamos df_line ---
    df_line.loc[:,'r_(ohm/km)'] = df_line['r_b100_%']*df_line['u_hv_kv']*df_line['u_lv_kv']/(100*net.sn_mva)
    df_line.loc[:,'x_(ohm/km)'] = df_line['x_b100_%']*df_line['u_hv_kv']*df_line['u_lv_kv']/(100*net.sn_mva)
    df_line.loc[:,'f_(nF/km)'] = df_line['mvar']/(df_line['u_hv_kv']*df_line['u_lv_kv'])*(1E9/(2*np.pi*net.f_hz)) 
    df_line.loc[:,'f_(nF/km)'] = df_line['f_(nF/km)'].fillna(0)
    df_line.loc[:,'I_mx_kA'] = df_line['cap_nom_mw']/(df_line['u_lv_kv']*(3**0.5)*parametros_red.Fp)
    df_line.drop(columns=['r_b100_%','x_b100_%','mvar','u_hv_kv','u_lv_kv','estado','cap_nom_mw'], inplace=True)
    df_line['nombre_componente'] = df_line['nombre_componente'].str.upper().str.strip()
    # --- agregamos las lineas ---
    lineas_exitosas = 0
    lineas_fallidas = 0
    for _, fila in df_line.iterrows():
        try:
            linea = lineas(
                name = fila['nombre_componente'],
                from_bus = fila['id_bus_origen'],
                to_bus = fila['id_bus_destino'],
                r_ohm_per_km = fila['r_(ohm/km)'],
                x_ohm_per_km = fila['x_(ohm/km)'],
                c_nf_per_km = fila['f_(nF/km)'],
                max_i_ka = fila['I_mx_kA'],
                in_service =fila['estatus'],
                indice_sddp = fila['id_elemento_sddp']
            )
            pp.create_line_from_parameters(net,
            name=linea.name, 
            from_bus=linea.from_bus, 
            to_bus=linea.to_bus, 
            r_ohm_per_km = linea.r_ohm_per_km,
            x_ohm_per_km = linea.x_ohm_per_km,
            c_nf_per_km = linea.c_nf_per_km,
            max_i_ka = linea.max_i_ka,
            index=linea.indice_sddp,
            in_service = linea.in_service, 
            g_us_per_km = linea.g_us_per_km,
            type = linea.type,
            df=linea.df,
            length_km = linea.length_km,
            parallel = linea.parallel, 
            max_loading_percent=linea.max_loading_percent)
            lineas_exitosas += 1
        except Exception as e:
            lineas_fallidas += 1
            logger.error(
                f"Error al crear línea '{fila['nombre_componente']}' "
                f"(Bus {fila['id_bus_origen']} → {fila['id_bus_destino']}): {e}"
            )
    
    if lineas_fallidas > 0:
        logger.warning(
            f"Se crearon {lineas_exitosas} líneas exitosamente, "
            f"pero {lineas_fallidas} fallaron."
        )
    else:
        logger.info(f'Se agregaron {len(net.line)} líneas a la red exitosamente.')
    ## ----- Tarnsformadores -----
    # --- Prepraramos df_trafo ---
    df_trafo.loc[:,'sn_mva'] = df_trafo['cap_nom_mw'] / parametros_red.Fp
    df_trafo.loc[:,'cambio_base'] = df_trafo['sn_mva'] / net.sn_mva
    df_trafo.loc[:,'|z|_b_100'] = ((df_trafo['r_b100_%']**2) + (df_trafo['x_b100_%']**2))**0.5
    df_trafo.loc[:,'Ucc_%_bnom'] = df_trafo['|z|_b_100'] * df_trafo['cambio_base']
    df_trafo.loc[:,'r_bnom_%']=df_trafo['r_b100_%']*df_trafo['cambio_base']
    df_trafo.drop(columns=['r_b100_%','x_b100_%','cap_nom_mw','estado', 'cambio_base', '|z|_b_100'], inplace=True)
    df_trafo['nombre_componente'] = df_trafo['nombre_componente'].str.upper().str.strip()
    # --- agregamos las transformadores ---
    trafos_exitosos = 0
    trafos_fallidos = 0
    for _, fila in df_trafo.iterrows():
        try:
            trafo = transformadores(
                name = fila['nombre_componente'],
                hv_bus = fila['id_bus_origen'],
                lv_bus = fila['id_bus_destino'],
                sn_mva = fila['sn_mva'],
                vn_hv_kv = fila['u_hv_kv'],
                vn_lv_kv = fila['u_lv_kv'],
                vk_percent = fila['Ucc_%_bnom'],
                vkr_percent = fila['r_bnom_%'],
                indice_sddp = fila['id_elemento_sddp'],
                in_service = fila['estatus'])
            pp.create_transformer_from_parameters(net,
            name = trafo.name,
            hv_bus = trafo.hv_bus,
            lv_bus = trafo.lv_bus,
            sn_mva = trafo.sn_mva,
            vn_hv_kv = trafo.vn_hv_kv,
            vn_lv_kv = trafo.vn_lv_kv,
            vk_percent = trafo.vk_percent,
            vkr_percent = trafo.vkr_percent,
            index = trafo.indice_sddp,
            in_service = trafo.in_service,
            pfe_kw = trafo.pfe_kw,
            i0_percent = trafo.i0_percent,
            shift_degree = trafo.shift_degree,
            max_loading_percent = trafo.max_loading_percent,
            parallel = trafo.parallel
            )
            trafos_exitosos += 1
        except Exception as e:
            trafos_fallidos += 1
            logger.error(
                f"Error al crear transformador '{fila['nombre_componente']}' "
                f"(Bus {fila['id_bus_origen']} → {fila['id_bus_destino']}): {e}"
            )
    if trafos_fallidos > 0:
        logger.warning(
            f"Se crearon {trafos_exitosos} transformadores exitosamente, "
            f"pero {trafos_fallidos} fallaron."
        )
    else:
        logger.info(f'Se agregaron {len(net.trafo)} transformadores a la red exitosamente.')
## --- Modelo para generadores ---
# --- Generadores sincronos ---
@dataclass
class generadores:
    name : str
    bus : int
    p_mw : float
    sn_mva : float 
    index = None
    type : str='sync'
    vm_pu : float = 1.0
    scaling : float = 1.0
    in_service : bool=True
    slack : bool=False
    controllable : bool=False

def agregar_gen_sincronos(net, df_chidrobo, df_ctermibo, df_dbus, parametros_red):
    """Creacion de generadores sincronos
    Args:
        net (_type_): Objeto pandapower endonde se cargan los generadores
        df_chidrobo (_type_): Dataframe con la informacion de las generadoras hidro
        df_ctermibo (_type_): Dataframe con la informacion de los generadores termicos
        df_dbus (_type_): Dataframe con la informacion de las barras
        config (_type_): COnfiguracion de los parametros de la red
    """
    ### ----- generadores ----- 
    # --- preparamos df_gen ---
    if df_chidrobo.empty:
        df_gen = df_ctermibo.copy()
    else:
        df_gen=pd.concat([df_chidrobo,df_ctermibo],axis=0, ignore_index=True)
    df_gen['p_min_mw']=df_gen['p_min_mw'].fillna(0)
    df_gen = pd.merge(df_gen, df_dbus[['id_bus_sddp','nombre_bus','genxbus']], how='left', left_on='nombre_gen', right_on='genxbus')
    df_gen['u_kV'] = df_gen['nombre_bus'].str.extract(r'(\d+)').astype(float)
    df_gen['sn_mva'] = df_gen['p_max_mw']/parametros_red.Fp_gen
    df_gen.drop(columns=['nombre_bus','genxbus'], inplace=True)
    # --- agregamos los generadores ---
    gen_exitosos = 0
    gen_fallidos = 0
    
    for _, fila in df_gen.iterrows():
        try:
            gen_sin = generadores(
                name = fila['nombre_gen'],
                bus = fila['id_bus_sddp'],
                p_mw = fila['p_max_mw'],
                sn_mva = fila['sn_mva']
            )
            pp.create.create_gen(net,
            name = gen_sin.name,
            bus = gen_sin.bus,
            p_mw = gen_sin.p_mw,
            sn_mva = gen_sin.sn_mva,
            index = gen_sin.index,
            type = gen_sin.type,
            vm_pu = gen_sin.vm_pu,
            scaling = gen_sin.scaling,
            in_service = gen_sin.in_service,
            slack = gen_sin.slack,
            controllable = gen_sin.controllable
            )
            gen_exitosos += 1
        except Exception as e:
            gen_fallidos += 1
            logger.error(
                f"Error al crear generador síncrono '{fila['nombre_gen']}' "
                f"(Bus: {fila['id_bus_sddp']}): {e}"
            )
    
    if gen_fallidos > 0:
        logger.warning(
            f"Se crearon {gen_exitosos} generadores síncronos exitosamente, "
            f"pero {gen_fallidos} fallaron."
        )
    else:
        logger.info(f'Se agregaron {len(net.gen)} generadores (Sincronos) a la red exitosamente.')


# --- Generadores estaticos ---
@dataclass
class generador_estatico:
    bus : int
    p_mw : float
    sn_mva : float
    name : str
    index =  None
    type = None
    q_mvar : float=0.0
    scaling : float=1.0
    in_service : bool=True
    current_source : bool=True
    controllable : bool=False

def agregar_gen_staticos(net,df_cgndbo,parametros_red):
    """Creacion de generadores estaticos
    Args:
        net (_type_): Objeto pandapower en donde se cargan los generadores
        df_cgndbo (_type_): Dataframe con la informacion de las generadoras variables
        config (_type_): Configuracion de los parametros de la red
    """
    ### ----- generadores estaticos ----- 
    # --- Configuracion del df_cgndbo ---
    df_cgndbo['sn_mva'] = df_cgndbo['p_mw']/parametros_red.Fp_sgen

    # --- Agregamos generadores estaticos ---
    sgen_exitosos = 0
    sgen_fallidos = 0
    
    for _, fila in df_cgndbo.iterrows():
        try:
            gen_stc = generador_estatico(
                name = fila['nombre_gen'],
                bus = fila['id_bus_gv'],
                p_mw = fila['p_mw'],
                sn_mva = fila['sn_mva']
            )
            pp.create_sgen(net,
            name = gen_stc.name,
            bus = gen_stc.bus,
            p_mw = gen_stc.p_mw,
            q_mvar = gen_stc.q_mvar,
            sn_mva = gen_stc.sn_mva,
            index = gen_stc.index,
            type = gen_stc.type,
            scaling = gen_stc.scaling,
            in_service = gen_stc.in_service,
            current_source = gen_stc.current_source,
            controllable = gen_stc.controllable
            )
            sgen_exitosos += 1
        except Exception as e:
            sgen_fallidos += 1
            logger.error(
                f"Error al crear generador estático '{fila['nombre_gen']}' "
                f"(Bus: {fila['id_bus_gv']}): {e}"
            )
    
    if sgen_fallidos > 0:
        logger.warning(
            f"Se crearon {sgen_exitosos} generadores estáticos exitosamente, "
            f"pero {sgen_fallidos} fallaron."
        )
    else:
        logger.info(f'Se agregaron {len(net.sgen)} generadores (Estaticos) a la red exitosamente.')
## ----- Modelo demanda -----
@dataclass
class cargas:
    bus : int
    name : str
    index = None
    type = None
    p_mw : float=0
    q_mvar : float=0.0
    # modelado de carga de potencia constante (Mejor para fujos en DC)
    const_z_percent : float=0.0
    const_i_percent : float=0.0
    scaling : float=1.0
    in_service : bool=True

def agregar_cargas(net,df_demxbael):
    """Creacion de las cargas en la red
    Args:
        net (_type_): Objeto pandapower en donde se cargan la informacion de barras con carga
        df_demxbael (_type_): Daataframe con las cargas
    """
    ## ----- Demanda -----
    # --- preparacion de df_demxbael ---
    df_demxbael=df_demxbael.set_index(['Etapa','Serie','Bloque'])
    df_demxbael.columns = [x.strip() for x in df_demxbael.columns]
    # --- agregamos cargas ---
    cargas_exitosas = 0
    cargas_fallidas = 0
    
    for barra in df_demxbael.columns:
        try:
            carga=cargas(
                bus = pp.get_element_index(net, 'bus', barra),
                name = barra
            )
            pp.create_load(net,
            bus = carga.bus,
            name = carga.name,
            index = carga.index,
            type = carga.type,
            p_mw = carga.p_mw,
            q_mvar = carga.q_mvar,
            const_z_p_percent = carga.const_z_percent,
            const_i_p_percent = carga.const_i_percent,
            const_z_q_percent = carga.const_z_percent,
            const_i_q_percent = carga.const_i_percent,
            scaling = carga.scaling,
            in_service = carga.in_service
            )
            cargas_exitosas += 1
        except Exception as e:
            cargas_fallidas += 1
            logger.error(
                f"Error al crear carga '{barra}': {e}"
            )
    
    if cargas_fallidas > 0:
        logger.warning(
            f"Se crearon {cargas_exitosas} cargas exitosamente, "
            f"pero {cargas_fallidas} fallaron."
        )
    else:
        logger.info(f'Se agregaron {len(net.load)} cargas a la red exitosamente.')

def reporte_red (net, ruta_reporte:str, generar_reporte: int, tipo_reporte: str = 'RED BASE'):
    """Generacion de reportes de red de lineas, trafos, generadores sincronos y generadores estaticos
    
    Args:
        net (PandaPowerNet): Objeto pandapower con toda la informacion de la red
        ruta_reporte (str): ruta donde se guarda el archivo 
        generar_reporte (int): Llave para generar reportes:
            1 -> Todos los reportes 
            2 -> Solo lineas, trafos, barras
            3 -> No generar nada
        tipo_reporte (str): Informacion sobre que red es la qeu se esta sacando el reporte de topologia
    """
    print(f'{'-'*80}')
    print(f'GENERACION DE REPORTES DE LA TOPOLOGIA DE LA {tipo_reporte}')
    print(f'{'-'*80}')
    ruta = Path(ruta_reporte)
    if generar_reporte == 3:
        logger.info('No se genero ningun reporte de topologia')
    elif generar_reporte == 2:
        for elemento, nombre in {'bus':'Buses','line':'Lineas','trafo':'Trafos'}.items():
            reporte = getattr(net, elemento)
            nombre_reporte = f'Reporte_{nombre}.csv'
            ruta_completa_archivo = Path(ruta) / nombre_reporte
            ruta_completa_archivo.parent.mkdir(parents=True, exist_ok=True)
            reporte.to_csv(ruta_completa_archivo, index=True)
            logger.info(f'Se genero el reporte {nombre_reporte}.')
        print(f'{'-'*80}')
    else: 
        for elemento, nombre in {'bus':'Buses','line':'Lineas','trafo':'Trafos', 'gen':'Gen_Sincronos', 
                    'sgen':'Gen_Estaticos'}.items():
            reporte = getattr(net, elemento)
            nombre_reporte = f'Reporte_{nombre}.csv'
            ruta_completa_archivo = Path(ruta) / nombre_reporte
            ruta_completa_archivo.parent.mkdir(parents=True, exist_ok=True)
            reporte.to_csv(ruta_completa_archivo, index=True)
            logger.info(f'Se genero el reporte {nombre_reporte}.')
        print(f'{'-'*80}')

def trafos_gen(net, u_kv_filtro=69):
    print(f"{'-' * 80}")
    df_trafos = net.trafo.copy()
    barras_gen = set()
    if hasattr(net, "gen"):
        barras_gen.update(net.gen["bus"].dropna().astype(int).tolist())
    if hasattr(net, "sgen"):
        barras_gen.update(net.sgen["bus"].dropna().astype(int).tolist())
    barras_con_lineas = set()
    if hasattr(net, "line"):
        barras_con_lineas.update(net.line["from_bus"].dropna().astype(int).tolist())
        barras_con_lineas.update(net.line["to_bus"].dropna().astype(int).tolist())
    trafos_por_barra = {}
    for idx, trafo in df_trafos.iterrows():
        hv_bus = int(trafo["hv_bus"])
        lv_bus = int(trafo["lv_bus"])
        trafos_por_barra.setdefault(hv_bus, []).append(idx)
        trafos_por_barra.setdefault(lv_bus, []).append(idx)
    df_trafos_baja_tension = df_trafos[
        (df_trafos["vn_lv_kv"] <= u_kv_filtro) |
        (df_trafos["vn_hv_kv"] <= u_kv_filtro)
    ].copy()
    trafos_exclusivos = []
    for idx, trafo in df_trafos_baja_tension.iterrows():
        nombre_trafo = str(trafo["name"]).strip()
        hv_bus = int(trafo["hv_bus"])
        lv_bus = int(trafo["lv_bus"])
        buses_trafo = [hv_bus, lv_bus]
        barras_gen_del_trafo = [
            bus for bus in buses_trafo
            if bus in barras_gen
        ]
        if not barras_gen_del_trafo:
            continue
        for barra_generacion in barras_gen_del_trafo:
            tiene_lineas = barra_generacion in barras_con_lineas
            trafos_en_barra = trafos_por_barra.get(barra_generacion, [])
            otros_trafos = [
                id_trafo for id_trafo in trafos_en_barra
                if id_trafo != idx
            ]
            tiene_otros_trafos = len(otros_trafos) > 0
            barra_generacion_exclusiva = (
                not tiene_lineas and
                not tiene_otros_trafos
            )
            if barra_generacion_exclusiva:
                trafos_exclusivos.append(nombre_trafo)
    trafos_exclusivos = sorted(set(trafos_exclusivos))
    logger.info(f"Se identificaron {len(trafos_exclusivos)} transformadores exclusivos de generacion.")
    logger.info(f"Transformadores exclusivos de generacion: {trafos_exclusivos}")
    todos_los_trafos = set(net.trafo["name"].dropna().astype(str).str.strip().tolist())
    trafos_transmision = sorted(todos_los_trafos - set(trafos_exclusivos))
    logger.info(f"Se hara el analisis para: {len(trafos_transmision)} tansformadores")
    print(f"{'-' * 80}")
    return trafos_transmision

def lista_doble_terna(net):
    lineas = net.line.copy()
    lineas['par_buses'] = lineas.apply(lambda row: tuple(sorted([row['from_bus'], row['to_bus']])), axis=1)
    lineas_dt = lineas.groupby('par_buses').tail(-1)
    lista_2t = set(lineas_dt['name'].dropna().tolist())
    if not lista_2t:
        logger.info('No se identificaron lineas doble terna en el sistema.')
    else:
        logger.info(f'Se  identificaron {len(lista_2t)} lineas doble terna,\n{lista_2t}.')
    return lista_2t