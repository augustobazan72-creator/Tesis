#%%
import pandas as pd
from pathlib import Path
from Rutas import ruta_bd_SDDP, carpeta_principal, pedir_ruta, ruta_escenarios_criticos
from Configuracion_inicial import configurar_logger_txt, input_log, cambiar_ubicacion_logger_txt, eliminar_carpeta
from Lector_bd_SDDP import lector_SDDP, alcance, validar_datos_SDDP, coordenadas
from Procesamiento_bd import crear_fechas, modificacion_circuitos, procesar_despachos
from Red_pandapower import (crear_red, agregar_barras, agregar_cargas, agregar_trafos_lineas, agregar_gen_staticos,
                            agregar_gen_sincronos)
from Resultados import diagrama_elementos_criticos
#%%
# --- ACTIVACION DEL CAPTURADOR DE LOGS Y PRINTS ---
ruta_carpeta_base = carpeta_principal()
configurar_logger_txt(ruta_carpeta_base, 'prueba 1.txt')

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
#%%
# LECTURA DF
ruta_condicion_n = rf"G:\Otros ordenadores\Augusto Bazan\Tesis\Codigo\Estudio_electrico_2026-08-28-07-58\Op1_pmp_sddp_05092025_(D.Completo)\1. Condicion_n\Reporte_analisis_condicion_n.csv"
ruta_contingencias = rf"G:\Otros ordenadores\Augusto Bazan\Tesis\Codigo\Estudio_electrico_2026-08-28-07-58\Op1_pmp_sddp_05092025_(D.Completo)\2. Contingencias\Ranking(cont)_pmp_sddp_05092025(07-58).csv"
analisis_componentes = pd.read_csv(Path(ruta_condicion_n))
ranking_contingencias = pd.read_csv(Path(ruta_contingencias))
print(analisis_componentes)
print(ranking_contingencias)

#%%
from pandapower.plotting.plotly.traces import (create_bus_trace, create_line_trace, create_trafo_trace,
                draw_traces)
nombre_estudio = 'Hola'
def diagrama_elementos_criticos(net, analisis_componentes: pd.DataFrame, ranking_contingencias: pd.DataFrame,
                                df_mtrafo: pd.DataFrame, df_mline: pd.DataFrame, nombre_estudio, ruta_base):
    print('='*80)
    print('DIAGRAMA DEL SISTEMA')
    print('='*80)
    if net.bus_geodata.empty:
        print('La red no cuenta con coordenadas por lo que no se generara el diagrama.')
        return
    # FUNCION AUX
    def _flatten(item):
        return item if isinstance(item, list) else [item]

    # MAPA DE COLORES
    color_map = {69.0: "red", 115.0: "blue", 230.0: "green", 500.0: "fuchsia"}
    u_colores = {v: k for k, v in color_map.items()}

    # BUSES
    bus_trace = create_bus_trace(net, buses=net.bus.index, size=6, color="blue")
    print('Todos los buses se generaran con color azul.')

    # LINEAS
    lineas_futuras = df_mline['nombre_componente'].tolist()
    df_lineas = net.line.copy()
    df_lineas_activas = df_lineas[df_lineas['in_service'] == True].copy()
    indices_lineas = df_lineas_activas.index.tolist()
    df_lineas_fuera = df_lineas[df_lineas['in_service'] == False].copy()
    for id, fila in df_lineas_fuera.iterrows():
        if fila['name'] in lineas_futuras:
            indices_lineas.append(id)
    barras_from = net.line.loc[indices_lineas, 'from_bus'].tolist()
    voltage_levels = net.bus.loc[barras_from, "vn_kv"].values
    line_colors = [color_map.get(vn, "black") for vn in voltage_levels]
    line_traces = []
    df_line_color = pd.DataFrame({"idx": indices_lineas, "color": line_colors})
    for color_val, grupo in df_line_color.groupby("color"):
        tension = u_colores.get(color_val, 'Otras tensiones.')
        trace = create_line_trace(net, lines=grupo["idx"].tolist(), width=2, color=color_val,
                trace_name=f"U_nom lineas {tension} [KV]")
        line_traces.extend(_flatten(trace))

    # TRAFOS
    trafos_futuros = df_mtrafo['nombre_componente'].tolist()
    df_trafo = net.trafo.copy()
    df_trafos_activos = df_trafo[df_trafo['in_service'] == True].copy()
    indices_trafos = df_trafos_activos.index.tolist()
    df_trafos_fuera = df_trafo[df_trafo['in_service'] == False].copy()
    for id, fila in df_trafos_fuera.iterrows():
        if fila['name'] in trafos_futuros:
            indices_trafos.append(id)
    voltage_levels = net.trafo.loc[indices_trafos, "vn_hv_kv"].values
    trafos_colors = [color_map.get(vn, "black") for vn in voltage_levels]
    trafo_traces = []
    df_trafo_color = pd.DataFrame({"idx": indices_trafos, "color": trafos_colors})
    for color_val, grupo in df_trafo_color.groupby("color"):
        tension = u_colores.get(color_val, 'Otras tensiones.')
        trace = create_trafo_trace(net, trafos=grupo["idx"].tolist(), width=5, color=color_val,
            trace_name=f"U_nom (HV) trafos {tension} [KV]")
        trafo_traces.extend(_flatten(trace))

    # PREPARACION DE ELEMENTOS CRITICOS
    df1 = analisis_componentes[analisis_componentes['P_1%'] >= 90].copy()
    df2 = ranking_contingencias[ranking_contingencias['Ind_Sev'] > 1].copy()
    lista_elementos_criticos = list(set(df1['Nombre_Componente'].tolist() + df2['Contingencia'].tolist()))
    print(f'Se identificaron: {len(lista_elementos_criticos)} elementos criticos, entre el analisis en condicion "n" y "n-1".')
    lineas = []
    trafos = []
    for elemento in lista_elementos_criticos:
        if elemento[:3] == elemento[6:9]:
            id_t = df_trafo[df_trafo['name'] == elemento].index[0]
            trafos.append(id_t)
        else:
            id_l = df_lineas[df_lineas['name'] == elemento].index[0]
            lineas.append(id_l)

    # RESALTADO DE ELEMENTOS CRITICOS
    markers_lcrit = []
    if lineas:
        trace_lcrit = create_line_trace(net, lines=lineas, width=6, color="orange",
            trace_name="Lineas criticas")
        markers_lcrit = _flatten(trace_lcrit)
    markers_tcrit = []
    if trafos:
        trace_tcrit = create_trafo_trace(net, trafos=trafos, width=8, color="orange",
            trace_name="Trafos criticos")
        markers_tcrit = _flatten(trace_tcrit)

    # GRAFICAMOS
    all_traces = (bus_trace if isinstance(bus_trace, list) else _flatten(bus_trace)) \
                + line_traces + trafo_traces + markers_lcrit + markers_tcrit
    fig = draw_traces(all_traces, on_map=True, map_style='light', auto_open=False,
                    filename=f"Diagrama_tensiones_{nombre_estudio}.html", figsize=1.5, showlegend=True)
    ruta = Path(ruta_base) / f"Diagrama_tensiones_{nombre_estudio}.html"
    fig.write_html(ruta)
    print('Se genero correctamnte el diagrama del sistema.')
    print('='*80)
#%%
rta =rf"G:\Otros ordenadores\Augusto Bazan\Tesis\Codigo\Estudio_electrico_2026-08-28-21-31"
diagrama_elementos_criticos(net, analisis_componentes, ranking_contingencias, df_mtrafo, df_mline, nombre_estudio, Path(rta))
# %%
