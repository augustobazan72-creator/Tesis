from Motor_DC import Gestor_Topologia, Configurador_Despacho_Demanda, simular_flujo_DC
from Configuracion_inicial import input_log
from pandapower.plotting.plotly import pf_res_plotly
import matplotlib.ticker as ticker
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons
from pathlib import Path
import gc
import pandas as pd
import numpy as np
import logging
import copy

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

def _forzar_backend_interactivo() -> bool:
    """True si hay backend con ventana; False si solo hay Agg y no se pudo cambiar."""
    be = (matplotlib.get_backend() or '').lower()
    if 'agg' not in be:
        return True
    for nombre in ('TkAgg', 'QtAgg', 'Qt5Agg'):
        try:
            plt.switch_backend(nombre)
            logger.info('Backend gráficos: %s', matplotlib.get_backend())
            return True
        except Exception:
            continue
    return False

def simular_contingencia(escenario, contingencia, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, ruta_contingencias,
                        auto_open = True):
    etapa, serie, bloque = escenario
    net_copy = copy.deepcopy(net)
    gestor_topologia = Gestor_Topologia(net_copy, df_mline, df_mtrafo)
    config_dd = Configurador_Despacho_Demanda(net_copy, df_demanda, df_desp_TH, df_desp_ren, Slacks)
    gestor_topologia.aplicar_topologia_etapa(etapa)
    config_dd.configurar_escenario(etapa, serie, bloque)
    id_cont, tipo_cont, nombre_cont = contingencia
    if tipo_cont == 'line':
        prev_status = net_copy.line.at[id_cont, 'in_service']
        net_copy.line.at[id_cont, 'in_service'] = False
    elif tipo_cont == 'trafo':
        prev_status = net_copy.trafo.at[id_cont, 'in_service']
        net_copy.trafo.at[id_cont, 'in_service'] = False
    try:
        simular_flujo_DC(net_copy, check_conn=False)
        nombre = f'Diagrama_cont_{nombre_cont}_E[{etapa}],S[{serie}],B[{bloque}].html'
        nombre_archivo = str(ruta_contingencias/nombre)
        graficar_red(net_copy, nombre_archivo, auto_open)
    except Exception as e:
        logger.error(f"Error en flujo DC para contingencia '{nombre_cont}' "
                f"(E:{etapa}, S:{serie}, B:{bloque}): {e}")
    finally:
        if tipo_cont == 'line':
            net_copy.line.at[id_cont, 'in_service'] = prev_status
        elif tipo_cont == 'trafo':
            net_copy.trafo.at[id_cont, 'in_service'] = prev_status

def simular_caso_base(escenario, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks, ruta_analisis_energetico,
                    auto_open = True, nombre = None):
    net_copy = copy.deepcopy(net)
    etapa, serie, bloque = escenario
    gestor_topologia = Gestor_Topologia(net_copy, df_mline, df_mtrafo)
    config_dd = Configurador_Despacho_Demanda(net_copy, df_demanda, df_desp_TH, df_desp_ren, Slacks)
    gestor_topologia.aplicar_topologia_etapa(etapa)
    config_dd.configurar_escenario(etapa, serie, bloque)
    simular_flujo_DC(net_copy)
    if nombre == None:
        nombre = f'Diagrama_cond_n_(E[{etapa}]_S[{serie}]_B[{bloque}]).html'
    nombre_archivo = str(ruta_analisis_energetico/nombre)
    graficar_red(net_copy, nombre_archivo, auto_open)

def graficar_red(net, nombre_archivo, auto_open):
    net.res_line.loc[net.line['in_service'] == False, 'loading_percent'] = np.nan
    net.res_trafo.loc[net.trafo['in_service'] == False, 'loading_percent'] = np.nan
    pp_logger = logging.getLogger("pandapower")
    old_level = pp_logger.level
    pp_logger.setLevel(logging.ERROR)
    try:
        pf_res_plotly(net, on_map=True, map_style='light', filename=nombre_archivo, auto_open=auto_open)
    finally:
        pp_logger.setLevel(old_level)

