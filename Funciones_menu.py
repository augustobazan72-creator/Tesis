from pandas import DataFrame as df
from numpy import linspace
from pandas import Series as sr
from datetime import datetime
from pathlib import Path
import logging
import re
from numpy import arange
from Rutas import (carpetas_OP1, carpetas_OP2, carpetas_OP3_cep, carpetas_OP3_sep, carpetas_OP4, carpetas_OP5, carpetas_OP6_sep,
                pedir_ruta, carpeta_existente, carpetas_OP7)
from Configuracion_inicial import config_estudio, config_estudio_2, cambiar_ubicacion_logger_txt, eliminar_carpeta, input_log
from Motor_DC import (Configuracion_Simulacion, Configuracion_Simulacion_Contingencias, caso_base_completo,
                contingencias_transmision, caso_base_escenarios, contingencias_op5)
from Analisis_estadistico import analisis_caso_base, analisis_contingencias, analisis_escenarios, analisis_flujos
from Red_pandapower import reporte_red, trafos_gen
from Diagramas_cargabilidad import (graficador_op1, graficador_op3_p1, graficador_op3_p2, graficador_op5_rb, graficador_op5_ctg,
                                    graficador_condicion_n, graficador_contingencias, graficador_pip)
from Resultados import grafica_elementos_criticos, resultados_diagnostico, resultados_refuerzos_propuestos, resultados_escenarios_criticos
from Refuerzos import analisis_ref_popuestos, ruta_refuerzos_usuario, refuerzos_usuario
from Procesamiento_bd import distancias_lineas
from Lector_excels import lectura_excel_refuerzos, lectura_flujos, lectura_escenarios
from Analisis_economico import costos
from Menus import (menu_seleccion_yyyy, menu_seleccion_areas, menu_graficador, pedir_contingencias, pedir_contingencias_graficador,
                graficador_contingencias_o_pip)
from Exportacion_PF import menu_vinculacion_pf

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

