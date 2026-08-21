import logging
from Configuracion_inicial import input_log

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

def menu_principal():
    print(f'{'='*80}')
    print("                MENU PRINCIPAL (ANALSIS ELECTRICO DC).")
    print(f'{'='*80}')
    print("1. [DIAGNOSTICO] Diagnostico de la red de transmision (Completo).")
    print("2. [REFUERZOS] Analisis de propuestas de refuerzos.")
    print("3. [ESCENARIOS] Identificacion de escenarios criticos.")
    print(f'{"-"*80}')
    print('Herramientas adicionales')
    print(f'{"-"*80}')
    print("4. [DIAGNOSTICO] Diagnostico de la red de transmision (Reducido).")
    print("5. [FLUJOS] Ejecutar flujos de potencia en DC solo para escenarios y/o contingencias seleccionadas.")
    print("6. [GRAFICADOR] Generar graficas de flujos y cargabilidades de componentes.")
    print("7. [DIGSILENT] Importar un escenario critico a DigSilent Power Factory (Flujos en DC).")
    print("8. Salir")
    print(f'{'-'*80}')

def estudio_previo_OP2()-> bool:
    while True:
        print(f'{'='*80}')
        opcion = input_log('Se realizo algun estudio previo (Diagnostico de la red de transmision)? (S/N):').strip().lower()
        if opcion == 's':
            logger.info('No se relizara el diagnostico de la red de transmision.')
            logger.info('Se tomara como base comparativa los resultados obtenidos previamente.')
            print(f'{'='*80}')
            return False
        elif opcion == 'n':
            logger.info('Se relizara el diagnostico de la red de transmision.')
            print(f'{'='*80}')
            return True
        else:
            logger.warning('Ingrese una opcion valida [S-N].')

def prints_refuerzos_usuario(ruta_diagnostico):
    print(f'{'='*80}')
    print('CONFIGURACION DEL ARCHIVO DE REFUERZOS .')
    print(f'{'='*80}')
    logger.info('El formato del archivo ".xlsx" de refuerzos debe tener los siguientes encabezados:')
    logger.info(('Nombre_refuerzo | id_bus_from | id_bus_to | Alternativa | Cartera | Tipo | sn[MVAR/km] | P[MW] | r[ohm/km] |') + 
    ('\n    x[ohm/km] | length_km | Elementos a monitorear | En servicio | Latitud | Longitud'))
    logger.info(('En caso de desconocer "id_bus_from" o "id_bus_to" el programa automaticamente saco un reporte de la topologia')+
    (f'\n    de la red guardada en:\n    {ruta_diagnostico}/3. Reportes'))
    logger.info(('En caso de desconexion de un componente se usa "0" en la columna de "En servicio", se deja vacia en caso de que')+
    ('\n    sea una conexion.'))
    print(f'{'-'*80}') 
    print('Nombre_refuerzo.\n')
    logger.info(('El nombre del refuerzo (linea o trafo) debe cumplir con barra_inicio y barra destino en conjunto con la')+
    ('\n    tension nominal (Ej. SAN230SUC230)'))
    logger.info('En caso de que el elemento ya exista debe llevar un (2) en vez de Un destino (Ej. SAN230SUC230 -> SAN230SUC(2)))')
    logger.info('En caso de que la propuesta sea un actualizacion de parametros el nombre debe ser el del componente original.')
    logger.info(('En caso de que sea sacar un componente de servicio, el nombre debe ser el del componente que se va a sacar de')+
    ('\n    servicio las demas columnas se deben dejar vacias (la unica que se llena es en servicio).'))
    logger.info(('El nombre en caso de ser una barra debe ser AAA-000, donde "AAA" (identificador de la barra) y')+
    ('\n    "000" (tension de la barra).'))
    print(f'{'-'*80}') 
    print('Configuracion para "Cartera" y "Alternativas".\n')
    logger.info('Cada "Cartera" esta constiuida por "Alternativas" donde el programa elige la alternativa de menor costo.') 
    logger.info(('Para evaluar varios refuerzos como una sola alternativa, la columna de alternativa debe ser la misma para todos') +
    ('\n    los refuerzos que constituyan dicha alternativa.'))
    logger.info(('En caso de que hayan varias alternatvas en una cartera la columna de alternativa debe ser diferente para') +
    ('\n    cada alternativa.'))
    print(f'{'-'*80}') 
    print('Barras.\n')
    logger.info('Para el ingreso de barras en "Tipo" debe ir el indicador "BARRA".')
    logger.info('No se debe llenar ningun otro dato (id_bus_from, id_bus_to, parametros electricos o en servicio).')
    logger.info('Si se conocen las coordenadas (Latidud - Longitud) se pueden ingresar (Parametro adicional).')
    print(f'{'-'*80}') 
    print('Lineas de transmision.\n')
    logger.info('Los parametros de: resistencia , reactancia  y suceptancia especificas deben estar en [ohm/km] - [MVAR/km].')
    logger.info('La conversion de los parametros electricos especificos a la base del sistema, se hace internamente.')
    logger.info('Para lineas doble terna se debe ingresar los parametros electricos de 1 sola terna.')
    logger.info(('En caso de que una linea se conecte a una barra que aun no esta creada dejar el campo de id_bus_from o')+
    ('\n    id_bus_to respectivamente vacio.'))
    logger.info(('En caso de que se quiera que el programa haga una aproximacion de la distancia de una linea las barras de')+
    ('\n    origen y destino deben contar con las coordenadas correspondientes.'))
    logger.info(('En caso de que la linea no cuente con distancia y las barras de origen y destino no cuenten con las')+
    ('\n    coordenadas correspondientes el programa asignara una distancia de 1 [Km].'))
    logger.info('El tipo de linea puede ser:')
    logger.info(' LST: Linea Simple Terna.')
    logger.info(' LDT: Linea Doble Terna.')    
    logger.info(' LDTI: Linea Doble Terna Incompleta.')    
    logger.info(' CDT: Completar Doble terna.')
    print(f'{'-'*80}') 
    print('Transformadores.\n')
    logger.info('Los parametros de los trafos deben ser en [ohm] referidos al lado de AT.')
    logger.info('Para transformadores dejar los campos (length_km, sn[MVAR]) length_km vacio o con 0.')
    logger.info('Para transformadores en "Tipo" debe ir el indicador "TRAFO".')
    logger.info(('En caso de que un trafo se conecte a una barra que aun no esta creada dejar el campo de id_bus_from o')+
    ('\n    id_bus_to respectivamente vacio.'))
    print(f'{'-'*80}')
    print('Elementos a monitorear.\n')
    logger.info(('Por "Cartera" ingrese solo 1  elemento de monitoreo (este elemento sera tomado como referencia para' )+
    ('\n    el analisis tecnico y la determinacon de la fecha de ingreso de la alternativa).'))
    print(f'{'='*80}\n')

