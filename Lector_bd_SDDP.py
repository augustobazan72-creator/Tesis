import pandas as pd
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime
import logging

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

# --- Estructura para la lectura de archivos ---
config_maestra = {
    # --- Archivos .dat ---
    'dbus': {
        'ruta': 'dbus.dat',
        'tipo': 'fwf',
        'datos_lector': {
            'skiprows': 1,
            'names': ['NUM.', 'Tp', 'Nombre', 'Id', '#', 'tg', 'Plnt', 'Nombre Gener', 'Area', '%per1',
                'Ploa1', 'Pind1', 'PerF1', '%per2', 'Ploa2', 'Pind2', 'PerF2', '%per3', 'Ploa3', 'Pind3',
                'PerF3', '%per4', 'Ploa4', 'Pind4', 'PerF4', '%per5', 'Ploa5', 'Pind5', 'PerF5', 'Icca'],
            'colspecs': [(0, 5),(6, 8),(8, 21),(22, 25),(25, 28),(28, 31),(31, 35),(35, 49),(49, 53),
                (53, 59),(59, 66),(66, 72),(72, 77),(77, 83),(83, 89),(89, 95),(95, 102),(102, 108),
                (108, 114),(114, 119),(119, 125),(125, 132),(132, 138),(138, 143),(143, 149),(149, 155),
                (155, 161),(161, 167),(167, 173),(173, 178)],
            'encoding': 'latin-1'
                        },
        'mapeo': {'NUM.': 'id_bus_sddp', 'Nombre': 'nombre_bus', 'Nombre Gener': 'genxbus', 'Id': 'zona'}
            },
    'dcirc': {
        'ruta': 'dcirc.dat',
        'tipo': 'fwf',
        'datos_lector': {
            'skiprows': 2,
            'names': ['#BOR.', '#BDE.NN', '.RESIS', '.REACT', 'Nome........', '(MVAR)', 'Tmn', 'Tmx',
                '(  MW)', '(MW)', '(Num)', 'I', 'C','1' ,'2','3','4','5', 'iflh','Prob', 'Cmon', 'S',
                'RPK2', 'PRTC', 'phsmin', 'phsmax'],
            'colspecs': [(0, 5),(8, 15),(16, 23),(23, 29),(30, 42),(42, 48),(48, 53),(53, 58),(58, 64),
                (64, 68),(69, 74),(74, 76),(76, 78),(79, 84),(85, 90),(91, 96),(97, 102),(103, 108),
                (109, 113),(114, 121),(122, 126),(126, 128),(129, 133),(134, 138),(139, 147),(148, 156)],
            'encoding': 'latin-1'
                        },
        'mapeo': {'#BOR.': 'id_bus_origen', '#BDE.NN': 'id_bus_destino', '(Num)': 'id_elemento_sddp',
            '.RESIS': 'r_b100_%', '.REACT': 'x_b100_%', '(MVAR)': 'mvar', '(  MW)': 'cap_nom_mw',
            'Nome........': 'nombre_componente', 'I': 'estado'}
            },
    'cgndbo': {
        'ruta': 'cgndbo.dat',
        'tipo': 'fwf',
        'datos_lector': {
            'skiprows': 2,
            'names': ["!Num","Name........",".Bus.","Tipo","Uni",".PotIns","..FatOpe","ProbFal",
                "SFal","Stat.","....O&M","CurtCos","TechTyp"],
            'colspecs': [(0, 4),(5, 17),(18, 23),(24, 28),(29, 33),(34, 41),(42, 50),(51, 58),(59, 63),
                (64, 69),(70, 77),(78, 85),(86, 93)],
            'encoding': 'latin-1'
                        },
        'mapeo': {'Name........': 'nombre_gen', '.Bus.': 'id_bus_gv', '.PotIns': 'p_mw'}
            },
    'ctermibo': {
        'ruta': 'ctermibo.dat',
        'tipo': 'fwf',
        'datos_lector': {
            'skiprows': 2,
            'names': ['!Num', '...Nombre...', '#Uni', 'Tipo', '.PotIns', '.GerMin', '.GerMax','..Teif.',
                '..Ih...','.CVaria','.MR.', 'Comb' ,'...G1..','.CEsp.1','...G2..','.CEsp.2','...G3..',
                '.CEsp.3', 'NAdF','...1','...2','...3', 'ComT', 'CTransp','StartUp', 'sfal', 'NGas',
                'NuCC','..NombreCC..', 'CoefE.'],
            'colspecs': [(0,4),(5,17),(18,22),(23,27),(28,35),(36,43),(44,51),(52,59),(60,67),(68,75),
                (76,80),(81,84),(85,92),(93,100),(101,108),(109,116),(117,124),(125,132),(133,137),
                (138,142),(143,147),(148,152),(153,157),(158,165),(166,173),(174,178),(179,183),(184,188),
                (189,201),(202,208)],
            'encoding': 'latin-1'
                        },
        'mapeo': {'...Nombre...': 'nombre_gen', '#Uni': 'unidades', '.GerMin': 'p_min_mw',
        '.GerMax': 'p_max_mw'}
                },
    'chidrobo': {
        'ruta': 'chidrobo.dat',
        'tipo': 'fwf',
        'datos_lector': {
            'skiprows': 1,
            'names': ['!NUM','...Nombre...', '.PV.', '.VAA','.TAA', '#Uni', 'Tipo', '....Pot','.FPMed.',
                '.QMin..', '.QMax..', '.VMin..', '.VMax..', '.VInic.', 'Min.V+T','..VNC..', '..ICP..',
                '...IH..'],
            'colspecs': [(0, 4),(5, 17),(18, 22),(23, 27),(28, 32),(33, 37),(38, 42),(43, 50),(51, 58),
                (59, 66),(67, 74),(75, 82),(83, 90),(91, 98),(99, 106),(107,114),(115,122),(123,130)],
            'encoding': 'latin-1'
                        },
        'mapeo': {'...Nombre...': 'nombre_gen', '#Uni': 'unidades', '....Pot': 'p_max_mw'}
                },
    'sddp': {
        'ruta': 'sddp.dat',
        'tipo': 'fwf',
        'datos_lector': {
            'skiprows': 0,
            'nrows': 25,
            'names': ['informacion', 'dato', 'extra'],
            'colspecs': [(0, 25), (26, 30), (31, 60)],
            'encoding': 'latin-1'
                        },
        'mapeo': {'informacion': 'clave','dato': 'valor'}
            },
    # --- Archivos .csv ---
    'mcirc': {
        'ruta': 'mcirc.csv', 'tipo': 'csv',
        'datos_lector': {'header': 0, 'encoding': 'latin-1'},
        'mapeo': {'Name': 'nombre_componente', 'Date': 'fecha', '#BFM.': 'id_bus_origen', '#BTO.': 'id_bus_destino',
        '.RESIS': 'r_b100_%', 'REACT': 'x_b100_%','(MVAR)':'mvar', 'LimFN(MW)': 'cap_nom_mw',
        'Status':'estatus'}
            },
    'gerter': {
        'ruta': 'gerter.csv', 'tipo': 'csv',
        'datos_lector': {'header': 3, 'encoding': 'latin-1'},
        'mapeo': {
            'Etapa' : ['Stag', 'Etap'],
            'Serie':['Seq.', 'Ser.','Scn.'],
            'Bloque':['Blck','Bloq']
                }
            },
    'demxbael': {
        'ruta': 'demxbael.csv', 'tipo': 'csv',
        'datos_lector': {'header': 3, 'encoding': 'latin-1'},
        'mapeo': {
            'Etapa' : ['Stag', 'Etap'],
            'Serie':['Seq.', 'Ser.','Scn.'],
            'Bloque':['Blck','Bloq']
                }
                },
    'gerhid': {
        'ruta': 'gerhid.csv',
        'tipo': 'csv',
        'datos_lector': {
            'header': 3,
            'encoding': 'latin-1'},
        'mapeo': {
            'Etapa' : ['Stag', 'Etap'],
            'Serie':['Seq.', 'Ser.','Scn.'],
            'Bloque':['Blck','Bloq']
                }       
            },
    'gergnd': {
        'ruta': 'gergnd.csv',
        'tipo': 'csv',
        'datos_lector': {
            'header': 3,
            'encoding': 'latin-1'},
        'mapeo': {
            'Etapa' : ['Stag', 'Etap'],
            'Serie':['Seq.', 'Ser.','Scn.'],
            'Bloque':['Blck','Bloq']
                }
            },
    'duraci': {
        'ruta': 'duraci.csv',
        'datos_lector': {'skiprows':4,'header': None, 'encoding': 'latin-1'},
        'encabezados': ['Etapa', 'Serie', 'Bloque', 'duracion']
                }
    }


