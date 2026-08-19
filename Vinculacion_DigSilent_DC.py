import pandas as pd
from pathlib import Path
import os
import sys
import logging
from Rutas_y_aux import (crear_carpeta_resultados, desempaquetado_ruta_salida, areas, seleccion_years)
from Red_v2 import (reporte_red)
from Simulador_DC_v3 import (Configuracion_Simulacion,Configuracion_Simulacion_Contingencias, 
                simulador_caso_base_DC)
from Analisis_estadistico_v4 import (analisis_escenarios, analisis_flujos)
from Graficador_red import graficador, graficador_op5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def adquisicion_datos(df_fechas, nombre_carpeta, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
                Slacks, datos_estudio, nucleos):
    print(f'{'='*60}')
    print('Adquisicion de datos de escenarios criticos.')
    print(f'{'='*60}')
    # Pedimos la ruta de la carpeta donde se guardo el analisis de escenarios criticos
    while True:
        ruta_base = input('-> Ingrese a ruta de la carpeta donde se guardo el analisis de los escenarios criticos, o "q" para realizarlo.\n').strip()
        if ruta_base.lower() =='q':
            estudio = True
            print(f'{'='*60}')
            break
        elif (Path(ruta_base).exists() and Path(ruta_base).is_dir()):
            estudio = False
            break
        else:
            print('La ruta no es valida. Intente nuevamente.')
    if estudio:
        print(f'\n{'='*60}')  
        print("[ESCENARIOS] Identificar escenarios criticos.")
        print(f'{'='*60}\n')
        
        # Modificables por el usuario
        print("Configuracion del caso de estudio.\n")
        nombre_del_estudio = str(input('-> Ingrese un nombre para el estudio (no usar ni espacios):')).strip()
        print(f'\n{'='*60}')
        interconexiones = areas()
        lista_years = seleccion_years(df_fechas)
        
        # No modificables
        escenarios = []
        generar_reportes_red = False
        config_sim = Configuracion_Simulacion(titulo_estudio = nombre_del_estudio)
        config_sim_cont = Configuracion_Simulacion_Contingencias(nombre_estudio = nombre_del_estudio)
        top_contingencias = []
        del config_sim_cont
        
        # Rutas de salida
        ruta_salida = crear_carpeta_resultados(nombre_carpeta, nombre_del_estudio)
        (ruta_reporte, ruta_cond_n, ruta_graficas, ruta_contingencias, ruta_rep_cont, ruta_Pip,
        ruta_dgrm_cb, ruta_dgrm_cont, ruta_refuerzos) = desempaquetado_ruta_salida(ruta_salida)
        del (ruta_contingencias, ruta_rep_cont, ruta_Pip, ruta_refuerzos)
        
        # Reportes de lineas, trafos y demas elementos de la red
        reporte_red (net, ruta_reporte, generar_reportes_red)
        
        # --- Ejecucion del caso base ---
        df_cargabilidades, df_flujos = simulador_caso_base_DC(escenarios, net, df_mline, df_mtrafo, df_demanda,
                                            df_desp_TH,df_desp_ren, Slacks, datos_estudio, df_fechas, nucleos,
                                            ruta_cond_n,ruta_reporte, config_sim, generar_reportes_red)
        del df_cargabilidades
        
        df_escenarios, lista_escenarios = analisis_escenarios(df_desp_TH, df_desp_ren, df_demanda,
                                                            ruta_cond_n, ruta_graficas, lista_years, df_fechas)
        del df_escenarios
        
        graficador (net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks, ruta_dgrm_cb,
                    top_contingencias, ruta_dgrm_cont, lista_escenarios)
        
        # --- Analisis de flujos ---
        df_res, lista_completa = analisis_flujos(df_flujos, interconexiones, ruta_cond_n, ruta_graficas, 
                                                lista_years)
        del df_res
        
        # --- Graficar diagrmas de cargab ---
        graficador_op5 (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks,
                    lista_completa, ruta_dgrm_cb)
        print(f"{'='*60}")
        print(f"Los resultados se guardaran en: {ruta_salida}")
        print(f"{'='*60}\n")
        ruta_base = ruta_salida
    ruta_archivos = Path(ruta_base)/'Analisis_DC'/'Condicion_n'
    try:
        esc_crit_p1 = pd.read_csv((ruta_archivos/'Reporte_escenarios_criticos_p1.csv'))
        esc_crit_p2 = pd.read_csv((ruta_archivos/'Reporte_escenarios_criticos_p2.csv'))
    except Exception as e:
        logger.error(f"La carpeta no cuenta con los archivos:\n-> Reporte_escenarios_criticos_p1.csv\n-> Reporte_escenarios_criticos_p2.csv")
        raise e
    # Construccion del df escenarios
    esc_crit_p2['escenario'] = esc_crit_p2['Interconexion'] +'_'+ esc_crit_p2['Lectura'] +'_'+esc_crit_p2['Año'].astype(str)
    esc_crit_p1 = esc_crit_p1[['Escenarios criticos', 'Etapa', 'Serie', 'Bloque']].copy()
    esc_crit_p1.rename(columns={'Escenarios criticos':'Escenarios'}, inplace = True)
    esc_crit_p2 = esc_crit_p2[['escenario', 'Etapa', 'Serie', 'Bloque']].copy()
    esc_crit_p2.rename(columns={'escenario':'Escenarios'}, inplace = True)
    ent = {'Etapa': int, 'Serie': int, 'Bloque': int}
    esc_crit_p2 = esc_crit_p2.astype(ent)
    logger.info('Se cargaron correctamente los escenarios disponibles.')
    print(f"{'='*60}")
    return esc_crit_p1, esc_crit_p2