def opcion_DC_1(df_mtrafo: df, df_demanda: df, df_desp_TH: df, df_desp_ren: df, df_mline: df, df_fechas: df,
                datos_estudio: dict,  Slacks: sr, df_duraci:df, ruta_carpeta_base: str|Path, 
                nombre_bd: str, diagnostico: bool, parametros_red, net):
    print(f'\n{'='*80}')
    if diagnostico:
        print("[DIAGNOSTICO] Diagnostico de la red de transmision (Completo).")
    else:
        print("[DIAGNOSTICO] Diagnostico de la red de transmision (Reducido).")
    print(f'{'='*80}')
    
    # --- CREACION DE RUTAS (SALIDA) ---
    if diagnostico:
        (rta_reportes, rta_cn, rta_cn_graf, rta_ctg, rta_ctg_fp, rta_ctg_pip, rta_ctg_dgm,
                rta_prop, ruta_base) = carpetas_OP1(ruta_carpeta_base, nombre_bd)
    else:
        (rta_reportes, rta_cn, rta_cn_graf, rta_ctg, rta_ctg_fp, rta_ctg_pip, rta_ctg_dgm,
            ruta_base) = carpetas_OP4(ruta_carpeta_base, nombre_bd)
    
    # --- CONFIGURACION INICIAL ESTUDIO ---
    nombre_estudio = f'{nombre_bd}({datetime.now().strftime(f'%H-%M')})'
    configuracion_estudio = config_estudio("opcion_1", ruta_carpeta_base)
    configuracion_red_base = Configuracion_Simulacion(nombre_estudio)
    configuracion_contingencias = Configuracion_Simulacion_Contingencias(nombre_estudio,
                                                            configuracion_estudio['exponente_n'])
    nucleos = configuracion_estudio['nucleos']
    
    # --- REPORTES DE TOPOLOGIA DE LA RED ---
    reporte_red (net, rta_reportes, configuracion_estudio['reporte_red'])
    trafos_limpios = trafos_gen(net)
    
    # --- SIMULACION CONDICION N ----
    df_cargabilidades, df_flujos = caso_base_completo (net, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                    df_desp_ren, Slacks, datos_estudio, df_fechas, nucleos, rta_cn, rta_reportes,
                    configuracion_red_base, configuracion_estudio['reportes_cn_flujos'],
                    configuracion_estudio['reportes_cn_flujos'])
    
    # --- ANALISIS CONDICION N ---
    analisis_componentes = analisis_caso_base (df_cargabilidades, df_flujos, df_duraci,
            net, datos_estudio, parametros_red, rta_cn, configuracion_estudio['generar_graficas'],
            rta_cn_graf, nucleos, trafos_limpios)
    
    # --- ANALISIS CONDICION N-1 (CONTINGENCIAS) ---
    indice_severidad = contingencias_transmision(configuracion_contingencias, net, df_mline, df_mtrafo, 
                    df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, rta_ctg_fp,
                    rta_ctg_pip, df_duraci, nucleos, configuracion_estudio['reportes_cont_flujos'], 
                    trafos_limpios)
    top_contingencias, ranking_contingencias  = analisis_contingencias(indice_severidad, rta_ctg,
                                                rta_ctg_pip, configuracion_contingencias)
    
    # --- RESULTADOS CONDICION N Y CONTINGENCIAS ---
    grafica_elementos_criticos(analisis_componentes, rta_cn)
    resultados = resultados_diagnostico(analisis_componentes, ranking_contingencias, df_duraci,
                        ruta_base, nombre_estudio, datos_estudio)
    
    # --- GENERADOR DE DIAGRAMAS PARA CONTINGENCIAS MAS SEVERAS ---
    graficador_op1 (net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks,
                        top_contingencias, rta_ctg_dgm)

    # --- ANALISIS DE REFUERZOS PROPUESTOS POR EL PROGRAMA ---
    if diagnostico:
        ref_propuestos = analisis_ref_popuestos(net, analisis_componentes, ranking_contingencias, rta_prop,
                        df_mline, df_mtrafo, df_demanda, df_desp_TH,df_desp_ren, Slacks, datos_estudio, df_fechas, 
                        df_duraci, parametros_red, configuracion_estudio['exponente_n'], nucleos,
                        df_cargabilidades, configuracion_estudio['numero_refuerzos_automaticos'], trafos_limpios)
        resultados_refuerzos_propuestos(resultados, ref_propuestos)
    return ruta_base

def opcion_DC_2(df_cargabilidades_rbase, ranking_contingencias_rb, ruta_diagnostico, nombre_bd, net, df_coord,
                    df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, df_duraci,
                    parametros_red, df_mline):
    print(f'\n{'='*80}')  
    print("[REFUERZOS] Analisis de propuestas de refuerzos.")
    print(f'{'='*80}')
    # --- LEEMOS EL EXCEL DE LOS REFUERZOS ----
    ruta_refuerzos, nombre_excel_refuerzos = ruta_refuerzos_usuario(ruta_diagnostico)
    df_refuerzos = lectura_excel_refuerzos(ruta_refuerzos, net)
    
    # --- CREACION DE RUTAS (SALIDA) ---
    _, rta_cart, rta_econ, rta_top_prev = carpetas_OP2(ruta_diagnostico, nombre_bd, nombre_excel_refuerzos)
    
    # --- CONFIGURACION INICIAL ---
    configuracion_estudio_2 = config_estudio_2("opcion_2", ruta_diagnostico.parent)
    
    # --- ACTUALIZACION DE DISTANCIAS DE LINEAS RED BASE ---
    df_mline = distancias_lineas(net, df_coord, df_mline)
    reporte_red (net, rta_top_prev, 2)
    logger.info('Se genero el reporte de la topologia de la red con parametros de lineas actualizados.')
    
    # --- COSTOS REFERENCIALES PARA EL ANALISIS ECONOMICO ---
    df_costos_ind, df_costos_reactores = costos(rta_econ)
    
    # --- REFUERZOS PROPUESTOS POR EL USUARIO ---
    ruta_pips_rb = Path(ruta_diagnostico)/"2. Contingencias"/"1. Reportes_PIp"
    refuerzos_usuario(net, df_refuerzos, df_cargabilidades_rbase, ranking_contingencias_rb, rta_cart, parametros_red,
                configuracion_estudio_2["elementos_monitoreo"], ruta_pips_rb, configuracion_estudio_2["exponente_n"],
                df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, df_duraci, parametros_red,
                df_costos_ind, df_costos_reactores, configuracion_estudio_2["nucleos"])