def leer_archivo(ruta_completa: Path, tipo: str, datos_lector: dict) -> Tuple[Dict[str, pd.DataFrame],
                                                                                pd.DataFrame]:
    """Metodo para la lectura de archivos"""
    if tipo == 'fwf':
        return pd.read_fwf(ruta_completa, **datos_lector)
    else:
        return pd.read_csv(ruta_completa, **datos_lector)

criticos = ['dbus.dat', 'duraci.csv', 'dcirc.dat', 'sddp.dat', 'demxbael.csv' ]

def lectura_limpieza_archivos_sddp(ruta_bd: str | Path) -> tuple[dict, list]:
    # Indentificamos archivos criticos faltantes
    criticos_no_leidos = []
    
    # lectura de archivos
    datos_limpios = {}
    
    for nombre, archivo in list(config_maestra.items())[:-1]:
        ruta_completa = ruta_bd/archivo['ruta']
        if not ruta_completa.exists():
            logger.warning(f'El archivo {archivo['ruta']} no existe en la base de datos SDDP.')
            if archivo['ruta'] in criticos:
                criticos_no_leidos.append(archivo['ruta'])
            else:
                datos_limpios[nombre] = pd.DataFrame()
            continue
        df = leer_archivo(ruta_completa, archivo['tipo'], archivo['datos_lector'])
        mapeo = archivo['mapeo']
        mapeo_final = {}
        try:
            columnas_reales = df.columns.tolist()
            for nombre_interno, valor_mapeo in mapeo.items():
                # Caso 1 - (gerter, gergnd, gerhid, demxbael)
                if isinstance(valor_mapeo, list):
                    encontrado = next((col for col in valor_mapeo if col in columnas_reales), None)
                    if encontrado:
                        mapeo_final[encontrado] = nombre_interno
                # Caso 2 - (los demas menos duraci)
                else:
                    # Si la llave del diccionario es la que está en el archivo (mcirc)
                    if nombre_interno in columnas_reales:
                        mapeo_final[nombre_interno] = valor_mapeo
                    # O si el valor es el que está en el archivo (.dat)
                    elif valor_mapeo in columnas_reales:
                        mapeo_final[valor_mapeo] = nombre_interno
            # Ejecutar el filtrado y renombramiento solo si se encontraron columnas
            if mapeo_final:
                df_filtrado = df.rename(columns=mapeo_final)
                datos_limpios[nombre] = df_filtrado
            else:
                logger.error(f"No se mapearon columnas para {nombre}")
                logger.error(f'Columnas reales:{columnas_reales} difieren de los posibles mapeos.')
                logger.error(f"Revisar:\n- Configuracion lectura:{archivo['datos_lector']}\n- Mapeos:{mapeo}.")
                if archivo['ruta'] in criticos:
                    criticos_no_leidos.append([archivo['ruta']])
        except:
            logger.exception(f"Error procesando {nombre}")
            logger.exception(f"Revisar:\n- Configuracion lectura:{archivo['datos_lector']}\n-Mapeos:{mapeo}.")
            if archivo['ruta'] in criticos:
                criticos_no_leidos.append([archivo['ruta']])
    return datos_limpios, criticos_no_leidos