def graficador_op1 (net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks,
                        top_contingencias, ruta_diagramas_cont):
    print(f"{'='*80}")
    print('DIAGRAMAS DE CARGABILIDAD PARA ELEMENTOS CRITICOS (CONTINGENCIAS).')
    print(f"{'='*80}")
    auto_open = False
    contingencias = list(top_contingencias['contingencias'])
    logger.info(f'Se generaran {len(contingencias)} diagramas de cargabilidad en total. ')
    logger.info('Por contingencia se usara el escenario de mayor PIp.')
    lista_contingencias = []
    for cont in contingencias:
        idx_line = net.line[net.line['name'] == cont].index
        if not idx_line.empty:
            lista_contingencias.append((idx_line[0], 'line', cont))
            continue
        idx_trafo = net.trafo[net.trafo['name'] == cont].index
        if not idx_trafo.empty:
            lista_contingencias.append((idx_trafo[0], 'trafo', cont))
            continue
    lista_esc_pip = list(top_contingencias['escenario_pip'])
    lista_argumentos = list(zip(lista_contingencias, lista_esc_pip))
    for contingencia, esce_pip in lista_argumentos:
        simular_contingencia(esce_pip, contingencia, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
                    Slacks, ruta_diagramas_cont, auto_open)
        gc.collect()
    logger.info('Diagramas de cargabilidad generados correctamente (Archivos.html).')
    print(f"{'='*80}")

def graficador_op3_p1 (net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks,
                        lista_escenarios, rutas_anio):
    print('DIAGRAMAS DE CARGABILIDAD PARA ESCENARIOS CRITICOS (P1).')
    print(f"{'-'*80}")
    auto_open = False
    logger.info('Generando diagramas de cargabilidad de la red para los escenarios criticos "parte 1" del caso base.')
    for info in lista_escenarios:
        etapas, series, bloques, tiempo, escenarios_criticos = info
        ruta = Path(rutas_anio[str(tiempo)][1])
        escenario = [etapas, series, bloques]
        nombre = f'Diagrama(cn)_{escenarios_criticos}.html'
        simular_caso_base(escenario, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                        df_desp_ren, Slacks, ruta, auto_open, nombre)
    print(f"{'='*80}")

def graficador_op3_p2 (net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren, Slacks,
                        lista_completa, rutas_anio):
    print('DIAGRAMAS DE CARGABILIDAD PARA ESCENARIOS CRITICOS (P2).')
    print(f"{'-'*80}")
    auto_open = False
    logger.info('Generando diagramas de cargabilidad de la red para los escenarios criticos "parte 2" del caso base.')
    for identificador, escenario in lista_completa:
        nombre = f'Diagrama(cn)_{identificador[0]}_{identificador[1]}_{identificador[2]}.html'
        ruta = Path(rutas_anio[str(identificador[2])][1])
        simular_caso_base(escenario, net, df_mline, df_mtrafo, df_demanda, df_desp_TH,
                            df_desp_ren, Slacks, ruta, auto_open, nombre)
    logger.info('Diagramas del caso base terminados correctamente.\n')
    print(f"{'='*80}\n")

def graficador_op5_rb(net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks, escenarios,
                        ruta_diagramas_cb):
    print(f'{'-'*80}')
    print('DIAGRAMAS DE CARGABILIDAD PARA ESCENARIOS ESPECIFICOS (CONDICION N).')
    print(f'{'-'*80}\n')
    auto_open = False
    logger.info(f'Se generaran los diagramas para {len(escenarios)}.')
    for escenario in escenarios:
        simular_caso_base(escenario, net, df_mline, df_mtrafo,  df_demanda, df_desp_TH, df_desp_ren,
                        Slacks, ruta_diagramas_cb, auto_open)
        gc.collect()
    logger.info('Diagramas del caso base terminados correctamente.\n')
    print(f'{'='*80}\n')

