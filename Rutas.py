from pathlib import Path
from Configuracion_inicial import input_log
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ruta_bd_SDDP()->tuple[Path, str]:
    print(f'\n{'='*80}')
    print('RUTA BASE DE DATOS SDDP.')
    print(f'{'='*80}')
    while True:
        ruta_sddp=input_log('Ingrese la ruta de la base de datos SDDP:').strip()
        ruta_sddp = ruta_sddp.replace('"', '').replace("'", "")
        if ruta_sddp =="":
            logger.warning('No ingreso ninguna ruta. Ingrese una direccion valida.')
            print(f'{'-'*80}')
        else:
            try: 
                ruta_bd=Path(ruta_sddp)
            except:
                logger.error(f'La ruta ingresada {ruta_sddp} no es una direccion valida.')
                print(f'{'-'*80}')
            
            if not ruta_bd.exists():
                logger.warning(f'La ruta: {ruta_bd} no existe.')
                print(f'{'-'*80}')
            elif not ruta_bd.is_dir():
                logger.warning(f'La ruta: {ruta_bd} no es una carpeta.')
                print(f'{'-'*80}')
            else:
                nombre_bd = ruta_bd.name
                print(f'{'='*80}')
                return (ruta_bd, nombre_bd)

def carpeta_principal():
    ruta_origen = Path(__file__).resolve().parent.parent
    ruta_principal = Path(ruta_origen)/f'Estudio_electrico_{datetime.now().strftime(f'%Y-%m-%d-%H-%M')}'
    ruta_principal.mkdir(parents=True, exist_ok=True)
    return ruta_principal