def lector_duraci(ruta_bd:str|Path, duraci):
    df_duraci = pd.DataFrame(columns=['Etapa', 'Serie', 'Bloque', 'duracion'])
    ruta_completa = ruta_bd / duraci['ruta']
    if not ruta_completa.exists():
        logger.warning(f'El archivo {duraci['ruta']} no existe en la base de datos SDDP.')
        return  pd.DataFrame()
    try:
        df_duraci = pd.read_csv(ruta_completa,
            skiprows=duraci['datos_lector']['skiprows'],
            header=duraci['datos_lector']['header'],
            names=duraci['encabezados'],
            encoding=duraci['datos_lector']['encoding'])
    except:
        logger.exception(f'Error procesando {duraci['ruta']}.')
        return pd.DataFrame()
    return df_duraci


def lector_SDDP(ruta_bd):
    
    print(f"{'='*80}")
    print(f"LECTURA BASE DE DATOS SDDP.")
    print(f"{'='*80}")
    
    # convertimos a ruta
    ruta_bd = Path(ruta_bd)
    
    # leemos archivos
    datos_limpios, criticos_NL = lectura_limpieza_archivos_sddp(ruta_bd)
    
    # leemos duraci
    duraci = config_maestra['duraci']
    df_duraci = lector_duraci(ruta_bd, duraci)
    
    # verificamos la lectura de todos los archivos
    archivos_leidos = list(datos_limpios.keys())
    if df_duraci.empty:
        criticos_NL.append(duraci['ruta'])
    else:
        archivos_leidos.append(duraci['ruta'])
        datos_limpios['duraci'] = df_duraci
    if criticos_NL:
        logger.error('Se encontraron archivos criticos faltantes, se detendra la ejecucion del programa.')
        msj = f'La base de datos {ruta_bd.name} le faltan los archivos criticos:\n{criticos_NL}'
        raise ValueError(msj)
    logger.info(f"Archivos:\n{archivos_leidos}\nDe la base de datos SDDP '{ruta_bd.name}' leidos correctamente")
    print(f'{'='*80}')
    return datos_limpios