def obtencion_flujos(ejecutar_flujos, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio,
                    df_fechas, ruta_carpeta_base, nombre_bd, ruta_bd):
    if ejecutar_flujos:
        rta_base, rta_cn, rta_esc, rta_infred, ruta_reporte_red = carpetas_OP3_sep(ruta_carpeta_base, nombre_bd)
        configuracion_estudio_3 = config_estudio("opcion_3", ruta_carpeta_base)
        nombre_estudio = f'{nombre_bd}({datetime.now().strftime(f'%H-%M')})'
        configuracion_red_base = Configuracion_Simulacion(nombre_estudio)
        _, df_flujos = caso_base_completo (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio,
                    df_fechas, configuracion_estudio_3['nucleos'], rta_cn, ruta_reporte_red, configuracion_red_base,
                    True, configuracion_estudio_3['reportes_cn_flujos'])
    else:
        ruta_diagnostico = pedir_ruta(ruta_bd)
        rta_base, rta_esc, rta_infred = carpetas_OP3_cep(ruta_diagnostico.parent, nombre_bd)
        configuracion_estudio_3 = config_estudio("opcion_3", ruta_diagnostico.parent)
        cambiar_ubicacion_logger_txt(ruta_diagnostico.parent, 'Reporte ejecucion 3.txt')
        if not Path(ruta_carpeta_base) == Path(ruta_diagnostico).parent:
            eliminar_carpeta(ruta_carpeta_base)
        _, df_flujos = lectura_flujos(ruta_diagnostico, datos_estudio, net)
    return df_flujos, (rta_base, rta_esc, rta_infred)

def seleccion_years(df_fechas, opcion):
    # identificamos años disponibles
    df_fechas['Years'] = df_fechas['Fecha'].dt.year
    lista_years = list(set(df_fechas['Years'].to_list()))
    if opcion == '1':
        logger.info(f'-> Los años deben pertenecer al rango [{df_fechas['Years'].min()}-{df_fechas['Years'].max()}].')
        anios = input_log('Ingrese el año o años seleccionados separados por una coma:').strip()
        lista_anios = [x.strip() for x in anios.split(',')]
        lista_limpia = []
        for an in lista_anios:
            try:
                x = int(an)
                lista_limpia.append(x)
            except:
                logger.warning(f'El elemento {an} no es un numero (entero), por lo que no se lo tomara en cuenta.')
                continue
        lista_final = list( set(lista_limpia) & set(lista_years))
        if lista_final:
            lista_final.sort()
            logger.info(f'La lista de años para analizar quedaria como:\n{lista_final}')
            print(f'{'='*80}')
            return lista_final
        else:
            logger.warning(f'Los años ingresados no estan dentro el rango [{df_fechas['Years'].min()}-{df_fechas['Years'].max()}]')
            logger.warning('Ingrese los años de estudio nuevamente.')
    elif opcion == '2':
        logger.info('Se hara el analisis de escenarios para todos los años del periodo de estudio.')
        print(f'{'='*80}')
        return lista_years
    else:
        logger.info('Se hara el analisis de escenarios para los años de corte.')
        min = df_fechas['Years'].min()
        max = df_fechas['Years'].max()
        lista_years = linspace(min, max, 3)
        lista_years = [int(x) for x in lista_years]
        print(f'{'='*80}')
        return lista_years