def graficador_op5_ctg(net, df_mline, df_mtrafo, df_demanda,df_desp_TH, df_desp_ren, Slacks, escenarios,
                        contingencias, ruta_diagramas_cont):
    print(f'{'-'*80}')
    print('DIAGRAMAS DE CARGABILIDAD PARA ESCENARIOS Y CONTINGENCIAS ESPECIFICOS (CONDICION N-1).')
    print(f'{'-'*80}\n')
    auto_open = False
    logger.info(f'Se generaran los diagramas para {len(escenarios) * len(contingencias)}.')
    for contingencia in contingencias:
        for escenario in escenarios:
            simular_contingencia(escenario, contingencia, net, df_mline, df_mtrafo, df_demanda, df_desp_TH, df_desp_ren,
                        Slacks, ruta_diagramas_cont, auto_open)
            gc.collect()
    logger.info('Diagramas del caso base terminados correctamente.\n')
    print(f'{'='*80}\n')


def _listar_etiquetas(ruta: Path, archivo:str) -> list[str]:
    ruta = Path(ruta)
    if not ruta.is_dir():
        return []
    etiquetas = []
    if archivo == 'LF':
        for p in sorted(ruta.glob('Loading_ctg_*.csv')):
            etiquetas.append(p.stem[len('Loading_ctg_'):])
    else:
        for p in sorted(ruta.glob('PIp_*.csv')):
            etiquetas.append(p.stem[len('PIp_'):])
    return etiquetas

def _resolver_rutas(ruta: Path, etiqueta: str, archivo:str) -> tuple[Path, Path] | None:
    ruta = Path(ruta)
    if archivo =='LF':
        c_exact = ruta / f'Loading_ctg_{etiqueta}.csv'
        f_exact = ruta / f'LF_ctg_{etiqueta}.csv'
        if c_exact.is_file() and f_exact.is_file():
            return c_exact, f_exact
        candidatos = sorted(ruta.glob(f'Loading_ctg_{etiqueta}*.csv'))
        for c_path in candidatos:
            suf = c_path.stem[len('Loading_ctg_'):]
            f_path = ruta / f'LF_ctg_{suf}.csv'
            if f_path.is_file():
                return c_path, f_path
        return None
    else:
        f_exact = ruta / f'PIp_{etiqueta}.csv'
        if f_exact.is_file():
            return f_exact
        candidatos = sorted(ruta.glob(f'PIp_{etiqueta}*.csv'))
        for c_path in candidatos:
            suf = c_path.stem[len('PIp_'):]
            f_path = ruta / f'PIp_{suf}.csv'
            if f_path.is_file():
                return f_path
        return None

def _serie_sort_key(x):
    try:
        return (0, int(x))
    except (TypeError, ValueError):
        return (1, str(x))