# Alcance de la base de datos para la validacion de datos 
# Diccionario para los idiomas
SDDP_KEYS = {
    'idioma': {
        'ESP': 'IDIOMA',
        'ENG': 'LANGUAGE'
    },
    'ano_inicial': {
        'ESP': 'ANO INICIAL',
        'ENG': 'INITIAL YEAR'
    },
    'etapa_inicio': {
        'ESP': 'MES/SEMANA INICIAL',
        'ENG': 'INITIAL WEEK/MONTH'
    },
    'numero_etapas': {
        'ESP': 'NUMERO DE ETAPAS',
        'ENG': 'NUMBER OF STAGES'
    },
    'numero_series': {
        'ESP': 'NUMERO DE SERIES',
        'ENG': 'NUMBER OF SERIES'
    },
    'numero_bloques': {
        'ESP': 'NUMERO DE BLOQUES DEMANDA',
        'ENG': 'NUMBER OF LOAD BLOCKS'
    },
    'tipo_estudio': {
        'ESP': 'ETAPA',
        'ENG': 'STAGE TYPE'
    }}

def detectar_idioma(df_datosSDDP):
    valor = df_datosSDDP.loc[df_datosSDDP['clave'].str.contains("IDIOMA|LANGUAGE", case=False), 'valor']
    if valor.empty:
        return 'ESP'  # default seguro
    return {0: 'ENG', 1: 'ESP'}.get(int(valor.iloc[0]), 'ESP')

def get_param_sddp(df, key, idioma):
    """ 
    Busca en el dataframe un la llave y devuelve un valor
    """
    nombre = SDDP_KEYS[key][idioma]
    fila = df.loc[df['clave'].str.strip() == nombre]
    if fila.empty:
        raise ValueError (f"Parámetro SDDP no encontrado: {nombre} ({idioma})")
    return fila.iloc[0]['valor']