def areas_op_2():
    logger.info('Ingrese los datos en el siguiente formato:')
    logger.info('"Nombre" : "Elemento 1, Elemento 2, ... , Elemento n"')
    logger.info('* Una vez terminado el ingreso de datos pulse ENTER (Campo vacio).')
    patron = r"^\s*['\"]\s*[\w\s-]+\s*['\"]\s*:\s*['\"]\s*[\w\s,()-. ]+\s*['\"]\s*$"
    areas_raw = []
    while True:
        entrada = input_log("Ingrese los datos: ")
        if re.match(patron, entrada):
            areas_raw.append(entrada)
        if entrada.strip() == "":
            break
        if re.match(patron, entrada):
            areas_raw.append(entrada)
        else:
            logger.warning('Formato no valido. Asegurese de usar "Nombre" : "Elem1, Elem2"')
    llaves, valores_listas = [], []
    for linea in areas_raw:
        k_raw, v_raw = linea.split(':')
        # El strip(" '\"") quita espacios, comillas simples y dobles de los extremos
        llaves.append(k_raw.strip(" '\""))
        # Limpiar valores (quitar comillas extremos, split por coma y strip individual)
        items = v_raw.strip(" '\"").split(',')
        valores_listas.append([i.strip().upper() for i in items])
    interconexiones = dict(zip(llaves, valores_listas))
    return interconexiones

def validacion_areas(interconexiones: dict, net):
    nombres_elementos = set(net.line['name'].tolist() + net.trafo['name'].tolist())
    dict_filtrado = {}
    dict_descartados = {}
    for clave, lista in interconexiones.items():
        validos = [elem for elem in lista if elem in nombres_elementos]
        descartados = [elem for elem in lista if elem not in nombres_elementos]
        dict_filtrado[clave] = validos
        if descartados:
            dict_descartados[clave] = descartados
    logger.info('Se verificaron los elementos de las interconexiones.')
    if dict_descartados:
        for clave, descartados in dict_descartados.items():
            logger.warning(
                f"Interconexion '{clave}': Se descartaron {len(descartados)} elemento(s) "
                f"por no pertenecer a la red: {descartados}")
    else:
        logger.info('Todos los elementos de las interconexiones existen dentro de la red.')
    return dict_filtrado

def areas(net, opcion):
    print(f'{'='*80}')
    if opcion == '1':
        interconexiones = {
                    'Centro - Oriente' : ['CAR500BRE500', 'CAR230YAP230', 'CAR230230ARB230', 'MAT230BRE230'], # C-O
                    'Centro - Sur' : ['CAT115OCU115', 'SAN230SUC230', 'SEH230SUC230', 'MIZ230SUC230', 'MIZ230SUC(2)'], # C-S
                    'Oriente - Norte' : ['GUA230PRA230', 'GUA230PRA(2)'], # O-N
                    'Centro - Norte' : ['SAN230PCA230', 'SAN230PCA(2)', 'SAN230UMA230', 'SAN230PLD230', 'VIN230MAZ230', 'VIN230PAT230', 'PGA230CBA230'], # C-N
        }
        logger.info(f'Las interconexiones predeterminadas son:')
        for llave, valor in interconexiones.items():
            logger.info(f'{llave}:{valor}')
        print(f'{'='*80}')
        return interconexiones
    else: 
        interconexiones = areas_op_2()
        interconexiones = validacion_areas(interconexiones, net)
        logger.info(f'Las interconexiones declaradas son:')
        for llave, valor in interconexiones.items():
            logger.info(f'{llave}:{valor}')
        print(f'{'='*80}')
        return interconexiones

def opcion_DC_3(df_flujos, rta_base, rta_esc, rta_infred, df_fechas, nombre_bd, net, df_mline, df_mtrafo,
                df_demanda, df_desp_TH, df_desp_ren, Slacks, estudio_predetermindado):
    # --- CONFIGURACION INICIAL ---
    if not estudio_predetermindado:
        opcion_yyyy = menu_seleccion_yyyy()
        lista_yyyy = seleccion_years(df_fechas, opcion_yyyy)
        opcion_areas = menu_seleccion_areas()
        interconexiones  = areas(net, opcion_areas)
    else:
        lista_yyyy = seleccion_years(df_fechas, opcion='2')
        interconexiones  = areas(net, opcion='1')
    
    # --- INFORMACION DE LA RED ---
    reporte_red (net, rta_infred, 1)
    
    # --- ANALISIS DE ESCENARIOS CRITICOS P1 ---
    rutas_anio, lista_escenarios, df_escenarios_p1 = analisis_escenarios(df_desp_TH, df_desp_ren, df_demanda, rta_esc,
                                                                    lista_yyyy, df_fechas)
    graficador_op3_p1 (net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks,
                        lista_escenarios, rutas_anio)
    
    # --- ANALISIS DE FLUJOS (INTERCONEXIONES) ---
    lista_completa, df_escenarios_p2 = analisis_flujos(df_flujos, interconexiones, rta_esc, rutas_anio, lista_yyyy)
    graficador_op3_p2 (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks,
                        lista_completa, rutas_anio)
    
    # --- RESULTADOS ---
    resultados_escenarios_criticos (df_escenarios_p1, df_escenarios_p2, rta_base, nombre_bd)

