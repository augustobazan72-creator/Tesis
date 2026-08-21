import logging
import os
import sys
import openpyxl
import pandas as pd
from pathlib import Path
from Configuracion_inicial import input_log
from Menus import menu_digsilent, menu_escenarios, guia__archivo_pareo
from Lector_excels import lector_pareo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def vinculacion_pf():
    print('='*80)
    print('Vinculacion con PowerFactory')
    print('='*80)
    while True:
        ruta_usuario = Path(input_log(f'Ingrese la ruta de DIgSIlent(Ej: ({r'C:\...\DIgSILENT\PowerFactory 2024\Python\3.12)'}):\n').strip())
        if ruta_usuario.exists() and ruta_usuario.is_dir():
            try: 
                ruta_dig = ruta_usuario.parent
                os.environ["PATH"] = rf'{str(ruta_dig)}'+';'+os.environ["PATH"]
                sys.path.append(rf'{str(ruta_usuario)}')
                import powerfactory as pf
                app = pf.GetApplication()
                app.Show()
                logger.info('Se vinculo correctamente DigSilent con el programa (Python).\n')
                print(f'{'-'*80}')
                return(app)
            except:
                logger.warning('Revise que la direccion copiada sea correcta.')
                print(f'{'-'*80}')
        else: 
            logger.warning('La ruta debe ser una la direccion de la carpeta.')
            print(f'{'-'*80}')

def seleccion_caso_estudio(app):
    # Seleccion base de datos
    print('Seleccion del caso de estudio a utilizar para la importacion de escenarios')
    logger.info('Del modo engine copie la direccion de la base de datos a utilizarse.')
    while True:
        ruta_proyecto = input_log('Ingrese la ruta de la carpeta pf:')
        nombre_usuario, dir_proyecto = ruta_proyecto.split('\\', 1)
        dir_proyecto = dir_proyecto.replace('\\', '\\\\')
        try:
            app.ActivateProject(dir_proyecto)
            # app.Hide()
            logger.info(f'El usuario seleccionado es: {nombre_usuario}')
            logger.info(f'La direccion de la base de datos es: {dir_proyecto}')
            logger.info('Se activo la base de datos correctamente.')
            print(f'{'-'*80}')
            return dir_proyecto
        except:
            logger.error('La ruta de la base de datos no existe o es incorrecta.')

def casos_estudio(app, dir_proyecto):
    # FUNCION AUXILIAR
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
    
    # SELECCION DE CASO DE ESTUDIO
    folder_estudios = app.GetProjectFolder('study', 1)
    if folder_estudios is None:
        logger.error("No se pudo encontrar la carpeta de casos de estudio.")
    else:
        casos = casos_de_estudio(folder_estudios)
        if not casos:
            logger.error("No se encontraron casos de estudio.")
        else:
            print(f'{'-'*80}')
            print(f"Casos de estudio disponibles: ({len(casos)}):")
            print(f'{'-'*80}')
            for i, caso in enumerate(casos, start=1):
                print(f"{i:>1}. {caso.loc_name}")
            print(f'{'-'*80}')
            while True:
                seleccion = input_log('Ingrese el numero de caso de estudio (a activarse): ').strip()
                if seleccion.isdigit() and 1 <= int(seleccion) <= len(casos):
                    caso_elegido = casos[int(seleccion) - 1]
                    caso_elegido.Activate()
                    logger.info(f"Caso de estudio (activado): {caso_elegido.loc_name}")
                    print(f'{'='*80}')
                    return [dir_proyecto.split('\\', -1)[-1], caso_elegido.loc_name]
                else:
                    logger.warning(f"Opcion invalida, ingrese un número entre 1 y {len(casos)}.")

def guardar_valores(ws, lista_PF, lista_SDDP):
    # Guardamos lista PF
    for i, elemento in enumerate(lista_SDDP):
        ws[f"A{i+1}"] = elemento
    for i, elemento in enumerate(lista_PF):
        ws[f"B{i+1}"] = elemento
    return ws