def alcance(dfs, nombre_carpeta):
    """Encuentra la informacion mas importante para la simulacion, numero de etapas, series, bloques, fecha de inicio
    y tipo de estudio
    Args:
        df_datosSDDP (_type_): dataframe con la imformacion de la simulacion propio del SDDP
        nombre_carpeta (_type_): Nombre de la base de datos SDDP
    raise ValueErrors:
        ValueError: En caso de no reconocer el tipo de estudio o que no concuerde regresa error y detine la ejecuciuon
    Returns:
        dict: diccionario con las constantes halladas
    """
    # desempaquetamos df_datos_SDDP
    df_datos_SDDP = dfs['sddp']
    # --- Lectura explícita de parámetros SDDP ---
    idioma = detectar_idioma(df_datos_SDDP)
    ano_inicial    = int(get_param_sddp(df_datos_SDDP, 'ano_inicial', idioma))
    etapa_inicio   = int(get_param_sddp(df_datos_SDDP, 'etapa_inicio', idioma))
    numero_etapas  = int(get_param_sddp(df_datos_SDDP, 'numero_etapas', idioma))
    numero_series  = int(get_param_sddp(df_datos_SDDP, 'numero_series', idioma))
    numero_bloques = int(get_param_sddp(df_datos_SDDP, 'numero_bloques', idioma))
    tipo_estudio   = int(get_param_sddp(df_datos_SDDP, 'tipo_estudio', idioma))
    # --- Interpretación del tipo de estudio ---
    if tipo_estudio == 1:
        dias_etapa = 7
        desc_estudio = "Semanal"
    elif tipo_estudio == 2:
        dias_etapa = 30
        desc_estudio = "Mensual"
    elif tipo_estudio == 3:
        dias_etapa = 90
        desc_estudio = "Trimestral"
    else:
        raise ValueError (f"Tipo de estudio no reconocido (numero del tipo de estudio = {tipo_estudio}"+
                        "- Solo puede ser 1, 2 o 3)\nRevise que sddp.dat tenga la informacion correcta en el modulo Lector")
    # --- Fecha inicial del estudio ---
    inicio = datetime(ano_inicial, 1, 1)
    print(f"{'='*80}")
    print(f"Descripcion del caso de estudio {nombre_carpeta}.")
    print(f"{'='*80}")
    logger.info(f"Numero de etapas: {numero_etapas}")
    logger.info(f"Numero de series: {numero_series}")
    logger.info(f"Numero de bloques: {numero_bloques}")
    logger.info(f"Tipo de estudio: {desc_estudio}")
    logger.info(f"Etapa de inicio: {etapa_inicio}")
    logger.info(f"Año de inicio: {ano_inicial}")
    print(f"{'='*80}")
    return {
        'inicio': inicio,
        'etapa_inicio': etapa_inicio,
        'numero_etapas': numero_etapas,
        'numero_series': numero_series,
        'numero_bloques': numero_bloques,
        'dias_etapa': dias_etapa
    }

# Validacion de datos

