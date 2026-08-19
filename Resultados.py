from Analisis_estadistico import aplicar_tema_light, ALTO, ANCHO, DPI
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging
import pandas as pd

# --- Configuracion logging ---
logger = logging.getLogger(__name__)

def formatear_resultados(valor, digitos):
    if valor == 0 or pd.isna(valor):
        return "00.000"
    parte_entera = int(abs(valor))
    if parte_entera == 0:
        digitos_enteros = 1
    else:
        digitos_enteros = len(str(parte_entera))
    decimales_permitidos = max(0, digitos - digitos_enteros)
    return f"{valor:.{decimales_permitidos}f}"

def grafica_elementos_criticos(df_analisis, rta_cn):
    df_analisis = df_analisis.head(20).copy()
    nombre = 'Elementos_criticos(Graf. Barras apiladas)'
    rta_cn = Path(rta_cn)
    df = df_analisis.copy()
    componentes = df['Nombre_Componente'].astype(str).tolist()
    p0 = df['Cargabilidad_Max'].astype(float).to_numpy()
    p1 = df['P_1%'].astype(float).to_numpy()
    p5 = df['P_5%'].astype(float).to_numpy()
    x = np.arange(len(componentes))
    ancho_barra = 0.25
    fig, ax = plt.subplots(figsize=(ANCHO + 2, ALTO))
    barras_p0 = ax.bar(x - ancho_barra, p0, ancho_barra, label='Maxima')
    barras_p1 = ax.bar(x, p1, ancho_barra, label='P_1%')
    barras_p5 = ax.bar(x + ancho_barra, p5, ancho_barra, label='P_5%')
    ax.set_ylim(0, max(p0.max(), p1.max(), p5.max()) + 10)
    ax.set_xticks(x)
    ax.set_xticklabels(componentes, rotation=45, ha='right')
    ax.set_xlabel('Ranking de componentes críticos')
    ax.set_ylabel('Cargabilidad [%]')
    ax.legend()
    aplicar_tema_light(
        ax,
        titulo='Comportamiento de los elementos criticos.',
        subtitulo=nombre,
        xlabel='Ranking de componentes críticos',
        ylabel='Cargabilidad [%]'
    )
    plt.tight_layout()
    plt.savefig(rta_cn / f"{nombre}.png", dpi=DPI)
    plt.close()