def pedir_escenarios(datos_estudio):
    print(f'{'='*80}')
    print(f'CONFIGURACION INICIAL.')
    print(f'{'='*80}')
    logger.info("\nConfiguracion de escenarios (Ej: Etapa_1, Serie_1, Bloque_1 ; Etapa_2, ....)")
    logger.info("-> Dejar en blanco para cargar todos los escenarios(Alcance Completo).")
    entrada_esc = input_log("Ingrese los escenarios separados por ';': ").strip()
    # PARAMETROS DE REFRENCIA
    lista_etapas = arange(1, datos_estudio['numero_etapas']+1, 1, dtype=int)
    lista_series = arange(1, datos_estudio['numero_series']+1, 1, dtype=int)
    lista_bloques = arange(1, datos_estudio['numero_bloques']+1, 1, dtype=int)
    # VALIDACION DE ESCENARIOS
    escenarios = []
    if not entrada_esc:
        return escenarios
    bloques = entrada_esc.split(';')
    for b in bloques:
        try:
            etapa, serie, bloque = map(int, b.strip().split(','))
            if etapa in lista_etapas and serie in lista_series and bloque in lista_bloques:
                escenarios.append((etapa, serie, bloque))
            else:
                logger.warning(f"Error en el escenario '{b}', no esta incluido en el horizonte de estudios, se omitira del estudio.")
        except:
            logger.warning(f"Error en el escenario '{b}', se omitira del estudio.")
            continue
    logger.info(f'Se validaron los escenarios {escenarios} Correctamente')
    return escenarios

def opcion_DC_5(nombre_bd, ruta_carpeta_base, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,df_desp_ren, Slacks,
            datos_estudio, df_fechas, df_duraci):
    print(f'{'='*80}')  
    print("[FLUJOS] Ejecutar flujos de potencia en DC solo para escenarios y/o contingencias seleccionadas.")
    print(f'{'='*80}')
    
    # --- CONFIGURACION INICIAL ---
    ruta_carpeta_nueva, cambiar_reporte = carpeta_existente(ruta_carpeta_base)
    if cambiar_reporte:
        cambiar_ubicacion_logger_txt(ruta_carpeta_nueva, 'Reporte ejecucion 5.txt')
        if not Path(ruta_carpeta_base) == Path(ruta_carpeta_nueva):
            eliminar_carpeta(ruta_carpeta_base)
    escenarios = pedir_escenarios(datos_estudio)
    contingencias, llave_contingencias = pedir_contingencias(net)
    configuracion_estudio = config_estudio("opcion_5", ruta_carpeta_nueva)
    nombre_estudio = f'{nombre_bd}({datetime.now().strftime(f'%H-%M')})'
    configuracion_red_base = Configuracion_Simulacion(nombre_estudio)
    
    # --- CREACION DE RUTAS (SALIDA) ---
    _, rta_flw, rta_dgm, rta_ctg_pip, rta_ctg_fp, rta_ctg_dgm, _, rta_reportes = carpetas_OP5(ruta_carpeta_nueva, nombre_bd,
                                                                                            llave_contingencias)
    
    # --- SIMULACION ---
    if not escenarios:
        _, _ = caso_base_completo (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio,
                    df_fechas, configuracion_estudio['nucleos'], rta_flw, rta_reportes, configuracion_red_base,
                    configuracion_estudio['reporte_topologia'], configuracion_estudio['reportes_cn_flujos'])
        logger.info('Al haberse configurado todo el alcance de la base de datos, no se realizaran los diagramas de cargabilidad.')
    else:
        _, _ = caso_base_escenarios (net, configuracion_red_base, df_mtrafo, df_mline, df_desp_TH, df_desp_ren, df_fechas,
                        Slacks, df_demanda, rta_flw, configuracion_estudio['reportes_cn_flujos'], rta_reportes, escenarios)
        graficador_op5_rb(net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, escenarios, rta_dgm)
    
    if llave_contingencias:
        trafos_limpios = trafos_gen(net)
        configuracion_contingencias = Configuracion_Simulacion_Contingencias(nombre_estudio,
                                                            configuracion_estudio['exponente_n'])
        contingencias_op5(escenarios, contingencias, configuracion_contingencias, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                                    df_desp_ren, Slacks, datos_estudio, df_fechas, rta_ctg_fp, rta_ctg_pip, df_duraci,
                                    configuracion_estudio['nucleos'], configuracion_estudio['reportes_cont_flujos'], trafos_limpios)
        graficador_op5_ctg(net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks, escenarios,
                        contingencias, rta_ctg_dgm)