def validar_datos_SDDP(df_limpios, datos_estudio):
    print(f"{'='*80}")
    print(f"VALIDACION DE LA BASE DE DATOS SDDP.")
    print(f"{'='*80}")
    
    # Desempaquetado de dfs
    df_dbus = df_limpios["dbus"]
    df_dcirc = df_limpios["dcirc"]
    df_cgndbo = df_limpios["cgndbo"]
    df_ctermibo = df_limpios["ctermibo"]
    df_chidrobo = df_limpios["chidrobo"]
    df_mcirc = df_limpios["mcirc"]
    df_gerter = df_limpios["gerter"]
    df_gerhid = df_limpios["gerhid"]
    df_gergnd = df_limpios["gergnd"]
    df_demxbael = df_limpios["demxbael"]
    df_datos_SDDP = df_limpios["sddp"]
    df_duraci = df_limpios["duraci"]
    
    # Topologia
    
    # funcion para verificar duplicados
    def duplicados(nombre_archivo, df, columnas):
        for col in columnas:
            duplicado = df[col].duplicated().any()
            if duplicado:
                e = f'Existen duplicados en {nombre_archivo} en  la columna {col}.'
                logger.error(e)
                raise ValueError(f'{e}\nSe detendra la ejecucion del programa.')
            else: continue
    
    # funcion para verificar ceros
    def verificar_ceros(nombre_archivo, df, columnas):
        for col in columnas:
            ceros = (df[col] == 0).any()
            if ceros:
                    e = f'Existen ceros en {nombre_archivo} en la columna {col}.'
                    logger.error(e)
                    raise ValueError(f'{e}\nSe detendra la ejecucion del programa.')
            else: continue
    
    # generadores
    nombres_gen = set()
    generacion = {'ctermibo': df_ctermibo, 'chidrobo': df_chidrobo, 'df_cgndbo':df_cgndbo}
    for gen, df in generacion.items():
        duplicados(gen, df, ['nombre_gen'])
        nombres_gen.update(df['nombre_gen'].dropna().astype(str).str.strip().tolist())
    
    # barras
    barras = set(df_dbus['id_bus_sddp'].tolist())
    gen_barra = set(df_dbus['genxbus'].dropna().astype(str).str.strip().tolist())
    
    #circuitos
    columnas = ['nombre_componente', 'id_elemento_sddp']
    duplicados('dcirc', df_dcirc, columnas)
    col_0 = ['x_b100_%', 'cap_nom_mw']
    verificar_ceros('dcirc', df_dcirc, col_0)
    bus_from = set(df_dcirc['id_bus_origen'].tolist())
    bus_to = set(df_dcirc['id_bus_destino'].tolist())
    #modificaciones futuras
    if not df_mcirc.empty:
        verificar_ceros('mcirc', df_mcirc, col_0)
        mbus_from = set(df_mcirc['id_bus_origen'].dropna().tolist())
        mbus_to = set(df_mcirc['id_bus_destino'].dropna().tolist())
        if not mbus_from.issubset(barras):
            logger.error('Existen barras inexistentes en bus origen de mcirc.')
            raise ValueError('Barra inexistente en bus origen de mcirc.')
        if not mbus_to.issubset(barras):
            logger.error('Existen barras inexistentes en bus destino de mcirc.')
            raise ValueError('Barra inexistente en bus destino de mcirc.')
        vacios = df_mcirc['fecha'].isna().any()
        if vacios:
                e = f'Existen elementos sin fecha de ingres en mcirc.'
                logger.error(e)
                raise ValueError(f'{e}\nSe detendra la ejecucion del programa.')
    else:
        logger.warning('El archivo mcirc esta vacio.')
    # verificaciones red
    validaciones = {
        'Gen aislada (Generadores sin barra)' : gen_barra.issubset(nombres_gen), 
        'Bus inicio inexistente (circuito abiertos)': bus_from.issubset(barras),
        'Bus fin inexistente(circuito abiertos)': bus_to.issubset(barras),
    }
    for obs, val in validaciones.items():
        if val==False:
            logger.error(f'Existe {obs}')
            raise ValueError (obs)
    
    logger.info('Topologia de la red validada.')
    
    # Escenarios
    total_escenarios =(datos_estudio['numero_bloques'] * datos_estudio['numero_etapas'] * 
                        datos_estudio['numero_series'])
    
    # funcion de comparacion escenarios
    def validacion_escenarios(nombre_archivo, df, total_escenarios):
        df.columns = df.columns.str.strip()
        df_copia = df[['Etapa', 'Serie', 'Bloque']].copy()
        filas_df = df_copia.shape[0]
        if not total_escenarios == filas_df:
            logger.error(f'El archivo {nombre_archivo} presenta discrepancia de escenarios esperados.')
            logger.error(f'Escenarios esperados {total_escenarios}, escenarios leidos {filas_df}.')
            e = 'Debido a la incoherencia de datos recibidos se detendra la ejecucion del programa.'
            raise ValueError(e)
    for archivo, df in {'demxbael': df_demxbael, 'gerhid': df_gerhid, 'gergnd':df_gergnd,
                        'gerter':df_gerter}.items():
        validacion_escenarios(archivo, df, total_escenarios)
    
    # generadores y despachos
    def validacion_componentes(na_1, na_2, df_1, df_2):
        componentes_1 = set(df_1.columns.astype(str).str.strip().tolist()[3:])
        componentes_2 = set(df_2['nombre_gen'].astype(str).str.strip().tolist())
        diferencia = componentes_1 - componentes_2
        if len(diferencia)>0:
            logger.error(f'Existe una discrepancia entre los elementos de {na_1} y los declarados en {na_2}.')
            logger.error(f'Los elementos en cuestion son {diferencia}.')
            e = 'Debido a la incoherencia de datos recibidos se detendra la ejecucion del programa.'
            raise ValueError(e)
    validacion_componentes('gerter', 'ctermibo', df_gerter, df_ctermibo)
    validacion_componentes('gerhid', 'chidrobo', df_gerhid, df_chidrobo)
    validacion_componentes('gergnd', 'cgndbo', df_gergnd, df_cgndbo)
    
    # barras y demandas
    cargas = set(df_demxbael.columns.astype(str).str.strip().tolist()[3:])
    diferencia = cargas.issubset(set(df_dbus['nombre_bus'].tolist()))
    if not diferencia:
        logger.error(f'Existe una discrepancia entre los elementos de demxbael y los declarados en dbus.')
        e = 'Debido a la incoherencia de datos recibidos se detendra la ejecucion del programa.'
        raise ValueError(e)
    
    # df_duraci
    long_duraci = datos_estudio['numero_bloques'] * datos_estudio['numero_etapas']
    filas_duraci = df_duraci.shape[0]
    if not filas_duraci == long_duraci:
        logger.error(f'El archivo duraci presenta discrepancia de escenarios esperados.')
        logger.error(f'Escenarios esperados {long_duraci}, escenarios leidos {filas_duraci}.')
        e = 'Debido a la incoherencia de datos recibidos se detendra la ejecucion del programa.'
        raise ValueError(e)
    
    logger.info('Escenarios de despacho, demanda validados.')
    print(f"{'-'*80}")
    return (df_dbus, df_dcirc, df_cgndbo, df_ctermibo, df_chidrobo, df_duraci, df_mcirc, df_gerter,
                df_gerhid, df_gergnd, df_demxbael, df_datos_SDDP)