def _graficar_cargab_flujo_interactivo(df_c: pd.DataFrame, df_f: pd.DataFrame, titulo: str) -> None:
    """Dos filas: cargabilidad y flujo; panel lateral con series y promedio."""
    req_c = ['Etapa', 'Bloque', 'Serie', 'Componente', 'loading_percent']
    req_f = ['Etapa', 'Bloque', 'Serie', 'Componente', 'Flujo_mw']
    faltan_c = [c for c in req_c if c not in df_c.columns]
    faltan_f = [c for c in req_f if c not in df_f.columns]
    if faltan_c or faltan_f:
        logger.error(f'Faltan columnas: cargabilidad {faltan_c}, flujo {faltan_f}')
        return
    df_c_din = df_c.pivot_table(
        index=['Etapa', 'Bloque'], columns='Serie', values='loading_percent', aggfunc='first')
    df_f_din = df_f.pivot_table(
        index=['Etapa', 'Bloque'], columns='Serie', values='Flujo_mw', aggfunc='first')
    df_c_din = df_c_din.sort_index()
    df_f_din = df_f_din.reindex(index=df_c_din.index).reindex(columns=df_c_din.columns)
    df_c_din['EB'] = ('E:' + df_c_din.index.get_level_values('Etapa').astype(str) + '-' +
                        'B:' + df_c_din.index.get_level_values('Bloque').astype(str))
    etiquetas_x = df_c_din['EB'].tolist()
    df_c_din.drop(columns=['EB'], inplace = True)
    df_c_din['prom'] = df_c_din[[c for c in df_c_din.columns if c != 'prom']].mean(axis=1)
    df_f_din['prom'] = df_f_din[[c for c in df_f_din.columns if c != 'prom']].mean(axis=1)
    ser_cols = [c for c in df_c_din.columns if c != 'prom']
    ser_cols = sorted(ser_cols, key=_serie_sort_key)
    ordered = ser_cols + (['prom'] if 'prom' in df_c_din.columns else [])
    df_c_din = df_c_din[ordered]
    df_f_din = df_f_din[ordered]
    plot_labels = [f'Serie {c}' for c in ser_cols]
    if 'prom' in ordered:
        plot_labels.append('Promedio')
    plt.close('all')
    if not _forzar_backend_interactivo():
        ruta = Path.cwd() / (
            ''.join(c if c.isalnum() or c in '-_' else '_' for c in titulo)[:80] + '_estatica.png')
        fig_e, (ax1e, ax2e) = plt.subplots(2, 1, sharex=True, figsize=(13, 9))
        x = np.arange(1, len(df_c_din) + 1, 1, dtype='int')
        col_p = 'prom' if 'prom' in df_c_din.columns else ordered[0]
        lbl = 'Promedio' if col_p == 'prom' else plot_labels[0]
        ax1e.plot(etiquetas_x, df_c_din[col_p].values, color='C0', linewidth=1.4, label=lbl)
        ax2e.plot(etiquetas_x, df_f_din[col_p].values, color='C0', linewidth=1.4)
        ax1e.set_ylabel('Cargabilidad [%]')
        ax2e.set_ylabel('Flujo [MW]')
        ax2e.set_xlabel('Índice ordenado (Etapa, Bloque)')
        ax1e.grid(True, alpha=0.35)
        ax2e.grid(True, alpha=0.35)
        fig_e.suptitle(titulo, fontsize=12, fontweight='bold')
        fig_e.savefig(ruta, dpi=150, bbox_inches='tight')
        plt.close(fig_e)
        logger.warning(
            'Solo backend Agg sin GUI: se guardó vista (promedio/serie 1) en %s. '
            'Instale PySide/PyQt o use entorno con pantalla para controles interactivos.',
            ruta.resolve(),)
        return
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8))
    plt.subplots_adjust(left=0.18, right=0.98, top=0.9, bottom=0.1, hspace= .35)
    x = np.arange(1, len(df_c_din) + 1, 1, dtype='int')
    cmap = plt.cm.tab20(np.linspace(0, 1, max(len(ordered), 1)))
    lineas_c: list = []
    lineas_f: list = []
    nlab = len(plot_labels)
    actives = [False] * nlab
    if 'Promedio' in plot_labels:
        actives[plot_labels.index('Promedio')] = True
    elif nlab:
        actives[0] = True
    for i, col in enumerate(ordered):
        color = cmap[i % len(cmap)]
        lc, = ax1.plot(
            etiquetas_x, df_c_din[col].values, color=color, linewidth=1.4,
            label=plot_labels[i], visible=actives[i])
        lf, = ax2.plot(
            etiquetas_x, df_f_din[col].values, color=color, linewidth=1.4,
            label=plot_labels[i], visible=actives[i])
        lineas_c.append(lc)
        lineas_f.append(lf)
    ax1.set_ylabel('Cargabilidad [%]')
    ax2.set_ylabel('Flujo [MW]')
    ax2.set_xlabel('Índice ordenado (Etapa, Bloque)')
    ax1.grid(True, alpha=0.35)
    ax2.grid(True, alpha=0.35)
    fig.suptitle(titulo, fontsize=12, fontweight='bold')
    rax = fig.add_axes([0.01, 0.3, 0.1, 0.5])
    check = CheckButtons(rax, plot_labels, actives)
    def _on_check(_label):
        estado = check.get_status()
        for j, vis in enumerate(estado):
            lineas_c[j].set_visible(vis)
            lineas_f[j].set_visible(vis)
        fig.canvas.draw_idle()
    check.on_clicked(_on_check)
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins=12, integer=True))
    ax2.xaxis.set_major_locator(ticker.MaxNLocator(nbins=12, integer=True))
    @ticker.FuncFormatter
    def formatear_eje_x(x, pos):
        idx = int(round(x))
        if 0 <= idx < len(etiquetas_x):
            return etiquetas_x[idx]
        return ''
    ax1.xaxis.set_major_formatter(formatear_eje_x)
    ax2.xaxis.set_major_formatter(formatear_eje_x)
    plt.show()