def obtencion_flujos_6(ejecutar_flujos, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio,
                    df_fechas, ruta_carpeta_base, nombre_bd, ruta_bd):
    if ejecutar_flujos:
        rta_cn, rta_ctg_pip,_, rta_ctg_fp = carpetas_OP6_sep(ruta_carpeta_base, nombre_bd)
        configuracion_estudio_6 = config_estudio("opcion_6", ruta_carpeta_base)
        nombre_estudio = f'{nombre_bd}({datetime.now().strftime(f'%H-%M')})'
        configuracion_red_base = Configuracion_Simulacion(nombre_estudio)
        df_cargabilidades, df_flujos = caso_base_completo (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks,
                    datos_estudio, df_fechas, configuracion_estudio_6['nucleos'], rta_cn, None, configuracion_red_base,
                    configuracion_estudio_6['reporte_topologia'], configuracion_estudio_6['reportes_cn_flujos'])
        rutas = (rta_ctg_pip, rta_ctg_fp)
    else:
        ruta_diagnostico = pedir_ruta(ruta_bd)
        ruta_carpeta_principal = ruta_diagnostico
        rta_ctg_pip = ruta_diagnostico / '2. Contingencias/1. Reportes_PIp'
        rta_ctg_fp= ruta_diagnostico / '2. Contingencias/2. Flujos_cargabilidades(n-1)'
        configuracion_estudio_6 = config_estudio("opcion_6", ruta_carpeta_principal.parent)
        cambiar_ubicacion_logger_txt((ruta_carpeta_principal.parent), 'Reporte ejecucion 6.txt')
        if not Path(ruta_carpeta_base) == Path(ruta_diagnostico).parent:
            eliminar_carpeta(ruta_carpeta_base)
        df_cargabilidades, df_flujos = lectura_flujos(ruta_diagnostico, datos_estudio, net, True)
        rutas = (rta_ctg_pip, rta_ctg_fp)
    return (df_cargabilidades, df_flujos), rutas, configuracion_estudio_6