def escenario_elegido (df_escenarios):
    indices_disponibles = df_escenarios.index.to_list()
    while True:
        indice = input('\nIngrese el indice del escenario a exportar:').strip()
        try:
            indice = int(indice)
        except:
            logger.warning('El indice seleccionado debe ser un numero.')
        if indice in indices_disponibles:
            nombre, etapa, serie, bloque = df_escenarios.loc[indice, ['Escenarios', 'Etapa', 'Serie', 'Bloque']]
            logger.info(f'El escenario elegido es {nombre}(E:{etapa} - S:{serie} - B:{bloque})')
            print(f'{'='*60}')
            return nombre, etapa, serie, bloque
        else: 
            min_idx = df_escenarios.index.min()
            max_idx = df_escenarios.index.max()
            logger.warning(f'El indice seleccionado esta fuera del rango [{min_idx}-{max_idx}].')
            logger.info('Porfavor vuelva a intentarlo.')

def casos_estudio(app, dir_proyecto):
    # funcion auxiliar
    def casos_de_estudio(folder):
        casos = []
        contenido = folder.GetContents()
        for obj in contenido:
            class_name = obj.GetClassName()
            if class_name == 'IntCase':
                casos.append(obj)
            elif class_name == 'IntFolder':
                casos.extend(casos_de_estudio(obj))
        return casos
    # seleccion caso de estudio
    
    folder_estudios = app.GetProjectFolder('study', 1)
    if folder_estudios is None:
        logger.error("No se pudo encontrar la carpeta de casos de estudio.")
    else:
        casos = casos_de_estudio(folder_estudios)
        if not casos:
            logger.error("No se encontraron casos de estudio.")
        else:
            print(f"-> Casos de estudio disponibles: ({len(casos)}):\n")
            for i, caso in enumerate(casos, start=1):
                print(f"{i:>1}. {caso.loc_name}")
            print(f'{'-'*60}')
            while True:
                seleccion = input('Ingrese el numero de caso de estudio (a activarse): ').strip()
                if seleccion.isdigit() and 1 <= int(seleccion) <= len(casos):
                    caso_elegido = casos[int(seleccion) - 1]
                    caso_elegido.Activate()
                    logger.info(f"-> Caso de estudio (activado): {caso_elegido.loc_name}")
                    print(f'{'-'*60}')
                    return [dir_proyecto.split('\\', -1)[-1], caso_elegido.loc_name]
                else:
                    logger.warning(f"-> Opcion invalida, ingrese un número entre 1 y {len(casos)}.")

# seleccion de escenarios por  el usuario
def escenario_digsil(df_esc_p1, df_esc_p2,app, dir_proyecto):
    while True:
        print(f'{'-'*60}\n')
        print('Escenarios criticos disponibles.')
        print('1. Escenarios de despacho (Gen. Sincrona - Gen. Variable) y demanda.')
        print('2. Escenarios de maxima transferencia entre areas.')
        print('3. Para cambiar de caso de estudio.')
        print(f'{'-'*60}')
        opcion = input('Ingrese una opcion [1-3] o "q" para salir:').strip()
        print(f'{'-'*60}')
        if opcion.lower() == 'q':
            logger.info('-> Cerrando el modulo de importacion de escenarios.')
            return None, None
        if opcion == '1':
            print(f'Los escenarios disponibles son:\n{df_esc_p1}')
            nombre, etapa, serie, bloque = escenario_elegido(df_esc_p1)
            escenario = [etapa, serie, bloque]
            return nombre, escenario
        elif opcion == '2':
            print(f'Los escenarios disponibles son:\n{df_esc_p2}')
            nombre, etapa, serie, bloque = escenario_elegido(df_esc_p2)
            escenario = [etapa, serie, bloque]
            return nombre, escenario
        elif opcion =='3':
            x, y = casos_estudio(app, dir_proyecto)
        else:
            logger.error('Opcion no valida. Ingrese un valor entre [1-2]')

