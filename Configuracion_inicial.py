from pathlib import Path
from datetime import datetime
from multiprocessing import cpu_count
import sys
import os
import stat
import logging
import shutil
import atexit
import warnings
import json

LOGGER_ACTIVADO = False
ARCHIVO_LOG = None
STDOUT_ORIGINAL = None
STDERR_ORIGINAL = None
HANDLERS_LOGGER = []
RUTA_LOG_ACTUAL = None
ATEXIT_REGISTRADO = False

class Tee:
    def __init__(self, terminal, archivo):
        self.terminal = terminal
        self.archivo = archivo
    def write(self, mensaje):
        try:
            self.terminal.write(mensaje)
            self.terminal.flush()
        except Exception:
            pass
        try:
            if self.archivo is not None and not self.archivo.closed:
                self.archivo.write(mensaje)
                self.archivo.flush()
        except Exception:
            pass
    def flush(self):
        try:
            self.terminal.flush()
        except Exception:
            pass
        try:
            if self.archivo is not None and not self.archivo.closed:
                self.archivo.flush()
        except Exception:
            pass

def configurar_logger_txt(
    ruta_salida,
    nombre_archivo="Reporte_ejecucion.txt",
    nivel=logging.INFO):
    global LOGGER_ACTIVADO
    global ARCHIVO_LOG
    global STDOUT_ORIGINAL
    global STDERR_ORIGINAL
    global HANDLERS_LOGGER
    global RUTA_LOG_ACTUAL
    global ATEXIT_REGISTRADO
    if LOGGER_ACTIVADO:
        logging.info("El capturador de salida ya estaba activado.")
        return RUTA_LOG_ACTUAL
    LOGGER_ACTIVADO = True
    ruta_salida = Path(ruta_salida)
    ruta_salida.mkdir(parents=True, exist_ok=True)
    ruta_log = ruta_salida / nombre_archivo
    RUTA_LOG_ACTUAL = ruta_log
    ARCHIVO_LOG = open(ruta_log, "a", encoding="utf-8", buffering=1)
    STDOUT_ORIGINAL = sys.stdout
    STDERR_ORIGINAL = sys.stderr
    ARCHIVO_LOG.write("\n")
    ARCHIVO_LOG.write("=" * 90 + "\n")
    ARCHIVO_LOG.write(f"INICIO DE EJECUCION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    ARCHIVO_LOG.write("=" * 90 + "\n\n")
    ARCHIVO_LOG.flush()
    sys.stdout = Tee(STDOUT_ORIGINAL, ARCHIVO_LOG)
    sys.stderr = Tee(STDERR_ORIGINAL, ARCHIVO_LOG)
    logging.captureWarnings(True)
    warnings.simplefilter("default")
    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(nivel)
    for handler in logger_raiz.handlers[:]:
        try:
            handler.flush()
            handler.close()
        except Exception:
            pass
        logger_raiz.removeHandler(handler)
    formato = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    handler_consola = logging.StreamHandler(STDOUT_ORIGINAL)
    handler_consola.setLevel(nivel)
    handler_consola.setFormatter(formato)
    handler_archivo = logging.FileHandler(
        ruta_log,
        mode="a",
        encoding="utf-8"
    )
    handler_archivo.setLevel(nivel)
    handler_archivo.setFormatter(formato)
    logger_raiz.addHandler(handler_consola)
    logger_raiz.addHandler(handler_archivo)
    HANDLERS_LOGGER = [handler_consola, handler_archivo]
    if not ATEXIT_REGISTRADO:
        atexit.register(cerrar_logger_txt)
        ATEXIT_REGISTRADO = True
    logging.info(f"Registro de ejecucion activado: {ruta_log}")
    return ruta_log

def cerrar_logger_txt():
    global LOGGER_ACTIVADO
    global ARCHIVO_LOG
    global STDOUT_ORIGINAL
    global STDERR_ORIGINAL
    global HANDLERS_LOGGER
    global RUTA_LOG_ACTUAL
    if not LOGGER_ACTIVADO:
        return
    try:
        logging.info("Cerrando reporte de ejecucion actual.")
    except Exception:
        pass
    logger_raiz = logging.getLogger()
    # Cerrar handlers del logger
    try:
        for handler in HANDLERS_LOGGER:
            try:
                handler.flush()
                handler.close()
            except Exception:
                pass
            try:
                logger_raiz.removeHandler(handler)
            except Exception:
                pass
        HANDLERS_LOGGER = []
    except Exception:
        pass
    # Restaurar consola original
    try:
        if STDOUT_ORIGINAL is not None:
            sys.stdout = STDOUT_ORIGINAL
        if STDERR_ORIGINAL is not None:
            sys.stderr = STDERR_ORIGINAL
    except Exception:
        pass
    # Cerrar archivo TXT
    try:
        if ARCHIVO_LOG is not None and not ARCHIVO_LOG.closed:
            ARCHIVO_LOG.write("\n")
            ARCHIVO_LOG.write("=" * 90 + "\n")
            ARCHIVO_LOG.write(
                f"FIN DE EJECUCION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            ARCHIVO_LOG.write("=" * 90 + "\n")
            ARCHIVO_LOG.flush()
            ARCHIVO_LOG.close()
    except Exception:
        pass
    LOGGER_ACTIVADO = False
    ARCHIVO_LOG = None
    STDOUT_ORIGINAL = None
    STDERR_ORIGINAL = None
    RUTA_LOG_ACTUAL = None

def cambiar_ubicacion_logger_txt(nueva_ruta_salida, nombre_archivo="Reporte_ejecucion.txt", nivel=logging.INFO):
    cerrar_logger_txt()
    nueva_ruta_salida = Path(nueva_ruta_salida)
    print(f"{'-'*80}")
    return configurar_logger_txt(
        ruta_salida=nueva_ruta_salida,
        nombre_archivo=nombre_archivo,
        nivel=nivel
    )

# --- FUNCION PARA LOS INPUTS ---
def input_log(mensaje: str) -> str:
    valor = input(f'{mensaje}')
    print(f"> {valor}")
    return valor

# --- ELIMINAR CARPETA CREADA PARA LA OP 2 ---
def eliminar_carpeta(ruta_carpeta):
    def manejar_error_permiso(func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    if os.path.exists(ruta_carpeta):
        try:
            shutil.rmtree(ruta_carpeta, onexc=manejar_error_permiso)
        except Exception as e:
            print(f"No se pudo eliminar la carpeta por completo: {e}")

# configuacion preeterminada por estudio
"""
generar_reportes_red (1 todos los reportes de topologia, 2 solo lineas, trafos y barras, 3 nada)
reportes_cb (True genera reportes de la simualcion en condicion n)
reportes_DDT Reportes despacho demanda y topologia
generar_graficas Para graficas de por elemento critico identificado
"""

# --- Nucleos para el multiprocessing ---
def hilos_procesamiento ():
    nucleos = min(18, max(4, int(cpu_count()*0.75)))
    return nucleos

config_predeterminada = {
    "opcion_1": {
        "reporte_red" : 1,
        "reportes_cn_flujos" : True,
        "reporte_topologia" : False,
        "exponente_n" : 40,
        "nucleos" : hilos_procesamiento(),
        "generar_graficas" : True,
        "reportes_cont_flujos" : False,
        "numero_refuerzos_automaticos": 7
    },
    "opcion_2": {
        "elementos_monitoreo" : 3,
        "reporte_red" : 1,
        "reportes_cn_flujos" : True,
        "reporte_topologia" : True,
        "exponente_n" : 40,
        "nucleos" : hilos_procesamiento(),
        "generar_graficas" : True,
        "reportes_cont_flujos" : True,
        "Factor_dolar" : 1.3118, 
        "Factor_inflacion" : .62,
        "numero_refuerzos_automaticos": 3,
        "modo_elementos_monitoreo": 1,
        "n_elementos_sensibles": 10,
        "guardar_reportes_contingencias": False,
        "guardar_reporte_economico": True,
        "guardar_reporte_tecnico_economico": True
    },
    "opcion_3": {
        "reporte_red" : 1,
        "reporte_topologia" : False,
        "nucleos" : hilos_procesamiento(),
        "reportes_cn_flujos" : True,
    },
    "opcion_5": {
        "exponente_n" : 40,
        "reportes_cn_flujos" : True,
        "reporte_topologia" : True,
        "generar_graficas" : False,
        "reportes_cont_flujos" : True,
        "nucleos" : hilos_procesamiento(),
    },
        "opcion_6": {
        "exponente_n" : 40,
        "reportes_cn_flujos" : True,
        "reporte_topologia" : False,
        "generar_graficas" : False,
        "reportes_cont_flujos" : True,
        "nucleos" : hilos_procesamiento(),
    }
}

def cargar_configuracion(ruta_config: str | Path) -> dict:
    ruta_config = Path(ruta_config)/"config_estudio.json"
    if not ruta_config.exists():
        crear_config_default(ruta_config)
    with open(ruta_config, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config

def guardar_configuracion(config: dict, ruta_config: str | Path = "config_estudio.json"):
    ruta_config = Path(ruta_config)
    with open(ruta_config, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def crear_config_default(ruta_config: str | Path):
    ruta_config = Path(ruta_config)
    with open(ruta_config, "w", encoding="utf-8") as f:
        json.dump(config_predeterminada, f, indent=4, ensure_ascii=False)
    return ruta_config

def config_estudio(op_estudio: str, ruta_config: str | Path) -> dict:
    while True:
        x = input_log('Usar configuracion predeterminada (s/n):').strip().lower()
        print(f"{'-'*80}")
        config_completa = cargar_configuracion(ruta_config)
        if x == 's':
            print(f"Cargando configuracion predeterminada para: {op_estudio}")
            print(f"{'-'*80}")
            return config_completa[op_estudio]
            
        elif x == 'n':
            print(f"MODIFICACION MANUAL DE PARAMETROS - {op_estudio.upper()}")
            print(f"{'-'*80}")
            for llave, valor_original in config_completa[op_estudio].items():
                nuevo_valor_str = input_log(f"-> {llave} (Actual: {valor_original}): ").strip()
                if nuevo_valor_str == "":
                    continue
                if isinstance(valor_original, bool):
                    config_completa[op_estudio][llave] = nuevo_valor_str.lower() in ['s', 'si', 'true', '1']
                elif isinstance(valor_original, int):
                    config_completa[op_estudio][llave] = int(nuevo_valor_str)
                elif isinstance(valor_original, float):
                    config_completa[op_estudio][llave] = float(nuevo_valor_str)
                else:
                    config_completa[op_estudio][llave] = nuevo_valor_str
            ruta_archivo_json = Path(ruta_config) / "config_estudio.json"
            guardar_configuracion(config_completa, ruta_archivo_json)
            print("Configuración de ejecucion personalizada guardada.")
            print(f"{'-'*80}")
            return config_completa[op_estudio]
        else:
            print('Opcion no valida. Elija entre "s" o "n".')
            print(f"{'-'*80}")

# --- MONITOREO DE CONTINGENCIAS ---
def monitoreo_contingencias()-> int:
    print(f'{'='*80}')
    print('IDENTIFICACION DE ELEMENTOS SENSIBLES.')
    print(f'{'='*80}\n')
    print('1. Solo los elementos de monitoreo declarados en el archivo de refuerzos.')
    print('2. Monitoreo de n elementos sensibles al ingreso del refuerzo.')
    print(f'{'-'*80}')
    while True:
        opcion = input('Seleccione una opcion (1-2): ').strip()
        if opcion in '1':
            print('Se usaran solo los elementos declarados en el excel.')
            print('En caso de no haber elementos declarados el programa identificara los 3 elementos mas sensibles'+
                        '\na la conexion del refuerzo.')
            print(f'{'='*80}')
            return 3
        elif opcion == '2':
            while True:
                elementos = input_log('Ingrese el numero de elementos a monitorear:')
                if int(elementos)>0:
                    print(f'Se identificaran los {elementos} elementos mas sensibles.')
                    print(f'En caso de que se haya declarado elementos de monitoreo en el excel los se uniran ambas'+
                                '\nlistas y se eleiminaran duplicados.')
                    print(f'{'='*80}')
                    return int(elementos)
                else:
                    e=f'Debe ingresar un numero entero mayor a 0. {elementos} no es numero entero o no es mayor a 0.'
                    print(e)
                    print(f'{'-'*80}')
        else:
            print('Opcion no valida, intente de nuevo.')


def config_estudio_2(op_estudio: str, ruta_config: str | Path) -> dict:
    while True:
        x = input_log('Usar configuracion predeterminada (s/n):').strip().lower()
        print(f"{'-'*80}")
        config_completa = cargar_configuracion(ruta_config)
        if x == 's':
            print(f"Cargando configuracion predeterminada para: {op_estudio}\n")
            print(f"{'-'*80}")
            return config_completa[op_estudio]
            
        elif x == 'n':
            print(f"MODIFICACION MANUAL DE PARAMETROS - {op_estudio.upper()}")
            print(f"{'-'*80}")
            config_completa[op_estudio]['elementos_monitoreo'] =  monitoreo_contingencias()
            ruta_archivo_json = Path(ruta_config) / "config_estudio.json"
            guardar_configuracion(config_completa, ruta_archivo_json)
            print("Configuración de ejecucion personalizada guardada.")
            print(f"{'-'*80}")
            return config_completa[op_estudio]
        else:
            print('Opcion no valida. Elija entre "s" o "n".')
            print(f"{'-'*80}")