def menu_distancias():
    print(f'{'='*80}')
    print("Configuracion de las longitudes de las lineas.")
    print(f'{'='*80}\n')
    print("1. Calcular las distancias de las lineas segun Haversine. (Se requiere coordenadas de las barras)")
    print("2. Cargar archivo '.xlsx' con las distancias de las lineas. (Nombre - longitud [Km])")
    print(f'{'-'*80}')

def menu_costos_usuario():
    print(f'{'-'*80}')
    print('Cargar costos (Desde un archivo excel).')
    print(f'{'-'*80}')
    logger.info(rf'La ruta del archivo excel debe incluir el archivo excel Ej: "C\..\...\archivo.xlsx")')
    logger.info('El formato del archivo.xlsx debe tener el siguiete formato:')
    logger.info('Debe contar con 2 hojas, "Hoja 1" de costos de lineas y trafos, y "Hoja 2" de costos de rectores.')
    logger.info('La "Hoja 1" debe contar con los siguiente puntos y el siguiente formato:')
    logger.info('-> El costo de bahia debe incluir ambas bahias, la de incio como la de fin.\n')
    print(' Elemento |  Un_1  |  ...  |  Un_n  | AT/BT_1 |  ...  | AT/BT_n |')
    print('   LST    |  Costo |  ...  |  Costo |    -    |  ...  |    -    |')
    print('   LDT    |  Costo |  ...  |  Costo |    -    |  ...  |    -    |')
    print('   LDTI   |  Costo |  ...  |  Costo |    -    |  ...  |    -    |')
    print('   CDT    |  Costo |  ...  |  Costo |    -    |  ...  |    -    |')
    print('  Bahia   |  Costo |  ...  |  Costo |  Costo  |  ...  |  Costo  |')
    print('  Trafo   |    -   |  ...  |    -   |  Costo  |  ...  |  Costo  |')
    logger.info('\nLa "Hoja 2" debe contar con los siguiente puntos y el siguiente formato:')
    logger.info('-> En caso de que no se tenga el costo poner "-".')
    print(' Reactor_mvar |  Un_1  |  ...  |  Un_n  |')
    print('     Q_1      |  Costo |  ...  |  Costo |')
    print('      .       |  Costo |  ...  |  Costo |')
    print('      .       |  Costo |  ...  |  Costo |')
    print('      .       |  Costo |  ...  |  Costo |')
    print('     Q_n      |  Costo |  ...  |  Costo |')
    print(f'{'-'*80}')