def archivos_contingencias(net, nombre_estudio, configuracion_estudio, contingencias, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                    df_desp_ren, Slacks, datos_estudio, df_fechas, rta_ctg_pip, rta_ctg_fp, df_duraci):
    nombres_archivos_ctg = [(f'LF_ctg_{x}.csv', f'Loading_ctg_{x}.csv', f'PIp_{x}.csv', x) for x in contingencias]
    existen = []
    no_existen = []
    rta_ctg_pip = Path(rta_ctg_pip)
    rta_ctg_fp = Path(rta_ctg_fp)
    for archivo_lf, archivo_crg, archivo_pip, ctg_id in nombres_archivos_ctg:
        ruta_lf_diagnostico = rta_ctg_fp / archivo_lf
        ruta_crgb_diagnostico = rta_ctg_fp / archivo_crg
        if ruta_lf_diagnostico.is_file() and ruta_crgb_diagnostico.is_file():
            existen.append(ctg_id)
        else:
            no_existen.append(ctg_id)
    logger.info(f'Se valido la existencia de los archivos de contingencias: {existen}')
    if no_existen:
        print('-'*80)
        while True:
            opcion = input_log(f'No se encontraron archivos de flujo para {no_existen}. ¿Quieres simular? [s/n]: ').strip().lower()
            print('-'*80)
            if opcion == 's':
                logger.info(f"Se simularán {len(no_existen)} contingencias faltantes.")
                escenarios = []
                trafos_limpios = trafos_gen(net)
                configuracion_contingencias = Configuracion_Simulacion_Contingencias(
                    nombre_estudio, configuracion_estudio['exponente_n'])
                contingencias_op5(
                    escenarios, no_existen, configuracion_contingencias, net, df_mline, df_mtrafo, 
                    df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, 
                    rta_ctg_fp, rta_ctg_pip, df_duraci, configuracion_estudio['nucleos'], 
                    configuracion_estudio['reportes_cont_flujos'], trafos_limpios)
                print('='*80)
                return rta_ctg_fp, rta_ctg_pip
            elif opcion == 'n':
                logger.warning('Al no haber flujos ni cargabilidades se recomienda no graficarlas.')
                logger.info('Pero sí se pueden graficar los PIp disponibles.')
                print('='*80)
                return rta_ctg_fp, rta_ctg_pip
            else:
                logger.error('Opción no válida. Elija entre [s/n].')
    print('='*80)
    return rta_ctg_fp, rta_ctg_pip

def opcion_DC_6(nombre_bd, configuracion_estudio, rta_ctg_pip, rta_ctg_fp, df_cargabilidades, df_flujos, net, 
                df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, df_duraci):
    nombre_estudio = f'{nombre_bd}({datetime.now().strftime(f'%H-%M')})'
    lista_elementos = net.line['name'].tolist() + net.trafo['name'].tolist()
    while True:
        modo = menu_graficador()
        if modo =='1':
            print('='*80)
            graficador_condicion_n(df_cargabilidades, df_flujos, lista_elementos)
            print('='*80)
        elif modo =='2':
            contingencias = pedir_contingencias_graficador(net)
            ruta_flujos, ruta_pips = archivos_contingencias(net, nombre_estudio, configuracion_estudio, contingencias, df_mline, df_mtrafo,
                                                df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, rta_ctg_pip, rta_ctg_fp,
                                                df_duraci)
            while True:
                opcion = graficador_contingencias_o_pip()
                if opcion == '1':
                    graficador_contingencias(ruta_flujos, lista_elementos)
                elif opcion == '2':
                    graficador_pip(ruta_pips, lista_elementos)
                else:
                    break
            
        else:
            return

def opcion_DC_7(ruta_estudio, ruta_escenarios, nombre_bd, ruta_carpeta_base, net, df_demanda, df_desp_TH, df_desp_ren):
    # CONFIGURACION INICIAL
    configuracion_estudio_6 = config_estudio("opcion_6", ruta_estudio)
    cambiar_ubicacion_logger_txt((ruta_estudio), 'Reporte ejecucion 6.txt')
    if not Path(ruta_estudio) == Path(ruta_carpeta_base):
        eliminar_carpeta(ruta_carpeta_base)
    # LECTURA DE ESCENARIOS
    df_p1, df_p2 = lectura_escenarios(ruta_escenarios)
    if df_p1.empty or df_p2.empty:
        e = 'Existe uno o ambos dataframe de escenario(s) vacio(s), por lo que no se mostraran los escenarios criticos'
        logger.warning(e)
    # FUNCION
    rta_par, rta_ac = carpetas_OP7(ruta_estudio, nombre_bd)
    menu_vinculacion_pf(df_p1, df_p2, ruta_escenarios, rta_par, rta_ac, net, df_demanda, df_desp_TH, df_desp_ren)