def vinculacion_pf():
    while True:
        ruta_usuario = Path(input(f'Ingrese la ruta de DIgSIlent(Ej: ({r'C:\...\DIgSILENT\PowerFactory 2024\Python\3.12)'}):\n').strip())
        if ruta_usuario.exists() and ruta_usuario.is_dir():
            try: 
                ruta_dig = ruta_usuario.parent
                os.environ["PATH"] = rf'{str(ruta_dig)}'+';'+os.environ["PATH"]
                sys.path.append(rf'{str(ruta_usuario)}')
                import powerfactory as pf
                app = pf.GetApplication()
                app.Show()
                logger.info('-> Se vinculo correctamente DigSilent con el programa (Python).\n')
                print(f'{'-'*60}')
                return(app)
            except:
                logger.warning('Revise que la direccion copiada sea correcta.')
        else: 
            logger.warning('La ruta debe ser una la direccion de la carpeta.')

def seleccion_caso_estudio(app):
    # Seleccion base de datos
    print('-> Del modo engine copie la direccion de la base de datos a utilizarse.')
    while True:
        ruta_proyecto = input('Ingrese la ruta de la carpeta pf:\n')
        nombre_usuario, dir_proyecto = ruta_proyecto.split('\\', 1)
        dir_proyecto = dir_proyecto.replace('\\', '\\\\')
        try:
            app.ActivateProject(dir_proyecto)
            app.Hide()
            logger.info(f'-> El usuario seleccionado es: {nombre_usuario}')
            logger.info(f'-> La base de datos es: {dir_proyecto}')
            logger.info('-> Se activo la base de datos correctamente.')
            print(f'{'-'*60}')
            return dir_proyecto
        except:
            logger.error('La ruta de la base de datos no existe o es incorrecta.')

def base_pf(net, app) -> bool:
    """Compara la red pandapower con la red digsilent 
    Solo generadores (Sincronos y renovables) y cargas.
    Args:
        net (_type_): Red pandapower
        app (_type_): Red Digsilent
    Returns:
        True: Si todos los elementos de la red pandapower coinciden con los de digsilent\n
        False: Si por lo menos un elemento de PF o PP no existiese en la otra base\n
        bd_pf: devuelve los diccionarios de generadores y cargas de pf
    """
    print(f'{'='*60}')
    print('Base de datos DigSilent.')
    print(f'{'='*60}')
    
    # Antes de la extraccion de elementos activamos todas las grids disponibles de la base de datos
    print(f'GRIDS')
    folder_red = app.GetProjectFolder('netdat')
    grids = folder_red.GetContents('*.ElmNet')
    for g in grids:
        g.outserv = 0
        logger.info(f'-> Grid activada: {g.loc_name}')
    print(f'{'-'*60}')
    
    # Armamos los diccionarios de generacion y cargas
    print(f'GENERACION')
    # Sincrona
    gen_pf = {}
    generadores_pf = app.GetCalcRelevantObjects('*.ElmSym')
    for i in generadores_pf:
        gen_pf[i.loc_name] = i
    logger.info('-> Se importaron los generadores sincronos.')
    # Renovable
    # Estaticos
    ren_pf = {}
    generadores_estaticos = app.GetCalcRelevantObjects('*.ElmGenstat')
    for i in generadores_estaticos:
        ren_pf[i.loc_name] = i
    # Solares
    generadores_estaticos = app.GetCalcRelevantObjects('*.ElmPvsys')
    for i in generadores_estaticos:
        ren_pf[i.loc_name] = i
    logger.info('-> Se importaron los generadores estaticos.')
    print(f'{'-'*60}')
    
    # CARGAS
    print('CARGAS')
    cargas_pf = {}
    cargas = app.GetCalcRelevantObjects('*.ElmLod')
    for i in cargas:
        cargas_pf[i.loc_name] = i
    logger.info('-> Se importaron las cargas.')
    print(f'{'-'*60}')
    
    # verificamos la existencia de los elementos de pp en pf
    # Funcion auxiliar
    def comparacion_pf_pp(set_pf, set_pp, elemento):
        solo_en_pf = set_pf - set_pp  # PF - PP
        solo_en_pp = set_pp - set_pf  # PP - PF
        if len(solo_en_pf) == 0 and len(solo_en_pp) == 0:
            logger.info(f'-> Existen los mismos {elemento} en PP y PF.')
            return True
        else:
            if len(solo_en_pf) > 0:
                logger.warning(f'-> Se mapearon {len(solo_en_pf)} mas {elemento} en PF que en PP (Faltan en PP).')
                logger.info(f'Los elementos exclusivos de PF son:\n{solo_en_pf}')
            if len(solo_en_pp) > 0:
                logger.warning(f'-> Se mapearon {len(solo_en_pp)} mas {elemento} en PP que en PF (Faltan en PF).')
                logger.info(f'Los elementos exclusivos de PP son:\n{solo_en_pp}')
            return False
    
    print('Comparamos la base de datos pf con la pp.')
    # generadores sincronos
    gen_sin_pf = set(gen_pf.keys())
    gen_sin_pp = set(list(net.gen['name']))
    elemento = 'Gen.Sincrona'
    gen = comparacion_pf_pp(gen_sin_pf, gen_sin_pp, elemento)
    
    # generadores renovables
    gen_ren_pf = set(ren_pf.keys())
    gen_ren_pp = set(list(net.sgen['name']))
    elemento = 'Gen. Renovable'
    sgen = comparacion_pf_pp(gen_ren_pf, gen_ren_pp, elemento)
    
    # cargas
    loads_pf = []
    for _, valor in cargas_pf.items():
        barra = valor.bus1.cterm.loc_name
        loads_pf.append(barra)
    loads_pf = set(loads_pf)
    loads_pp = set(list(net.load['name']))
    elemento = 'cargas'
    carga = comparacion_pf_pp(loads_pf, loads_pp, elemento)
    print(f'{'='*60}')
    comparacion = [gen, sgen, carga]
    bd_pf = [gen_pf, ren_pf, cargas_pf]
    return [all(comparacion), bd_pf]