def estudio_previo_OP3()-> bool:
    while True:
        print(f'{'='*80}')
        opcion = input_log('Se realizo algun estudio previo (Diagnostico de la red de transmision)? (S/N):').strip().lower()
        if opcion == 's':
            logger.info('Para el analisis de escenarios se usaran los resultados de los flujos obtenidos previamente.')
            print(f'{'='*80}')
            return False
        elif opcion == 'n':
            logger.info('Se ejecutaran flujos de potencia para todos los escenarios de la base de datos(Condicion n).')
            print(f'{'='*80}')
            return True
        else:
            logger.warning('Ingrese una opcion valida [S-N].')

def menu_seleccion_yyyy():
    print(f'{'='*80}')
    print('SELECCION DE AÑOS PARA EL ANALISIS DE ESCENARIOS.')
    print(f'{'='*80}')
    print(f'1. Realizar el estudio para 1 o varios años (Elegidos por el usuario).')
    print(f'2. Realizar el estudio para todos los años del horizonte de estudios.')
    print(f'3. Realizar el estudio solo para los años de corte (Inicio - Mitad - Final)')
    print(f'{'-'*80}')
    while True:
        opcion = input_log('Elija una opcion en el rango [1-3]: ').strip()
        if opcion in ['1', '2', '3']:
            print(f'{'='*80}')
            return opcion
        else:
            print('Opcion no valida. Elija una opcion en el rango [1-3].')

def menu_seleccion_areas():
    print(f'{'='*80}')
    print('CONFIGURACION DE AREAS Y ELEMENTOS (TRANSFERENCIA ENTRE AREAS).')
    print(f'{'='*80}')
    print("1. Usar interconexion entre areas predeterminadas.")
    print("2. Ingresar las interconexiones.")
    print(f'{'-'*80}')
    while True:
        opcion = input_log('Elija una opcion en el rango [1-2]: ').strip()
        if opcion in ['1', '2']:
            print(f'{'='*80}')
            return opcion
        else:
            print('Opcion no valida. Elija una opcion en el rango [1-2].')

def opcion3_predeterminada()-> bool:
    print(f'{'='*80}')
    print('CONFIGURACION DE AÑOS Y AREAS.')
    print(f'{'='*80}')
    print("1. Usar años e interconexion predeterminada.")
    print("2. Ingresar los años e interconexiones.")
    print(f'{'-'*80}')
    while True:
        opcion = input_log('Elija una opcion en el rango [1-3]: ').strip()
        if opcion == '1':
            print(f'{'='*80}')
            return True
        elif opcion == '2':
            print(f'{'='*80}')
            return False
        else:
            print('Opcion no valida. Elija una opcion en el rango [1-2].')

def estudio_previo_OP6()-> bool:
    while True:
        print(f'{'='*80}')
        opcion = input_log('Se realizo algun estudio previo [Diagnostico - Evaluacion de escearios ]? (S/N):').strip().lower()
        if opcion == 's':
            logger.info('Se usara la informacion de los flujos obtenidos en el condicion "n", para l graficadora de elementos.')
            print(f'{'='*80}')
            return False
        elif opcion == 'n':
            logger.info('Se ejecutaran flujos de potencia para todos los escenarios de la base de datos(Condicion n).')
            print(f'{'='*80}')
            return True
        else:
            logger.warning('Ingrese una opcion valida [S-N].')

def menu_graficador():
    print(f'{'='*80}')
    print('GRAFICADOR DE COMPONENTES (FLUJOS, CARGABILIDAD Y PIP).')
    print(f'{'='*80}')
    print('[1] Caso base (CONDICION "N")')
    print('[2] Contingencias (CONDICION "N-1" - PIP)')
    print("[q] Salir")
    while True:
        print(f'{'-'*80}')
        modo = input_log('Seleccione (1/2/q): ').strip().lower()
        if modo in ['1', '2', 'q']:
            print(f'{'-'*80}')
            return modo
        else:
            logger.warning('Opcion no valida, seleccione una opcion entre [1/2/3/q].')

def pedir_contingencias(net):
    print(f'{'-'*80}')
    logger.info("Configuración de Contingencias (Ej: San230suc230)")
    logger.info("Ingresar 'q' solo para ejecutar los escenarios del caso base (No contingencias).")
    logger.info("Dejar en blanco para cargar todas las contingencias.")
    entrada_cont = input_log("Ingrese las contingencias separadas por ',': ").strip()
    contingencias = []
    if entrada_cont.lower()=='q':
        llave_contingencias = False
    elif entrada_cont:
        contingencias = [c.strip().upper() for c in entrada_cont.split(',') if c.strip()]
        elementos_red = set(net.line['name'].tolist() + net.trafo['name'].tolist())
        contingencias = set(contingencias)
        llave_contingencias = True
        cotingencias_validas = contingencias.issubset(elementos_red) 
        if cotingencias_validas:
            logger.info(f'Se validaron las contingencias: {cotingencias_validas}')
        else:
            contingencias = contingencias.intersection(elementos_red)
            no_validados = contingencias.difference(elementos_red)
            logger.info(f'Se validaron las contingencias: {cotingencias_validas}')
            logger.warning(f'Los siguientes elementos no existen, por lo que no seran tomados en cuenta:\n{no_validados}')
    else:
        llave_contingencias = True
        logger.info(f'Se cargaran todas las contingencias.')
    print(f'{'='*80}')
    return contingencias, llave_contingencias

