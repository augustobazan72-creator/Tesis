import logging
import sys
from pathlib import Path
from Rutas import ruta_bd_SDDP, carpeta_principal, pedir_ruta, ruta_escenarios_criticos
from Configuracion_inicial import configurar_logger_txt, input_log, cambiar_ubicacion_logger_txt, eliminar_carpeta
from Lector_bd_SDDP import lector_SDDP, alcance, validar_datos_SDDP, coordenadas
from Procesamiento_bd import crear_fechas, modificacion_circuitos, procesar_despachos
from Red_pandapower import (crear_red, agregar_barras, agregar_cargas, agregar_trafos_lineas, agregar_gen_staticos,
                            agregar_gen_sincronos)
from Menus import menu_principal, estudio_previo_OP2, estudio_previo_OP3, opcion3_predeterminada, estudio_previo_OP6
from Funciones_menu import (opcion_DC_1 , opcion_DC_2, obtencion_flujos, opcion_DC_3, opcion_DC_5, opcion_DC_6,
                            obtencion_flujos_6, opcion_DC_7)
from Refuerzos import lectura_estudio_previo

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    
    # --- ACTIVACION DEL CAPTURADOR DE LOGS Y PRINTS ---
    ruta_carpeta_base = carpeta_principal()
    configurar_logger_txt(ruta_carpeta_base, 'Reporte ejecucion 1.txt')
    
    # --- INGRESO DE LA RUTA DE LA BASE DE DATOS ---
    ruta_bd, nombre_bd = ruta_bd_SDDP()
    
    # --- LECTURA Y VALIDACION DE LA BASE DE DATOS SDDP ---
    dfs_leidos = lector_SDDP(ruta_bd)
    datos_estudio = alcance(dfs_leidos, nombre_bd)
    (df_dbus, df_dcirc, df_cgndbo, df_ctermibo, df_chidrobo, df_duraci, df_mcirc, df_gerter,
        df_gerhid, df_gergnd, df_demxbael, df_datosSDDP) = validar_datos_SDDP(dfs_leidos, datos_estudio)
    df_coord = coordenadas (ruta_bd)
    
    # --- CONSTRUCCION DF_FECHAS ---
    df_fechas = crear_fechas(datos_estudio)
    
    # --- CONSTRUCTOR RED PANDAPOWER ---
    net, parametros_red = crear_red()
    df_barras = agregar_barras(net, df_dbus, df_coord)
    agregar_trafos_lineas(net, df_dcirc, df_barras, parametros_red)
    agregar_gen_sincronos(net, df_chidrobo, df_ctermibo, df_dbus, parametros_red)
    agregar_gen_staticos(net, df_cgndbo, parametros_red)
    agregar_cargas(net, df_demxbael)
    
    # --- PREPARACION POST FLUJOS (MODIFICACIONES CIRC Y CONVERSION A MW)
    (df_mtrafo, df_mline) = modificacion_circuitos(df_mcirc, df_fechas, df_barras, datos_estudio, net,
                                                parametros_red)
    (df_desp_TH, df_desp_ren, Slacks, df_demanda) = procesar_despachos(df_gerter, df_gerhid,
                                                            df_gergnd, df_demxbael, df_duraci, net)
    
    # --- BUCLE MENU ---
    while True:
        menu_principal()
        opcion = input_log("Seleccione una opcion (1-8): ").strip()
        print(f'{'='*80}')
        if opcion == '1':
            _ = opcion_DC_1(df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, df_mline, df_fechas,
                datos_estudio,  Slacks, df_duraci, ruta_carpeta_base, nombre_bd, True, parametros_red, net)
        
        elif opcion == '2':
            # --- ADQUISICION DE DATOS DE ESTUDIOS PREVIOS ---
            realizar_diagnostico = estudio_previo_OP2()
            if realizar_diagnostico:
                ruta_diagnostico = opcion_DC_1(df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, df_mline, df_fechas,
                datos_estudio,  Slacks, df_duraci, ruta_carpeta_base, nombre_bd, parametros_red, net)
            else:
                ruta_diagnostico = pedir_ruta(ruta_bd)
                cambiar_ubicacion_logger_txt(ruta_diagnostico, 'Reporte ejecucion 2.txt')
                if not Path(ruta_carpeta_base) == Path(ruta_diagnostico).parent:
                    eliminar_carpeta(ruta_carpeta_base)
            df_cargabilidades_rbase, ranking_contingencias_rb = lectura_estudio_previo(ruta_diagnostico)
            
            # --- ANALISIS DE REFUERZOS ---
            opcion_DC_2(df_cargabilidades_rbase, ranking_contingencias_rb, ruta_diagnostico, nombre_bd, net, df_coord,
                    df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, df_duraci,
                    parametros_red, df_mline)
        
        elif opcion == '3':
            print(f'\n{'='*80}')
            print("[ESCENARIOS] Identificacion de escenarios criticos.")
            print(f'{'='*80}')  
            # --- ADQUISICION DE DATOS DE ESTUDIOS PREVIOS ---
            ejecutar_flujos = estudio_previo_OP3()
            df_flujos, rutas = obtencion_flujos(ejecutar_flujos, net, df_mline, df_mtrafo, df_demanda,
                                df_desp_TH, df_desp_ren, Slacks, datos_estudio, df_fechas, ruta_carpeta_base, nombre_bd, ruta_bd)
            estudio_predetermindado = opcion3_predeterminada()
            rta_base, rta_esc, rta_infred = rutas
            
            # --- ANALISIS DE ESCENARIOS ---
            opcion_DC_3(df_flujos, rta_base, rta_esc, rta_infred, df_fechas, nombre_bd, net, df_mline, df_mtrafo,
                df_demanda, df_desp_TH, df_desp_ren, Slacks, estudio_predetermindado)
        
        elif opcion == '4':
            _ = opcion_DC_1(df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, df_mline, df_fechas,
                datos_estudio,  Slacks, df_duraci, ruta_carpeta_base, nombre_bd, False, parametros_red, net)
        
        elif opcion == '5':
            opcion_DC_5(nombre_bd, ruta_carpeta_base, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,df_desp_ren, Slacks,
            datos_estudio, df_fechas, df_duraci)
        
        elif opcion == '6':
            print(f'\n{'='*80}')
            print("[GRAFICADOR] Generar graficas de flujos y cargabilidades de componentes.")
            print(f'{'='*80}')  
            ejecutar_flujos = estudio_previo_OP6()
            dfs, rutas, configuracion_estudio = obtencion_flujos_6 (ejecutar_flujos, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks,
                                            datos_estudio, df_fechas, ruta_carpeta_base, nombre_bd, ruta_bd)
            rta_ctg_pip, rta_ctg_fp = rutas
            df_cargabilidades, df_flujos = dfs
            opcion_DC_6(nombre_bd, configuracion_estudio, rta_ctg_pip, rta_ctg_fp, df_cargabilidades, df_flujos, net,
                df_mline, df_mtrafo, df_demanda, df_desp_TH,df_desp_ren, Slacks, datos_estudio, df_fechas, df_duraci)

        elif opcion == '7':
            print(f'\n{'='*80}')
            print("[DIGSILENT] Importar un escenario critico a DigSilent Power Factory (Flujos en DC).")
            print(f'{'='*80}')
            ruta_estudio, ruta_escenarios = ruta_escenarios_criticos()
            if not ruta_estudio:
                logger.warning('Se saldra al menu.')
                break
            else:
                opcion_DC_7(ruta_estudio, ruta_escenarios, nombre_bd, ruta_carpeta_base, net, df_demanda, df_desp_TH, df_desp_ren)
        
        elif opcion == '8':
            print("\nCerrando el programa.")
            sys.exit()
        
        else:
            logger.info(f'Opcion {opcion} no valida, ingrese un valor entre [1-8].')
            print(f'{'-'*80}')