def coordenadas(ruta_base_sddp: str) -> pd.DataFrame:
    """_Si existe el archivo dbus.csv (que se puede generar en el sddp) se lee y se cargan las coordenadas de cada barra
    en caso de que si existiese y en caso de que no exista el archivo las coordenadas se dejan vacias_
    Args:
        ruta_base_sddp (str): _Ruta de la base de base de datos SDDP_
    raise ValueErrors:
        ValueError: En caso de que el archivo exista pero la informacion de las coordenadas este incompleta o no se
            tengan las coordenaas de ninguna barra
    Returns:
        pd.DataFrame: Devuelve el dbus con las coordenadas por barra
    """
    ruta_coordenadas = Path(ruta_base_sddp) / 'dbus.csv'
    if ruta_coordenadas.exists():
        df = pd.read_csv(ruta_coordenadas, skiprows=1, encoding='latin-1', header=0)
        nombre_columnas = ['id', 'bus', 'sistema', 'area', 'corte de carga', 'voltaje', 'latitud', 'longitud']
        df.columns = nombre_columnas
        df_coord = df[['id', 'bus', 'latitud', 'longitud']].sort_values(by='id')
        nan_mask = df_coord[['latitud', 'longitud']].isna().any(axis=1)
        if nan_mask.any():
            buses_con_error = df_coord.loc[nan_mask, 'bus'].tolist()
            e = (
                f"\nSe encontraron buses sin latitud ni longitud (Verifique los datos).\n"
                f"Nombres de buses: {buses_con_error}\nSe omitira el uso de coordendas")
            logger.warning(e)
            print(f'{'='*80}')
            return pd.DataFrame()
        
        df_coord.set_index(['id'], inplace=True)
        logger.info('Se encontraron las coordenadas en el archivo "dbus.csv".')
        print(f'{'='*80}')
        return df_coord[['bus', 'latitud', 'longitud']]
    else:
        logger.info(f'No se tiene el archivo de las coordenadas en: {ruta_coordenadas}')
        logger.info('Se continuara con la ejecucion del programa sin coordenadas.')
        print(f'{'='*80}')
        return pd.DataFrame()