def pedir_contingencias_graficador(net):
    while True:
        print(f'{'='*80}')
        print("MENU DE CONFIGURACION DE CONTINGENCIAS (Ej: San230suc230)")
        print(f'{'='*80}')
        print("-> Dejar en blanco para cargar todas las contingencias.")
        print(f'{'-'*80}')
        elementos_red = set(net.line['name'].tolist() + net.trafo['name'].tolist())
        entrada_cont = input_log("Ingrese las contingencias separadas por ',': ").strip()
        if entrada_cont.strip() == '':
            return elementos_red
        contingencias = [c.strip().upper() for c in entrada_cont.split(',') if c.strip()]
        contingencias = set(contingencias)
        cotingencias_validas = contingencias.issubset(elementos_red)
        if cotingencias_validas:
            logger.info(f'Se validaron las contingencias: {contingencias}')
            return contingencias
        else:
            contingencias = contingencias.intersection(elementos_red)
            no_validados = contingencias.difference(elementos_red)
            if len(contingencias) == 0:
                logger.warning('No se valido ninguna contingencia, por favor ingrese una contingencia valida.')
                continue
            else:
                logger.info(f'Se validaron las contingencias: {contingencias}')
                logger.warning(f'Los siguientes elementos no existen, por lo que no seran tomados en cuenta:\n{no_validados}')
                return contingencias

def graficador_contingencias_o_pip():
    print(f'{'='*80}')
    print("MENU DE GRAFICADOR DE CONTINGENCIAS(Ej: San230suc230)")
    print(f'{'='*80}')
    print('[1] Flujos y cargabilidaes en elementos.')
    print('[2] Performance Index of active power (PIp) ')
    print('[q] Salir')
    while True:
        print(f'{'-'*80}')
        opcion = input_log("Seleccione (1/2/q):  ").strip().lower()
        if opcion in ['1', '2', 'q']:
            print(f'{'='*80}')
            return opcion
        else:
            logger.warning('Opcion no valida, seleccione una opcion entre [1/2/q].')

def menu_digsilent():
    print(f'{'='*80}')
    print("MENU DE IMPORTACION DE ESCENARIOS")
    print(f'{'='*80}')
    print('[1] Cargar escenarios (criticos o escenario especifico).')
    print('[2] Generar el reporte de elementos de la red.')
    print('[q] Salir.')
    while True:
        print(f'{'-'*80}')
        opcion = input_log("Seleccione (1/2/q): ").strip().lower()
        if opcion in ['1', '2', '3', 'q']:
            print('='*80)
            return opcion
        else:
            logger.warning('Opcion no valida, seleccione una opcion entre [1/2/3/q].')

def guia__archivo_pareo():
    print('='*80)
    print('CONFIGURACION DEL ARCHIVO DE PAREO')
    print('='*80)
    print('\nEl archivo debe subirse en formato excel.')
    print('El archivo excel debe contar con 3 hojas: "Gen. Syn." - "Gen. Sta." - "Cargas"')
    print('Los nombres de las hojas deben ser los mencionados anteriormente y estar en el mismo orden.')
    print('Cada hoja debe contar con una primera columna "PF" y una segunda "SDDP" donde se relacione')
    print('    el nombre en PowerFactory con el nombre SDDP.')
    print('En el caso de la hoja de generadores sincronos "Gen. Syn." se debe contar con una tercera')
    print('    columna llamada "P_min_MW" en donde se detalle la potencia minima de cada generador.')
    print('Mediante la aopcion 3, puede obtener la informacion de nombres de generadores sincronos,')
    print('    generadores estaticos y cargas.')
    print('-'*80)

def menu_escenarios():
    print(f'{'-'*80}\n')
    print('Cargar escenarios.')
    print('[1] Escenarios de despacho (Gen. Sincrona - Gen. Variable) y demanda.')
    print('[2] Escenarios (criticos) de transferencia entre areas.')
    print('[3] Escenarios especificos.')
    print('[4] Para cambiar de caso de estudio.')
    print('[q] Salir.')
    while True:
        print(f'{'-'*80}')
        opcion = input_log("Seleccione (1/2/3/4/q):  ").strip().lower()
        if opcion in ['1', '2', '3', '4', 'q']:
            print('='*80)
            return opcion
        else:
            logger.warning('Opcion no valida, seleccione una opcion entre [1/2/3/q].')