def _graficar_pip_interactivo(df_pip: pd.DataFrame, titulo: str) -> None:
    # LIMITE PIP
    LIMITE =1.05
    # GRAFICA
    req_c = ['Etapa', 'Bloque', 'Serie', 'Nombre_Contingencia', 'PIp_Total']
    faltan_c = [c for c in req_c if c not in df_pip.columns]
    if faltan_c:
        logger.error(f'Faltan columnas: {faltan_c}')
        logger.error('Revisar archivos Pip.')
        return
    df_pip_din = df_pip.pivot_table(
        index=['Etapa', 'Bloque'], columns='Serie', values='PIp_Total', aggfunc='first')
    df_pip_din = df_pip_din.sort_index()
    df_pip_din = df_pip_din.reindex(index=df_pip_din.index).reindex(columns=df_pip_din.columns)
    df_pip_din['EB'] = ('E:' + df_pip_din.index.get_level_values('Etapa').astype(str) + '-' +
                        'B:' + df_pip_din.index.get_level_values('Bloque').astype(str))
    etiquetas_x = df_pip_din['EB'].tolist()
    df_pip_din.drop(columns=['EB'], inplace = True)
    df_pip_din['prom'] = df_pip_din[[c for c in df_pip_din.columns if c != 'prom']].mean(axis=1)
    ser_cols = [c for c in df_pip_din.columns if c != 'prom']
    ser_cols = sorted(ser_cols, key=_serie_sort_key)
    ordered = ser_cols + (['prom'] if 'prom' in df_pip_din.columns else [])
    df_pip_din = df_pip_din[ordered]
    plot_labels = [f'Serie {c}' for c in ser_cols]
    if 'prom' in ordered:
        plot_labels.append('Promedio')
    plot_labels.append(f'Límite ({LIMITE})')
    plt.close('all')
    if not _forzar_backend_interactivo():
        ruta = Path.cwd() / (
            ''.join(c if c.isalnum() or c in '-_' else '_' for c in titulo)[:80] + '_estatica.png')
        fig_e, ax1e = plt.subplots(figsize=(13, 9))
        col_p = 'prom' if 'prom' in df_pip_din.columns else ordered[0]
        lbl = 'Promedio' if col_p == 'prom' else plot_labels[0]
        ax1e.plot(etiquetas_x, df_pip_din[col_p].values, color='C0', linewidth=1.4, label=lbl)
        ax1e.axhline(y=LIMITE, color='r', linestyle='--', linewidth=1.5, label='Límite')
        ax1e.set_ylabel('Indice PIp')
        ax1e.set_xlabel('Índice ordenado (Etapa, Bloque)')
        ax1e.grid(True, alpha=0.35)
        fig_e.suptitle(titulo, fontsize=12, fontweight='bold')
        fig_e.savefig(ruta, dpi=150, bbox_inches='tight')
        plt.close(fig_e)
        logger.warning(
            'Solo backend Agg sin GUI: se guardó vista (promedio/serie 1) en %s. '
            'Instale PySide/PyQt o use entorno con pantalla para controles interactivos.',
            ruta.resolve(),)
        return
    fig, ax1 = plt.subplots(figsize=(13, 9))
    plt.subplots_adjust(left=0.18, right=0.98, top=0.9, bottom=0.15)
    cmap = plt.cm.tab20(np.linspace(0, 1, max(len(ordered), 1)))
    lineas_c: list = []
    nlab = len(plot_labels)
    actives = [False] * nlab
    if 'Promedio' in plot_labels:
        actives[plot_labels.index('Promedio')] = True
    elif nlab:
        actives[0] = True
    actives[plot_labels.index(f'Límite ({LIMITE})')] = True
    for i, col in enumerate(ordered):
        color = cmap[i % len(cmap)]
        lc, = ax1.plot(
            etiquetas_x, df_pip_din[col].values, color=color, linewidth=1.4,
            label=plot_labels[i], visible=actives[i])
        lineas_c.append(lc)
    lc_limite = ax1.axhline(
        y=LIMITE, color='red', linestyle='--', linewidth=1.8, 
        label=f'Límite ({LIMITE})', visible=actives[-1])
    lineas_c.append(lc_limite)
    ax1.set_ylabel('Indice PIp')
    ax1.set_xlabel('Índice ordenado (Etapa, Bloque)')
    plt.xticks(rotation=45, ha='right', fontsize=8)
    ax1.grid(True, alpha=0.35)
    fig.suptitle(titulo, fontsize=12, fontweight='bold')
    rax = fig.add_axes([0.01, 0.3, 0.1, 0.5])
    check = CheckButtons(rax, plot_labels, actives)
    def _on_check(_label):
        estado = check.get_status()
        for j, vis in enumerate(estado):
            lineas_c[j].set_visible(vis)
        fig.canvas.draw_idle()
    check.on_clicked(_on_check)
    ax1.xaxis.set_major_locator(ticker.MaxNLocator(nbins=12, integer=True))
    @ticker.FuncFormatter
    def formatear_eje_x(x, pos):
        idx = int(round(x))
        if 0 <= idx < len(etiquetas_x):
            return etiquetas_x[idx]
        return ''
    ax1.xaxis.set_major_formatter(formatear_eje_x)
    plt.show()