def DigSilent(bd_pf, escenario, df_desp_TH, df_desp_ren, Slacks, df_demanda, app):
    print(f'{'='*60}')
    print('Actualizacion de despachos y demandas.')
    print(f'{'='*60}')
    
    # Desempaquetamos los datos
    etapa, serie, bloque = escenario
    gen_pf, ren_pf, cargas_pf = bd_pf
    logger.info(f'-> El escenario seleccionado es E:{etapa} - S:{serie} - B:{bloque} .')
    # Actualizamos generadores
    # Sincronos
    for llave, valor in gen_pf.items():
        valor.SetAttribute('ip_ctrl', 0) # seteamos al inicio que ningun gen es slack
        p = df_desp_TH.loc[(etapa, serie, bloque), llave]
        valor.SetAttribute('pgini', p) # asignamos la potencia
    # Caso de gen renovable
    for llave, valor in ren_pf.items():
        valor.SetAttribute('ip_ctrl', 0) # seteamos al inicio que ningun gen es slack
        p = df_desp_ren.loc((etapa, serie, bloque), llave)
        valor.SetAttribute('pgini', p) # asignamos la potencia
    logger.info('-> Se asignaron correctamente las potencias de despacho para los generadores (Sinc - Renov).')
    
    # Seteamos el gen Slack
    slack = Slacks.at[(etapa, serie, bloque)]
    gen_pf[slack].SetAttribute('ip_ctrl', 1)
    logger.info(f'-> Para el escenario actual la maquina slack es {slack}.')
    
    # Actualizamos cargas
    for llave, valor in cargas_pf.items():
        p = df_demanda.loc[(etapa, serie, bloque), valor.bus1.cterm.loc_name]
        valor.SetAttribute('plini', p)
    logger.info('-> Se asignaron correctamente las potencias de carga para las barras.')
    
    # Flujo de potencia en DC
    ldf =app.GetFromStudyCase('ComLdf')
    ldf.iopt_net = 2
    app.Show()
    ldf.Execute()
    logger.info('-> Se ejecuto correctamente el flujo por el metodo DC.')
    print(f'{'='*60}')

# funcion principal
def cargar_escenario_pf(df_fechas, nombre_carpeta, net, df_mline, df_mtrafo, df_demanda,
                                df_desp_TH, df_desp_ren, Slacks, datos_estudio, nucleos):
    
    print(f'{'='*60}')
    print('Vinculacion con DigSilent.')
    print(f'{'='*60}')
    # Vinculamos con Digsilent
    app = vinculacion_pf()
    dir_proyecto = seleccion_caso_estudio(app)
    name_bd, name_ce = casos_estudio(app, dir_proyecto)
    igualdad, bd_pf = base_pf(net, app)
    df_esc_p1, df_esc_p2 = adquisicion_datos(df_fechas, nombre_carpeta, net, df_mline, df_mtrafo, df_demanda,
                                df_desp_TH, df_desp_ren, Slacks, datos_estudio, nucleos)
    while True:
        nombre, escenario = escenario_digsil(df_esc_p1, df_esc_p2, app, dir_proyecto)
        if nombre == None and escenario==None:
            print(f'{'='*60}')
            break
        if igualdad:
            DigSilent(bd_pf, escenario, df_desp_TH, df_desp_ren, Slacks, df_demanda, app)