def elementos_pf(app, ruta, net):
    print('='*80)
    print('EXPORTACION DE ELEMENTOS A EXCEL')
    print('='*80)
    # RED
    print(f'GRIDS')
    folder_red = app.GetProjectFolder('netdat')
    grids = folder_red.GetContents('*.ElmNet')
    for g in grids:
        if g.loc_name.strip() == 'SIN':
            g.outserv = 0
            logger.info(f'Grid activada: {g.loc_name}')
            break
    print(f'{'-'*80}')
    
    # GENERADORES SINCRONOS
    print(f'GENERACION SINCRONA')
    generacion_sincrona = {}
    generadores_syn_pf = folder_red.GetContents('*.ElmSym', 1)
    for i in generadores_syn_pf:
        generacion_sincrona[i.loc_name] = i
    logger.info('Se importaron los generadores sincronos.')
    print(f'{'-'*80}')
    
    # GENERADORES RENOVABLES
    print(f'GENERACION RENOVABLE')
    generadores_estaticos = {}
    generadores_sta_pf = folder_red.GetContents('*.ElmGenstat', 1)
    for i in generadores_sta_pf:
        generadores_estaticos[i.loc_name] = i
    logger.info('Se importaron los generadores estaticos.')
    print(f'{'-'*80}')
    
    # DEMANDAS
    print('CARGAS')
    cargas_pf = {}
    cargas = folder_red.GetContents('*.ElmLod', 1)
    for i in cargas:
        print(i)
        cargas_pf[i.loc_name] = i
    logger.info('Se importaron las cargas.')
    print(f'{'-'*80}')
    
    # ELEMENTOS - SDDP
    gen_syn_sddp = net.gen['name'].tolist()
    gen_sta_sddp = net.sgen['name'].tolist()
    load_sddp = net.load['name'].tolist()
    
    # PREPARAR LAS LISTAS
    gen_syn_sddp.insert(0, 'SDDP')
    gen_sta_sddp.insert(0, 'SDDP')
    load_sddp.insert(0, 'SDDP')
    
    gen_syn_pf = list(generacion_sincrona.keys())
    gen_syn_pf.insert(0, 'PF')
    gen_sta_pf = list(generadores_estaticos.keys())
    gen_sta_pf.insert(0, 'PF')
    load_pf = list(cargas_pf.keys())
    load_pf.insert(0, 'PF')
    
    # EXCEL 
    wb = openpyxl.Workbook()
    ws1 = wb.create_sheet('Gen. Syn.', 0)
    ws1 = guardar_valores(ws1, gen_syn_pf, gen_syn_sddp)
    ws2 = wb.create_sheet('Gen. Sta.', 1)
    ws2 = guardar_valores(ws2, gen_sta_pf, gen_sta_sddp)
    ws3 = wb.create_sheet('Cargas.', 2)
    ws3 = guardar_valores(ws3, load_pf, load_sddp)
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])

    # ARCHIVO
    ruta = Path(ruta)/'Pareo_nombres_PF_SDDP.xlsx'
    wb.save(ruta)
    logger.info('Se genero el reporte de elementos correctamente.')
    print('='*80)

def escenarios_disponibles(df, llave):
    print(f'{'-'*80}')
    print(f"Casos de estudio disponibles: ({len(df)}):")
    print(f'{'-'*80}')
    if llave == 1:
        lista_escenarios = df['Escenarios criticos'].tolist()
    else:
        df['Año'] = df['Año'].astype(str)
        df['escenarios'] = df['Interconexion'] + "_" + df['Lectura'] + "_" + df['Año']
        lista_escenarios = df['escenarios'].tolist()
    for i, caso in enumerate(lista_escenarios, start=1):
        print(f"{i:>1}. {caso}")
    print(f'{'-'*80}')
    while True:
        seleccion = input_log('Ingrese el numero de escenario a importar: ').strip()
        if seleccion.isdigit() and 1 <= int(seleccion) <= len(lista_escenarios):
            escenario_elegido = int(seleccion) - 1
            escenario = df.loc[escenario_elegido] [['Etapa', 'Serie', 'Bloque']]
            return escenario
        else:
            logger.warning(f"Opcion invalida, ingrese un número entre 1 y {len(lista_escenarios)}.")

def ingresar_escenario():
    while True:
        etapa = input_log('Ingrese la etapa:')
        serie = input_log('Ingrese la serie:')
        bloque = input_log('Ingrese el bloque:')
        escenario = []
        for val in [etapa, serie, bloque]:
            try:
                x = int(val)
                escenario.append(x)
            except:
                e = f'El valor ingresado {x} no es un numero entero.'
                logger.error(e)
        if len(escenario) == 3 :
            return escenario