def graficador_condicion_n(df_cargabilidades, df_flujos, lista_elementos):
    while True:
        elemento = input_log("Nombre del componente a graficar ('q' volver al menu): ").strip().upper()
        if elemento == 'Q':
            return
        if elemento not in lista_elementos:
            logger.warning(f'El elemento [{elemento}] no esta en la red o esta mal escrito, intente nuevamente.')
            print(f'{'-'*80}')
        else:
            df_c = df_cargabilidades[df_cargabilidades['Componente'] == elemento].copy()
            df_f = df_flujos[df_flujos['Componente'] == elemento].copy()
            if df_c.empty or df_f.empty:
                logger.error(f'Sin datos para el componente {elemento}. Verifique el nombre.')
            titulo = f'Elemento [{elemento}] - Condicion "n".'
            _graficar_cargab_flujo_interactivo(df_c, df_f, titulo)

def graficador_contingencias(ruta_res_cont, lista_elementos):
    while True:
        etiquetas = _listar_etiquetas(ruta_res_cont, archivo = 'LF')
        if not etiquetas:
            logger.error(
                f'No se encontraron archivos de cargabilidad ni flujos en {ruta_res_cont}. '
                'Ejecute contingencias con generación de reportes o use otra carpeta.')
            return
        print('='*80)
        print('Contingencias disponibles:')
        print('='*80)
        for i, t in enumerate(etiquetas[:40], 1):
            print(f'  {i:3}. {t}')
        if len(etiquetas) > 40:
            print(f'  ... y {len(etiquetas) - 40} más.')
            print('-'*80)
        raw = input_log("Contingencia (Ingrese el nombre del archivo, o 'q' volver al menu): ").strip()
        if raw.lower() == 'q':
            return
        etiqueta = raw.upper()
        par = _resolver_rutas(ruta_res_cont, etiqueta, archivo='LF')
        if etiqueta not in lista_elementos:
            logger.warning(f'El elemento [{etiqueta}] no se encuentra en la base de datos, revise el nombre.')
            print('-'*80)
            continue
        if par is None:
            logger.error(f'No se hallo el par de archivos de dicha contingencia: {etiqueta}')
            logger.error(f'Por favor revise el nombre de la contingencia que se va a analizar.')
            break
        df_c = pd.read_csv(par[0])
        df_f = pd.read_csv(par[1])
        print('-'*80)
        comp_raw = input_log("Nombre del componente a graficar ('q' para otra contingencia o 's' para volver al menu): ").strip().upper()
        print('-'*80)
        if comp_raw == 'Q':
            break
        if comp_raw == 'S':
            return
        if comp_raw not in lista_elementos:
            logger.warning(f'El elemento [{comp_raw}] no se encuentra en la base de datos, revise el nombre.')
            print('-'*80)
            continue
        df_c_e = df_c[df_c['Componente'] == comp_raw].copy()
        df_f_e = df_f[df_f['Componente'] == comp_raw].copy()
        if df_c_e.empty or df_f_e.empty:
            logger.error(f'Sin datos para {comp_raw} en esta contingencia.')
            logger.error(f'Revise el nombre del elemento que va a graficar.')
            continue
        titulo = f'Contingencia [{etiqueta}] — Elemento graficado [{comp_raw}]'
        df_c_e['Componente'] = df_c_e['Componente']
        df_f_e['Componente'] = df_c_e['Componente']
        df_f_e['Flujo_mw'] = df_f_e['flujo_mw']
        _graficar_cargab_flujo_interactivo(df_c_e, df_f_e, titulo)
        print('='*80)