def carpetas_OP1(ruta_carpeta_base: str | Path, nombre_bd : str):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op1_{nombre_bd}_(D.Completo)"
    rta_cn = ruta_base / "1. Condicion_n"
    rta_cn_graf = ruta_base / "1. Condicion_n/1. Graficas"
    rta_ctg_pip = ruta_base / "2. Contingencias/1. Reportes_PIp"
    rta_ctg = ruta_base / "2. Contingencias"
    rta_ctg_fp = ruta_base / "2. Contingencias/2. Flujos_cargabilidades(n-1)"
    rta_ctg_dgm = ruta_base / "2. Contingencias/3. Diagramas_condicion(n-1)"
    rta_reportes = ruta_base / "3. Reportes"
    rta_prop = ruta_base / "4. Propuesta refuerzos"
    subcarpetas = [
        rta_cn_graf,  
        rta_ctg_pip,
        rta_ctg_fp,
        rta_ctg_dgm,
        rta_ctg,
        rta_reportes,
        rta_prop
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (rta_reportes, rta_cn, rta_cn_graf, rta_ctg, rta_ctg_fp, rta_ctg_pip, rta_ctg_dgm, rta_prop,
            ruta_base)

def creacion_carpetas_refuerzos (ruta_refuerzos, nombre_del_estudio, num):
    # Carpeta principal
    ruta_ref = Path(ruta_refuerzos)/f'{num}. {nombre_del_estudio}'
    ruta_ref.mkdir(parents=True, exist_ok=True)
    # Sub carpetas
    ruta_caso_base = ruta_ref/'1. Condicion_n'
    ruta_caso_base.mkdir(parents=True, exist_ok=True) 
    ruta_reporte_red = ruta_ref/'3. Reportes'
    ruta_reporte_red.mkdir(parents=True, exist_ok=True) 
    ruta_graf = ruta_caso_base/'1. Graficas'
    ruta_graf.mkdir(parents=True, exist_ok=True)
    ruta_cont = ruta_ref/'2. Contingencias'
    ruta_cont.mkdir(parents=True, exist_ok=True) 
    ruta_pip = ruta_cont/'1. Reportes_PIp'
    ruta_pip.mkdir(parents=True, exist_ok=True) 
    return (ruta_caso_base, ruta_reporte_red, ruta_graf, ruta_cont, ruta_pip, ruta_ref)

def carpetas_OP2(ruta_carpeta_base: str | Path, nombre_bd : str, nombre_excel_refuerzos: str):
    ruta_carpeta_base = Path(ruta_carpeta_base).parent
    ruta_base = ruta_carpeta_base / f"Op2_{nombre_bd}_(A.Refuerzos)_({nombre_excel_refuerzos})"
    rta_cart = ruta_base / "1. Carteras"
    rta_econ = ruta_base / "2. Informacion economica"
    rta_top_prev = ruta_base / "3. Topologia previa"
    subcarpetas = [
        rta_econ,  
        rta_top_prev
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (ruta_base, rta_cart, rta_econ, rta_top_prev)

def carpetas_OP3_sep(ruta_carpeta_base: str | Path, nombre_bd : str):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op3_{nombre_bd}_(Esc.Criticos)"
    rta_esc = ruta_base / "1. Escenarios criticos"
    ruta_reporte_red = ruta_base / "1. Escenarios criticos" / "0. Despachos - demandas - topologia"
    rta_infred = ruta_base / "2. Informacion de la red"
    rta_cn = ruta_base / "3. Condicion_n"
    subcarpetas = [
        rta_cn,
        rta_esc,  
        rta_infred,
        ruta_reporte_red
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (ruta_base, rta_cn, rta_esc, rta_infred, ruta_reporte_red)

def carpetas_OP3_cep(ruta_carpeta_base: str | Path, nombre_bd : str):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op3_{nombre_bd}_(Esc.Criticos)"
    rta_esc = ruta_base / "1. Escenarios criticos"
    rta_infred = ruta_base / "2. Informacion de la red"
    subcarpetas = [
        rta_esc,  
        rta_infred,
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (ruta_base, rta_esc, rta_infred)

def carpetas_op3_individual(rta_esc, id, year):
    ruta_yyyy = rta_esc/f'{id}. {year}'
    ruta_diagramas = ruta_yyyy/'1. Diagramas(Cargabilidad)'
    ruta_graficas = ruta_yyyy/'2. Graficas'
    subcarpetas = [
        ruta_yyyy,  
        ruta_diagramas,
        ruta_graficas
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return ruta_yyyy, ruta_diagramas, ruta_graficas

def carpetas_OP4(ruta_carpeta_base: str | Path, nombre_bd : str):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op1_{nombre_bd}_(D.Completo)"
    rta_cn = ruta_base / "1. Condicion_n"
    rta_cn_graf = ruta_base / "1. Condicion_n/1. Graficas"
    rta_ctg_pip = ruta_base / "2. Contingencias/1. Reportes_PIp"
    rta_ctg = ruta_base / "2. Contingencias"
    rta_ctg_fp = ruta_base / "2. Contingencias/2. Flujos_cargabilidades(n-1)"
    rta_ctg_dgm = ruta_base / "2. Contingencias/3. Diagramas_condicion(n-1)"
    rta_reportes = ruta_base / "3. Reportes"
    subcarpetas = [
        rta_cn_graf,  
        rta_ctg_pip,
        rta_ctg_fp,
        rta_ctg_dgm,
        rta_ctg,
        rta_reportes,
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (rta_reportes, rta_cn, rta_cn_graf, rta_ctg, rta_ctg_fp, rta_ctg_pip, rta_ctg_dgm,
            ruta_base)

def carpetas_OP5(ruta_carpeta_base: str | Path, nombre_bd : str, llave_contingencias: bool):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op5_{nombre_bd}_(Flujos)"
    rta_cn = ruta_base / "1. Condicion_n"
    rta_flw = ruta_base / "1. Condicion_n/1. Flujos_escenario"
    rta_dgm = ruta_base / "1. Condicion_n/2. Diagramas cargabilidad"
    rta_reportes = ruta_base / "3. Reportes"
    if llave_contingencias:
        rta_ctg_pip = ruta_base / "2. Contingencias/1. Reportes_PIp"
        rta_ctg = ruta_base / "2. Contingencias"
        rta_ctg_fp = ruta_base / "2. Contingencias/2. Flujos_cargabilidades(n-1)"
        rta_ctg_dgm = ruta_base / "2. Contingencias/3. Diagramas_condicion(n-1)"
        subcarpetas = [
            rta_flw,
            rta_dgm, 
            rta_ctg_pip,
            rta_ctg_fp,
            rta_ctg_dgm,
            rta_ctg,
            rta_reportes,
        ]
        for sub in subcarpetas:
            sub.mkdir(parents=True, exist_ok=True)
        return (rta_cn, rta_flw, rta_dgm, rta_ctg_pip, rta_ctg_fp, rta_ctg_dgm, rta_ctg, rta_reportes)
    else:
        subcarpetas = [
            rta_flw,
            rta_dgm,
            rta_reportes,
        ]
        for sub in subcarpetas:
            sub.mkdir(parents=True, exist_ok=True)
        logger.info('Al no haber contingencias no se crearan las carpetas correspondientes al analisis de contingencias.')
        return (rta_cn, rta_flw, rta_dgm, None, None, None, None, rta_reportes)

def carpetas_OP6_sep(ruta_carpeta_base: str | Path, nombre_bd : str):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op6_{nombre_bd}_(Graficas)"
    rta_cn = ruta_base / "1. Condicion_n"
    rta_ctg_pip = ruta_base / "2. Contingencias/1. Reportes_PIp"
    rta_ctg = ruta_base / "2. Contingencias"
    rta_ctg_fp = ruta_base / "2. Contingencias/2. Flujos_cargabilidades(n-1)"
    subcarpetas = [
        rta_cn,
        rta_ctg_pip,
        rta_ctg,
        rta_ctg_fp,
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (rta_cn, rta_ctg_pip,rta_ctg, rta_ctg_fp)

def pedir_ruta(ruta_bd: Path) -> Path:
    nombre_bd = ruta_bd.name
    print("=" * 80)
    prefijos = ["Op1", "Op4"]
    while True:
        entrada_usuario = input_log('Ingrese la ruta del diagnostico de la red de transmision: ').strip()
        print("-" * 80)
        entrada_limpia = entrada_usuario.replace('"', '').replace("'", "")
        ruta = Path(entrada_limpia)
        if not ruta.exists():
            logger.error('La ruta ingresada no existe en el sistema de archivos.')
            logger.info('Intente introducir una ruta valida (ej. C:/.../Estudio_electrico_...)')
            continue
        carpeta_encontrada = None
        for prefijo in prefijos:
            patron = f"{prefijo}_{nombre_bd}_*"
            coincidencias = list(ruta.glob(patron))
            if coincidencias:
                carpeta_encontrada = coincidencias[0]
                break
        if carpeta_encontrada:
            logger.info('Se encontro la carpeta de diagnostico de la red de transmision.')
            logger.info(f'La carpeta es: {carpeta_encontrada}.')
            print("=" * 80)
            return Path(carpeta_encontrada)
        else:
            logger.warning('No se encontro la carpeta de diagnostico de la red de transmision.')
            logger.warning(f'No hay coincidencia con los patrones {prefijos} para la base "{nombre_bd}" en {ruta}')

def carpeta_existente(ruta_carpeta_base):
    # FUNCION AUXILIAR (VALIDACION)
    def validar_carpeta():
        print('-'*80)
        while True:
            ruta_carpeta = input_log('Ingrese la ruta de la carpeta:')
            ruta_carpeta = ruta_carpeta.replace('"', '').replace("'", "")
            try:
                ruta_carpeta = Path(ruta_carpeta)
                print('-'*80)
                return ruta_carpeta
            except:
                logger.info('La ruta ingresada no es una direccion de una carpeta, ingrese nuevamente.')
                print('-'*80)

    print('-'*80)
    while True:
        usar_carpeta = input_log('Quiere almacenar los resultados en una carpeta ya creada?[S/N]:')
        print('-'*80)
        if usar_carpeta.strip().lower() == 's':
            ruta_bd = validar_carpeta()
            return ruta_bd, True
        elif usar_carpeta.strip().lower() == 'n':
            print('-'*80)
            return ruta_carpeta_base, False
        else:
            logger.warning('Opcion no valida, Seleccione entre: [S/N]')
            print('-'*80)

def ruta_escenarios_criticos ():
    print('='*80)
    print('LECTURA DE ESCENARIOS CRITICOS')
    while True:
        print('='*80)
        ruta_estudio = input_log('Ingrese la ruta de la carpeta donde se almaceno el estudio de escenarios criticos ["q" para volver al menu]:\n').strip()
        ruta_estudio = ruta_estudio.replace('"', '').replace("'", "")
        if ruta_estudio.lower() == 'q':
            return ""
        elif (Path(ruta_estudio).exists() and Path(ruta_estudio).is_dir()):
            logger.info(f'La ruta: {ruta_estudio} existe.')
            try:
                ruta_escenarios = Path(ruta_estudio)/'Op3_BD_LP_(Esc.Criticos)'/'1. Escenarios criticos'
                print('='*80)
                return Path(ruta_estudio), Path(ruta_escenarios)
            except:
                logger.info('La carpeta de escenarios criticos no existe, porfavor realice el estudio o cambie de carpeta')
        else:
            logger.warning('Ingrese una ruta valida.')
            print('='*80)

def carpetas_OP7(ruta_carpeta_base: str | Path, nombre_bd : str):
    ruta_carpeta_base = Path(ruta_carpeta_base)
    ruta_base = ruta_carpeta_base / f"Op7_{nombre_bd}_(DigSilent)"
    rta_par = ruta_base / "1. Informacion_Pareo"    
    rta_ac = ruta_base / "2. Analisis_AC"
    subcarpetas = [
        rta_par,
        rta_ac,
    ]
    for sub in subcarpetas:
        sub.mkdir(parents=True, exist_ok=True)
    return (rta_par, rta_ac)