def base_datos_pf(app):
    folder_red = app.GetProjectFolder('netdat')
    grids = folder_red.GetContents('*.ElmNet')
    for g in grids:
        if g.loc_name.strip() == 'SIN':
            g.outserv = 0
            logger.info(f'Grid activada: {g.loc_name}')
            break
    # GENERADORES SINCRONOS
    generacion_sincrona = {}
    generadores_syn_pf = folder_red.GetContents('*.ElmSym')
    for i in generadores_syn_pf:
        generacion_sincrona[i.loc_name] = i
    # GENERADORES RENOVABLES
    generadores_estaticos = {}
    generadores_sta_pf = folder_red.GetContents('*.ElmGenstat')
    for i in generadores_sta_pf:
        if i.cCategory != 'Reactive Power Compensation':
            generadores_estaticos[i.loc_name] = i
    # DEMANDAS
    cargas_pf = {}
    cargas = folder_red.GetContents('*.ElmLod')
    for i in cargas:
        cargas_pf[i.loc_name] = i
    return generacion_sincrona, generadores_estaticos, cargas_pf


def importar_demanda(escenario, pareo_cargas, app, df_demanda, cargas_pf):
    df_demanda = df_demanda.copy()
    df_cargas = df_demanda.loc[[escenario]]
    cargas_sddp = set(pareo_cargas['SDDP'].tolist())
    demandas_pf = []
    for carga in list(cargas_sddp):
        df = pareo_cargas[pareo_cargas['SDDP'] == carga]
        num_demandas = len(df)
        demanda_sddp = float(df_cargas[carga].item())
        demanda_pf = demanda_sddp/ num_demandas
        x = [carga, demanda_pf]
        demandas_pf.append(x)
    df_demandas_pf = pd.DataFrame(demandas_pf, columns = ['SDDP', 'MW_pf'])
    pareo_cargas = pd.merge(pareo_cargas, df_demandas_pf, on = 'SDDP', how = 'left')
    pareo_cargas.set_index(['PF'], inplace=True)
    for llave, valor in cargas_pf.items():
        p = pareo_cargas.at[llave, 'MW_pf']
        print(p)
        print(valor)
        valor.SetAttribute('plini', float(p))
    return app


def importar_escenarios(pareo_syn, pareo_sta, pareo_cargas, df_p1, df_p2, app, dir_proyecto, df_demanda, df_desp_TH, df_desp_ren):
    gsyn_pf, gsta_pf, cargas_pf = base_datos_pf(app)
    opcion = menu_escenarios()
    if opcion == '1':
        escenario = escenarios_disponibles(df_p1, 1)
        app = importar_demanda(escenario, pareo_cargas, app, df_demanda, cargas_pf)
    elif opcion == '2':
        escenario = escenarios_disponibles(df_p2, 0)
    elif opcion == '3':
        escenario = ingresar_escenario()
    elif opcion == '4':
        casos_estudio(app, dir_proyecto)
    else:
        return


def menu_vinculacion_pf(df_p1, df_p2, ruta_escenarios, rta_par, rta_ac, net, df_demanda, df_desp_TH, df_desp_ren):
    # VINCULAMOS CON PF
    app = vinculacion_pf()
    dir_proyecto = seleccion_caso_estudio(app)
    name_bd, name_ce = casos_estudio(app, dir_proyecto)
    # BUCLE MENU
    while True:
        opcion = menu_digsilent()
        if opcion == '1':
            guia__archivo_pareo()
            pareo_syn, pareo_sta, pareo_cargas = lector_pareo()
            if pareo_syn.empty and pareo_sta.empty and pareo_cargas.empty:
                e = 'Las tablas de pareo estan vacias, Revise el archivo de pareo'
                logger.warning(e)
            else:
                importar_escenarios(pareo_syn, pareo_sta, pareo_cargas, df_p1, df_p2, app, dir_proyecto,
                                    df_demanda, df_desp_TH, df_desp_ren)
        elif opcion =='2':
            elementos_pf(app, rta_par, net)
        else:
            return