def graficador_pip(ruta_pip, lista_elementos):
    while True:
        etiquetas = _listar_etiquetas(ruta_pip, archivo='PIp')
        if not etiquetas:
            logger.error(
                f'No se encontraron archivos de indice [PIp] en {ruta_pip}. '
                'Ejecute contingencias con generación de reportes o use otra carpeta.')
            return
        print('='*80)
        print('Archivos de Indices PIp disponibles:')
        print('='*80)
        for i, t in enumerate(etiquetas[:40], 1):
            print(f'  {i:3}. {t}')
        if len(etiquetas) > 40:
            print(f'  ... y {len(etiquetas) - 40} más.')
        raw = input_log("Contingencia (Nombre del archivo ('q'para salir) ): ").strip()
        print('-'*80)
        if raw.lower() == 'q':
            return
        etiqueta = raw.upper()
        par = _resolver_rutas(ruta_pip, etiqueta, archivo= 'PIp')
        if etiqueta not in lista_elementos:
            logger.warning(f'El elemento [{etiqueta}] no se encuentra en la base de datos, revise el nombre.')
            print('-'*80)
            continue
        if par is None:
            logger.error(f'No se hallo el archivos PIp de dicha contingencia: {etiqueta}')
            logger.error(f'Por favor revise el nombre de la contingencia que se va a analizar.')
            break
        df_pip = pd.read_csv(par)
        titulo = f'Indice Performance index of Active Power (PIp) para [{etiqueta}] '
        _graficar_pip_interactivo(df_pip, titulo)
        print('='*80)