def resultados_diagnostico(analisis_componentes: pd.DataFrame, ranking_contingencias:pd.DataFrame, df_duraci: pd.DataFrame,
                        ruta_base:str|Path, nombre_estudio:str, datos_estudio:dict):
    ruta_base = Path(ruta_base)/f'Resultados_{nombre_estudio}.txt'
    # Tiempo percentil 5%
    df_duraci = df_duraci.copy()
    horas_serie = df_duraci['duracion'].sum()
    t_p1 = horas_serie * 0.01
    t_p5 = horas_serie * 0.05
    # preparacion is
    df_is = ranking_contingencias.query('Ind_Sev >= 1').copy()
    # CONDICION N
    with open(ruta_base, "w", encoding="utf-8") as archivo:
        archivo.write(f'\n{'='*80}')
        archivo.write(f'\nRESULTADOS CONDICION N')
        archivo.write(f'\n{'='*80}\n')
        archivo.write(f'-> Los elementos criticos identificados (Elemento - P1% - P5%)')
        archivo.write(f'\n-> La duración del estudio considerando: {datos_estudio['numero_series']} series, comprende {horas_serie * datos_estudio['numero_series']} [Hrs]')
        archivo.write(f'\n-> El percentil 1% se considera un comportamiento temporal.')
        archivo.write(f'\n-> El percentil 5% se considera un comportamiento permanente.')
        archivo.write(f'\n-> El P1% representa {t_p1:.2f} [Hrs] del tiempo total de estudio {horas_serie} [Hrs] que son la duración de una serie.')
        archivo.write(f'\n-> El P5% representa {t_p5:.2f} [Hrs] del tiempo total de estudio {horas_serie} [Hrs]que son la duración de una serie.\n')
        archivo.write('\n[RNK] |  COMPONENTE  |  P1%   |  P5%')
        for num,componente in analisis_componentes.iterrows():
            p1 = formatear_resultados(round(float(componente['P_1%']), 2), 4)
            p5 = formatear_resultados(round(float(componente['P_5%']), 2), 4)
            archivo.write(f'\n{num:>4}. | {componente['Nombre_Componente']:>12} | {p1:>5}  | {p5:>5}')
        archivo.write(f'\n{'='*80}\n')
        archivo.write(f'\n\n{'='*80}')
        archivo.write(f'\nRESULTADOS CONDICIOPN N-1 (CONTINGENCIAS)')
        archivo.write(f'\n{'='*80}\n')
        archivo.write(f'-> El PIp (performance Index of active power) es un resultado obtenido por escenario que toma en cuenta')
        archivo.write(f'\n    la cargabilidad de todos los elementos activos de la red en dicho escenario.')
        archivo.write(f'\n-> El IS (Indice de severidad) es un resultado promedio de las series consecuencia del PIp y de la')
        archivo.write(f'\n    duracion horaria de cada escenario.')
        archivo.write(f'\n-> El PIp considera un escenario unico mientras que el IS considera todos los escenarios del periodo de estudio')
        archivo.write(f'\n\n[Pos] | CONTINGENCIA  |   IS  |  PIp(mas alto)')
        for num, componente in df_is.iterrows():
            pip = formatear_resultados(round(float(componente['PIp_max']), 2), 3)
            isev = formatear_resultados(round(float(componente['Ind_Sev']), 2), 3)
            archivo.write(f'\n{num:>4}. | {componente['Contingencia']:>13} | {isev:>4}  |  {pip:>13}')
        archivo.write(f'\n{'='*80}\n')
        return ruta_base

def resultados_refuerzos_propuestos(resultados:str|Path, ref_propuestos:list):
    with open(resultados, "a", encoding="utf-8") as archivo:
        archivo.write(f'\n\n{'='*80}')
        archivo.write(f'\nEVALUACION DE REFUERZOS PROPUESTO POR EL PROGRAMA')
        archivo.write(f'\n{'='*80}')
        archivo.write(f'\n-> A continuacion se presentara una tabla que compara el comportamiento de la red base con los')
        archivo.write(f'\n    refuerzos propuestos a traves del indice de severidad y el numero de violaciones total a lo')
        archivo.write(f'\n    largo del periodo de estudio.')
        archivo.write(f'\n\n[NUM] |     REFUERZO    |   IS  |  NUMERO DE VIOLACIONES (Condicion "n")')
        for num, fila in enumerate(ref_propuestos):
            isev = formatear_resultados(round(float(fila[0]), 2), 3)
            n_violaciones = int(fila[1])
            archivo.write(f'\n{num:>4}. | {fila[2]:>15} | {isev:>4}  |  {n_violaciones:>20}')
        archivo.write(f'\n{'='*80}\n')

def resultados_alternativas_propuestas(ruta:str|Path, df_resultados:pd.DataFrame, alternativas:str):
    ruta_base = Path(ruta)/f'Resultados_cartera_{alternativas}.txt'
    def costo_redondeado(costo):
        try:
            costo = round(float(costo), 1)
            return costo
        except:
            return costo
    
    def fechas(fecha):
        try:
            f = pd.to_datetime(fecha)
            return f.strftime(f'%Y-%m-%d')
        except:
            return "          "
    
    with open(ruta_base, "a", encoding="utf-8") as archivo:
        archivo.write(f'\n{'='*80}')
        archivo.write(f'\nEVALUACION DE ALTERNATIVAS PROPUESTAS POR EL USUARIO PARA {alternativas}')
        archivo.write(f'\n{'='*80}')
        archivo.write(f'\n-> A continuacion se presentara una tabla que compara el comportamiento de la red base con las')
        archivo.write(f'\n    alternativas propuestas para la cartera {alternativas} a traves del indice de severidad en ')
        archivo.write(f'\n    Condicion "n" y "n-1" para elemento de monitoreo, costo total de la alternativa y las fechas')
        archivo.write(f'\n    de ingreso estimadas.')
        archivo.write(f'\n-> "RB" Son los datos de la red base (Sin refuerzos).')
        archivo.write(f'\n\n[NUM] |  ALT  |  IS(n) | ELMT(MONITOREO) | IS(n-1) | COSTO TOTAL [$] |   FECHA_1  |   FECHA_2')
        for num, fila in df_resultados.iterrows():
            alternativa = fila['Alternativa']
            is_n = formatear_resultados(round(float(fila['IS(n)']), 2), 3)
            monitoreo = fila['Elemento de monitoreo']
            isev = formatear_resultados(round(float(fila['IS (n-1)']), 2), 3)
            costo = costo_redondeado(fila['Costo total $'])
            fecha_1 = fechas(fila['Fecha (n)'])
            fecha_2 = fechas(fila['Fecha (n-1)'])
            archivo.write(f'\n{num:>4}. |  {alternativa:>3}  |  {is_n:>4}  | {monitoreo:>15} | {isev:>7} | {costo:>15} | {fecha_1} | {fecha_2}')
        archivo.write(f'\n{'='*80}\n')

def resultados_escenarios_criticos (df_escenarios_p1, df_escenarios_p2, rta_base, nombre_bd):
    ruta_base = Path(rta_base)/f'Resultados_{nombre_bd}_(Esc_Criticos).txt'
    with open(ruta_base, "a", encoding="utf-8") as archivo:
        archivo.write(f'\n\n{'='*80}')
        archivo.write(f'\nANALISIS DE ESCENARIOS CRITICOS')
        archivo.write(f'\n{'='*80}')
        archivo.write(f'\nLa maxima comprende al percentil 99.7% y la minima al percentil 0.3%.')
        archivo.write(f'\nEl analisis de escenarios se compone de 2 partes.')
        archivo.write(f'\n-> 1era Parte: Comprende escenarios de maxima y minima: generacion sincrona, generacion renovable')
        archivo.write(f'\n    y demanda, segun los años elegidos.')
        archivo.write(f'\n\n[NUM] |       ESCENARIO CRITICO       | ETAPA | SERIE | BLOQUE')
        for id, fila in df_escenarios_p1.iterrows():
            etapa = int(fila['Etapa'])
            serie = int(fila['Serie'])
            bloque = int(fila['Bloque'])
            archivo.write(f'\n{id:>4}. | {fila['Escenarios criticos']:>29} | {etapa:>5} | {serie:>5} | {bloque:>6}')
        archivo.write(f'\n\n-> 2da Parte: Comprende escenarios de maxima y minima transferencia segun los años elegidos, entre')
        archivo.write(f'\n    grupos de elementos elegidos.')
        archivo.write(f'\n\n[NUM] |      NOMBRE IDENTIFICADOR      | ETAPA | SERIE | BLOQUE |     MW    | ELEMENTOS')
        for id, fila in df_escenarios_p2.iterrows():
            nombre = fila['Interconexion'] + '_' + fila['Lectura'] + '_' + str(fila['Año'])
            etapa = int(fila['Etapa'])
            serie = int(fila['Serie'])
            bloque = int(fila['Bloque'])
            potencia = formatear_resultados(round(float(fila['Total_MW']), 2), 5)
            archivo.write(f'\n{id:>4}. | {nombre:>30} | {etapa:>5} | {serie:>5} | {bloque:>6} | {potencia:>9} | {fila['Elementos']}')
        archivo.write(f'\n{'='*80}\n')