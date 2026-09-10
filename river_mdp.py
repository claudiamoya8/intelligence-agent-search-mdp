#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
river_mdp.py — Parte 2 (MDP)

Cruce del río como Proceso de Decisión de Markov (MDP):

- Escenario: cuadrícula con orillas (primera y última columna, sin corriente) y río (columnas interiores).
- Islas (I): obstáculos no transitables (probabilidad de entrar = 0, el agente se queda).
- Salida (E): estado terminal con recompensa positiva.
- Peligros (P): casillas pisables con penalización fuerte (extensión opcional), configurables como terminales o no.
- Acciones: up, down, left, right, stay.
- Transiciones:
    * Si a != down:
        - Con prob. pdir = 1 - river_strength(col): intenta moverse en la dirección elegida.
        - Con prob. pdown = river_strength(col): la corriente empuja hacia abajo.
      Si el destino (por dirección o por corriente) es inválido (borde) o una isla -> el agente se queda.
    * Si a == down:
        - Movimiento determinista hacia abajo (si es inválido/isla, se queda).
- Fuerza de la corriente river_strength:
    * Columnas de los bordes (primera y última): 0.0
    * Columnas interiores: aleatorio uniforme entre 0.06 y 0.94, redondeado a 1 decimal.

- Recompensas:
    * Base: +100 al alcanzar la salida (E) y -1 por cada acción ejecutada (incluyendo "stay").
    * Extensión opcional: si se generan peligros (P), entrar en P añade una penalización fuerte (por defecto -100),
      y además se puede configurar si P es terminal o no.


Se resuelve con Value Iteration y se muestra la política óptima por consola.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple


# 1) Colores y utilidades de consola (estilo Parte 1)

USE_COLOR = True

_ANSI_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_MAGENTA = "\033[35m"


def paint(txt: str, style: str) -> str:
    """
    Aplica estilo ANSI al texto si USE_COLOR=True.
    
    Args:
        txt (str): Texto a colorear/estilizar.
        style (str): Secuencia ANSI (p. ej. '\033[31m') a aplicar.
    
    Returns:
        str: Texto con estilo aplicado (o sin cambios si USE_COLOR=False o style es vacío).
    """
    if (not USE_COLOR) or (not style):
        return txt
    return f"{style}{txt}{_ANSI_RESET}"


def print_banner(title: str) -> None:
    """
    Imprime el título principal del programa (sin marco).
    
    Args:
        title (str): Título a mostrar en consola.
    
    Returns:
        None: No devuelve nada; imprime por pantalla.
    """
    print(f"\n{title}\n")


def print_section(title: str) -> None:
    """
    Imprime un título de sección para separar bloques en consola.
    
    Args:
        title (str): Nombre de la sección.
    
    Returns:
        None: No devuelve nada; imprime por pantalla.
    """
    print(f"\n--- {title} ---")


def pedir_si_no(pregunta: str, por_defecto: bool = True) -> bool:
    """
    Pide al usuario una respuesta sí/no (s/n), con valor por defecto.
    
    Args:
        pregunta (str): Texto mostrado en el input.
        por_defecto (bool): Valor devuelto si el usuario pulsa ENTER.
    
    Returns:
        bool: True si la respuesta es afirmativa, False si es negativa.
    """
    while True:
        entrada = input(pregunta).strip().lower()
        if entrada == "":
            return bool(por_defecto)
        if entrada in ("s", "si", "sí", "y", "yes"):
            return True
        if entrada in ("n", "no"):
            return False
        print("Responde 's' o 'n'.")


def pedir_semilla() -> Optional[int]:
    """
    Pide una semilla opcional para reproducir el mismo tablero.
    
    Returns:
        int | None: Entero si el usuario introduce una semilla; None si pulsa ENTER (semilla aleatoria).
    """
    while True:
        entrada = input("Semilla (ENTER = aleatoria; escribe un entero para repetir el mismo tablero): ").strip()
        if entrada == "":
            return None
        try:
            return int(entrada)
        except ValueError:
            print("Semilla inválida: introduce un entero o pulsa ENTER.")



def pedir_entero(pregunta: str, por_defecto: int, minimo: Optional[int] = None, maximo: Optional[int] = None) -> int:
    """
    Pide un entero al usuario con soporte de valor por defecto y validación de rango.
    
    Args:
        pregunta (str): Texto mostrado en el input.
        por_defecto (int): Valor por defecto si el usuario pulsa ENTER.
        minimo (int | None): Mínimo permitido (inclusive). Si se da, se valida.
        maximo (int | None): Máximo permitido (inclusive). Si se da, se valida.
    
    Returns:
        int: Entero válido introducido por el usuario (o por_defecto).
    """
    while True:
        entrada = input(pregunta).strip()
        if entrada == "":
            return por_defecto
        try:
            val = int(entrada)
        except ValueError:
            print("Introduce un entero o pulsa ENTER.")
            continue
        if minimo is not None and val < minimo:
            print(f"El valor debe ser >= {minimo}.")
            continue
        if maximo is not None and val > maximo:
            print(f"El valor debe ser <= {maximo}.")
            continue
        return val
def formatear_celda(texto: str, ancho: int) -> str:
    """
    Formatea una celda del tablero a ancho fijo, aplicando color si procede.
    
    Args:
        texto (str): Contenido lógico de la celda (p. ej. 'CWCK', 'R', 'I', 'E', 'P', '').
        ancho (int): Ancho fijo (número de caracteres) con el que se imprimirá la celda.
    
    Returns:
        str: Texto alineado a ancho fijo y, si USE_COLOR=True, con color ANSI.
    """
    raw = texto.strip()
    style = ""
    if raw == "CWCKE":
        # El capitán está sobre la salida.
        style = _BOLD + _YELLOW
    elif raw == "CWCKP":
        style = _BOLD + _MAGENTA
    elif raw.startswith("CW"):
        style = _BOLD + _GREEN
    elif raw == "E":
        style = _BOLD + _YELLOW
    elif raw == "I":
        style = _BOLD + _RED
    elif raw == "P":
        style = _BOLD + _MAGENTA
    elif raw == "R":
        style = _CYAN
    return paint(raw.ljust(ancho)[:ancho], style)


# 2) Entorno del río (MDP)

State = Tuple[int, int]  # (fila, col)


def river_strength(ncols: int) -> List[float]:
    """
    Genera la fuerza de la corriente por columna según el enunciado.
    
    - Primera y última columna: 0.0 (orillas, sin corriente).
    - Columnas interiores: valor aleatorio U(0.06, 0.94) redondeado a 1 decimal.
    
    Args:
        ncols (int): Número de columnas del tablero.
    
    Returns:
        list[float]: Lista s tal que s[j] es la fuerza de corriente de la columna j.
    """
    s = []
    for j in range(ncols):
        if j == 0 or j == ncols - 1:
            s.append(0.0)
        else:
            s.append(round(random.uniform(0.06, 0.94), 1))
    return s


def in_bounds(nrows: int, ncols: int, s: State) -> bool:
    """
    Comprueba si un estado (fila, col) cae dentro de los límites del tablero.
    
    Args:
        nrows (int): Número de filas del tablero.
        ncols (int): Número de columnas del tablero.
        s (State): Estado (fila, col) a comprobar.
    
    Returns:
        bool: True si 0 <= fila < nrows y 0 <= col < ncols; False en caso contrario.
    """
    i, j = s
    return 0 <= i < nrows and 0 <= j < ncols

def aplicar_destino(env: Dict[str, object], s: State, dest: State) -> State:
    """
    Valida un destino y aplica la regla de 'rebote' contra bordes/islas.
    
    Si el destino está fuera del tablero o es una isla, el agente se queda en el estado actual s.
    
    Args:
        env (dict[str, object]): Entorno con 'nrows', 'ncols' e 'islands'.
        s (State): Estado actual.
        dest (State): Destino propuesto.
    
    Returns:
        State: Estado resultante (dest si es válido; s si es inválido o isla).
    """
    nrows = int(env["nrows"])
    ncols = int(env["ncols"])
    islas: set[State] = env["islands"]

    if (not in_bounds(nrows, ncols, dest)) or (dest in islas):
        return s
    return dest

def step_state(s: State, a: str) -> State:
    """
    Calcula el estado resultante de aplicar una acción (sin validar bordes/islas).
    
    Acciones soportadas: 'up', 'down', 'left', 'right', 'stay'.
    Si la acción no es reconocida, devuelve el mismo estado.
    
    Args:
        s (State): Estado actual.
        a (str): Acción a aplicar.
    
    Returns:
        State: Estado destino propuesto (sin comprobar límites ni islas).
    """
    i, j = s
    if a == "up":
        return (i - 1, j)
    if a == "down":
        return (i + 1, j)
    if a == "left":
        return (i, j - 1)
    if a == "right":
        return (i, j + 1)
    if a == "stay":
        return (i, j)
    return s


def generar_islas(nrows: int, ncols: int, nislas: int = 2) -> List[State]:
    """
    Genera posiciones de islas (obstáculos) sin primera ni última fila y sin repetir.
    
    Args:
        nrows (int): Número de filas del tablero.
        ncols (int): Número de columnas del tablero.
        nislas (int): Número de islas a generar.
    
    Returns:
        list[State]: Lista de coordenadas (fila, col) de las islas.
    """
    posibles = [(i, j) for i in range(1, nrows - 1) for j in range(1, ncols - 1)]
    # Evitar que bloqueen por completo: mantener variedad, pero sin más restricciones aquí.
    random.shuffle(posibles)
    return posibles[:nislas]



def generar_peligros(
    nrows: int,
    ncols: int,
    npeligros: int,
    islas: set[State],
    start: State,
    exit_s: State,
) -> set[State]:
    """
    Genera casillas peligrosas (P) pisables dentro del río (columnas interiores).
    
    Se evitan: islas, start y exit. Si npeligros excede los candidatos disponibles, se recorta.
    
    Args:
        nrows (int): Número de filas del tablero.
        ncols (int): Número de columnas del tablero.
        npeligros (int): Número de peligros a generar.
        islas (set[State]): Conjunto de islas (obstáculos) para evitar.
        start (State): Estado inicial (a evitar).
        exit_s (State): Estado de salida (a evitar).
    
    Returns:
        set[State]: Conjunto de casillas peligrosas generadas.
    """
    if npeligros <= 0:
        return set()

    candidatos = [(i, j) for i in range(nrows) for j in range(1, ncols - 1)]
    prohibidos = set(islas) | {start, exit_s}
    candidatos = [c for c in candidatos if c not in prohibidos]
    if not candidatos:
        return set()

    npeligros = min(npeligros, len(candidatos))
    random.shuffle(candidatos)
    return set(candidatos[:npeligros])
def generar_salida(nrows: int, ncols: int) -> State:
    """
    Genera una salida en la última columna (orilla derecha).
    
    Args:
        nrows (int): Número de filas del tablero.
        ncols (int): Número de columnas del tablero.
    
    Returns:
        State: Coordenadas (fila, col) de la salida.
    """
    return (random.randrange(0, nrows), ncols - 1)


def generar_entorno(
    nrows: int = 7,
    ncols: int = 6,
    nislas: int = 2,
    npeligros: int = 0,
    hazard_terminal: bool = True,
    hazard_penalty: float = -100.0,
) -> Dict[str, object]:
    """
    Crea el entorno del río (MDP), incluyendo corriente, islas, salida y peligros opcionales.
    
    Claves principales del diccionario devuelto:
    - 'nrows', 'ncols': dimensiones.
    - 'start': estado inicial.
    - 'exit': estado terminal de salida.
    - 'islands': conjunto de islas (obstáculos).
    - 'hazards': conjunto de peligros (pisables).
    - 'hazard_terminal': si True, los peligros son terminales.
    - 'hazard_penalty': penalización al entrar en un peligro.
    - 'strength': lista con river_strength por columna.
    - 'actions': lista de acciones disponibles.
    
    Args:
        nrows (int): Número de filas.
        ncols (int): Número de columnas.
        nislas (int): Número de islas (obstáculos no transitables).
        npeligros (int): Número de casillas peligrosas (P) pisables (extensión opcional).
        hazard_terminal (bool): Si True, caer en P termina el episodio ("muerte").
        hazard_penalty (float): Penalización al entrar en P (típicamente -100).
    
    Returns:
        dict[str, object]: Entorno listo para Value Iteration y simulación.
    """
    start = (0, 0)  # orilla izquierda, fila 0
    strengths = river_strength(ncols)
    islas = set(generar_islas(nrows, ncols, nislas=nislas))

    # La salida va en la última columna. Como las islas ya no pueden estar en la última columna,
    # aquí solo nos aseguramos de que no coincida con el start por seguridad.
    salida = generar_salida(nrows, ncols)
    if salida == start:
        salida = (nrows - 1, ncols - 1)

    peligros = generar_peligros(
        nrows=nrows,
        ncols=ncols,
        npeligros=npeligros,
        islas=islas,
        start=start,
        exit_s=salida,
    )

    return {
        "nrows": nrows,
        "ncols": ncols,
        "start": start,
        "exit": salida,
        "islands": islas,
        "hazards": peligros,
        "hazard_terminal": hazard_terminal,
        "hazard_penalty": float(hazard_penalty),
        "strength": strengths,
        "actions": ["up", "down", "left", "right", "stay"],
    }


def transiciones(env: Dict[str, object], s: State, a: str) -> List[Tuple[State, float]]:
    """
    Calcula la distribución de transición P(s' | s, a).
    
    Reglas:
    - Si s es terminal (exit o hazard terminal): devuelve [(s, 1.0)].
    - Si a == 'down': movimiento determinista hacia abajo (o quedarse si inválido/isla).
    - Si a != 'down':
        * Con prob. pdir = 1 - river_strength(col): intenta moverse en la dirección elegida.
        * Con prob. pdown = river_strength(col): la corriente empuja hacia abajo.
      Si un destino es inválido o isla, el agente se queda en s.
    
    Args:
        env (dict[str, object]): Entorno del río.
        s (State): Estado actual.
        a (str): Acción elegida.
    
    Returns:
        list[tuple[State, float]]: Lista de pares (s', probabilidad) que suma 1.0.
    """
    strength: List[float] = env["strength"]

    # Terminal: si ya estás en exit, te quedas
    if s == env["exit"]:
        return [(s, 1.0)]

    hazards: set[State] = env.get("hazards", set())
    hazard_terminal = bool(env.get("hazard_terminal", True))
    if hazard_terminal and (s in hazards):
        return [(s, 1.0)]


    if a == "down":
        dest = aplicar_destino(env, s, step_state(s, "down"))
        return [(dest, 1.0)]

    pdown = strength[s[1]]
    pdir = 1.0 - pdown

    dest_dir = aplicar_destino(env, s, step_state(s, a))
    dest_down = aplicar_destino(env, s, step_state(s, "down"))


    # Combinar si coinciden
    if dest_dir == dest_down:
        return [(dest_dir, 1.0)]
    return [(dest_dir, pdir), (dest_down, pdown)]


def recompensa(env: Dict[str, object], s: State, a: str, sp: State) -> float:
    """
    Recompensa por transición R(s, a, s') para el MDP del río.
    
    Reglas base:
    - Si el agente alcanza la salida (s' == exit): +100.
    - En cualquier otra transición no terminal: -1 (coste por acción).
    
    Extensión opcional (casillas peligrosas 'P'):
    - Entrar en un peligro añade una penalización fuerte (por defecto -100).
    - El usuario puede elegir si 'P' es terminal (muerte) o no.
    
    Nota:
    - Las islas son obstáculos no transitables: no existe el estado "en una isla".
    
    Args:
        env (dict[str, object]): Entorno del río.
        s (State): Estado actual.
        a (str): Acción ejecutada.
        sp (State): Estado siguiente.
    
    Returns:
        float: Recompensa inmediata asociada a la transición.
    """
    hazards: set[State] = env.get("hazards", set())
    hazard_terminal = bool(env.get("hazard_terminal", True))
    hazard_penalty = float(env.get("hazard_penalty", -100.0))

        # Estados terminales: si ya estás en terminal, no se ejecutan acciones.
    if s == env["exit"] or (hazard_terminal and (s in hazards)):
        return 0.0

    r = -1.0  # coste por acción (incluye el último paso)

    if sp == env["exit"]:
        r += 100.0
    elif (sp in hazards) and (s not in hazards):
        r += hazard_penalty

    return r

# ============================================================
# 3) Value Iteration
# ============================================================

def estados(env: Dict[str, object]) -> List[State]:
    """
    Devuelve la lista de estados válidos del entorno (todas las celdas menos las islas).
    
    Args:
        env (dict[str, object]): Entorno que contiene 'nrows', 'ncols' e 'islands'.
    
    Returns:
        list[State]: Estados válidos para el MDP.
    """
    nrows = int(env["nrows"])
    ncols = int(env["ncols"])
    islas: set[State] = env["islands"]
    out = []
    for i in range(nrows):
        for j in range(ncols):
            s = (i, j)
            if s not in islas:
                out.append(s)
    return out


def value_iteration(
    env: Dict[str, object],
    gamma: float = 0.95,
    theta: float = 1e-6,
    max_iter: int = 10_000,
) -> Tuple[Dict[State, float], Dict[State, str]]:
    """
    Resuelve el MDP mediante Value Iteration y devuelve V* y una política greedy.
    
    Args:
        env (dict[str, object]): Entorno del río.
        gamma (float): Factor de descuento (0 < gamma <= 1).
        theta (float): Umbral de convergencia (parada cuando el cambio máximo < theta).
        max_iter (int): Número máximo de iteraciones.
    
    Returns:
        tuple[dict[State, float], dict[State, str]]:
            - V: diccionario con el valor óptimo V*(s).
            - pi: política greedy respecto a V (acción por estado).
    """
    S = estados(env)
    A: List[str] = env["actions"]
    V: Dict[State, float] = {s: 0.0 for s in S}
    hazards: set[State] = env.get("hazards", set())
    hazard_terminal = bool(env.get("hazard_terminal", True))


    for _it in range(max_iter):
        delta = 0.0
        for s in S:
            if s == env["exit"] or (hazard_terminal and (s in hazards)):
                continue
            best = None
            for a in A:
                q = 0.0
                for sp, p in transiciones(env, s, a):
                    r = recompensa(env, s, a, sp)
                    q += p * (r + gamma * V[sp])
                if best is None or q > best:
                    best = q
            assert best is not None
            delta = max(delta, abs(best - V[s]))
            V[s] = best
        if delta < theta:
            break

    # Política greedy
    pi: Dict[State, str] = {}
    for s in S:
        if s == env["exit"] or (hazard_terminal and (s in hazards)):
            pi[s] = "·"
            continue
        best_a = "up"
        best_q = -1e18
        for a in A:
            q = 0.0
            for sp, p in transiciones(env, s, a):
                r = recompensa(env, s, a, sp)
                q += p * (r + gamma * V[sp])
            if q > best_q:
                best_q = q
                best_a = a
        pi[s] = best_a
    return V, pi

# 4) Impresión del entorno y la política

_ARROW = {"up": "↑", "down": "↓", "left": "←", "right": "→", "stay": "·", "·": "·"}

def mostrar_entorno(env: Dict[str, object], agente: Optional[State] = None, ancho: int = 6) -> None:
    """
    Imprime en consola el tablero del entorno y una leyenda.
    
    Args:
        env (dict[str, object]): Entorno del río.
        agente (State | None): Posición del agente a mostrar. Si es None, se muestra el inicio.
        ancho (int): Ancho fijo de cada celda impresa.
    
    Returns:
        None: No devuelve nada; imprime por pantalla.
    """
    nrows = int(env["nrows"])
    ncols = int(env["ncols"])
    islas: set[State] = env["islands"]
    exit_s: State = env["exit"]
    start: State = env["start"]
    hazards: set[State] = env.get("hazards", set())
    hazard_terminal = bool(env.get("hazard_terminal", True))
    hazard_penalty = float(env.get("hazard_penalty", -100.0))


    # Si no se especifica agente, mostramos el inicio (CWCK) por defecto
    if agente is None:
        agente = start

    print("Leyenda:")
    print("  CWCK = Capitán Willard y Kurtz")
    print("  R    = Río (corriente en columnas interiores)")
    print("  I    = Isla (obstáculo)")
    print("         (no es una casilla peligrosa: no hay penalización; simplemente no se puede entrar)")

    if hazards:
        modo = "terminal" if hazard_terminal else "no terminal"
        print(f"  P    = Peligro (penalización {hazard_penalty:.0f}; {modo})")
    print("  E    = Salida")
    print("  (celda vacía) = Orilla (sin corriente)")
    print("")

    # Cabecera con el índice de columna (1..ncols)
    header = []
    for j in range(ncols):
        header.append("|" + str(j + 1).center(ancho)[:ancho])
    print("".join(header) + "|")

    for i in range(nrows):
        fila = []
        for j in range(ncols):
            s = (i, j)
            if s == agente and s == exit_s:
                tag = "CWCKE"
            elif s == agente and s in hazards:
                tag = "CWCKP"
            elif s == agente:
                tag = "CWCK"
            elif s == exit_s:
                tag = "E"
            elif s in hazards:
                tag = "P"
            elif s in islas:
                tag = "I"
            else:
                # Orillas: celda vacía (como en el ejemplo del enunciado)
                if j == 0 or j == ncols - 1:
                    tag = ""
                else:
                    tag = "R"
            fila.append("|" + formatear_celda(tag, ancho))
        print("".join(fila) + "|")

def mostrar_strength(env: Dict[str, object]) -> None:
    """
    Imprime por consola los valores de river_strength por columna.
    
    Args:
        env (dict[str, object]): Entorno del río con la clave 'strength'.
    
    Returns:
        None: No devuelve nada; imprime por pantalla.
    """
    s: List[float] = env["strength"]
    print("\nRiver_strength por columna:")
    for idx, v in enumerate(s, start=1):
        print(f"- columna {idx}: {v:.1f}")


def mostrar_politica(env: Dict[str, object], pi: Dict[State, str], ancho: int = 4) -> None:
    """
    Imprime en consola la política óptima como una tabla de flechas.
    
    Args:
        env (dict[str, object]): Entorno del río.
        pi (dict[State, str]): Política (acción por estado).
        ancho (int): Ancho de cada celda en la tabla.
    
    Returns:
        None: No devuelve nada; imprime por pantalla.
    """
    nrows = int(env["nrows"])
    ncols = int(env["ncols"])
    islas: set[State] = env["islands"]
    exit_s: State = env["exit"]
    hazards: set[State] = env.get("hazards", set())

    print("\nPolítica óptima (flechas):")
    # Cabecera con índices de columna (1..ncols), alineada con el ancho de celda
    header = []
    for j in range(ncols):
        header.append(str(j + 1).center(ancho)[:ancho])
    print("".join(header))

    for i in range(nrows):
        fila = []
        for j in range(ncols):
            s = (i, j)
            if s in islas:
                fila.append(paint(" I ".ljust(ancho), _BOLD + _RED))
            elif s == exit_s:
                fila.append(paint(" E ".ljust(ancho), _BOLD + _YELLOW))
            elif s in hazards:
                fila.append(paint(" P ".ljust(ancho), _BOLD + _MAGENTA))
            else:
                a = pi.get(s, "·")
                fila.append(f" {_ARROW.get(a,'·')} ".ljust(ancho))
        print("".join(fila))


# 5) Simulación con la política

def sample_next(env: Dict[str, object], s: State, a: str) -> State:
    """
    Muestrea un estado siguiente s' según la distribución P(s' | s, a).
    
    Args:
        env (dict[str, object]): Entorno del río.
        s (State): Estado actual.
        a (str): Acción elegida.
    
    Returns:
        State: Estado siguiente muestreado.
    """
    trans = transiciones(env, s, a)
    x = random.random()
    acc = 0.0
    for sp, p in trans:
        acc += p
        if x <= acc:
            return sp
    return trans[-1][0]


def simular(env: Dict[str, object], pi: Dict[State, str], max_steps: int = 200, verbose: bool = False) -> List[State]:
    """
    Simula un episodio siguiendo la política π desde el estado inicial.
    
    Si verbose=True, imprime una tabla con:
    Step | s | a | s' | motivo | r | total
    
    Args:
        env (dict[str, object]): Entorno del río.
        pi (dict[State, str]): Política a seguir.
        max_steps (int): Máximo número de pasos de simulación.
        verbose (bool): Si True, imprime el trazado paso a paso.
    
    Returns:
        list[State]: Secuencia de estados visitados (incluye el estado inicial).
    """

    s = env["start"]
    path = [s]
    total = 0.0

    hazards: set[State] = env.get("hazards", set())
    hazard_terminal = bool(env.get("hazard_terminal", True))

    # Anchos generosos (para evitar que se descuadre con textos más largos)
    w_step = 6
    w_s = 12
    w_a = 10
    w_sp = 12
    w_mot = 26
    w_r = 8
    w_tot = 10

    if verbose:
        col_sp = "s'"
        header = (
            f"{'Step':^{w_step}} | "
            f"{'s':^{w_s}} | "
            f"{'a':^{w_a}} | "
            f"{col_sp:^{w_sp}} | "
            f"{'motivo':^{w_mot}} | "
            f"{'r':^{w_r}} | "
            f"{'total':^{w_tot}}"
        )
        sep = "-+-".join([
            "-" * w_step, "-" * w_s, "-" * w_a, "-" * w_sp,
            "-" * w_mot, "-" * w_r, "-" * w_tot
        ])
        print("\n" + header)
        print(sep)

    for t in range(1, max_steps + 1):
        if s == env["exit"] or (hazard_terminal and (s in hazards)):
            break

        a = pi.get(s, "right")
        sp = sample_next(env, s, a)
        r = recompensa(env, s, a, sp)
        total += r

        # Explicación del resultado (dirección vs corriente)
        if a == "down":
            motivo = "down (determinista)"
        elif a == "stay":
            dest_down = aplicar_destino(env, s, step_state(s, "down"))
            if sp == s:
                motivo = "espera"
            elif sp == dest_down:
                motivo = "corriente ↓"
            else:
                motivo = "bloqueado/ambos"
        else:
            dest_dir = aplicar_destino(env, s, step_state(s, a))
            dest_down = aplicar_destino(env, s, step_state(s, "down"))

            if sp == dest_dir and sp != dest_down:
                motivo = "dirección elegida"
            elif sp == dest_down and sp != dest_dir:
                motivo = "corriente ↓"
            else:
                motivo = "bloqueado/ambos"

        if verbose:
            print(
                f"{t:>{w_step}} | "
                f"{str(s):>{w_s}} | "
                f"{a:^{w_a}} | "
                f"{str(sp):>{w_sp}} | "
                f"{motivo:<{w_mot}} | "
                f"{r:>{w_r}.0f} | "
                f"{total:>{w_tot}.0f}"
            )

        path.append(sp)
        s = sp

    if verbose:
        estado_fin = "EXIT" if path[-1] == env["exit"] else ("PELIGRO" if (hazard_terminal and (path[-1] in hazards)) else "NO EXIT")
        print(f"\nFin: {estado_fin}  | pasos={len(path)-1} | retorno_total={total:.0f}")

    return path

# 6) Main

def main() -> None:
    """
    Punto de entrada del programa.
    
    - Pregunta opciones al usuario (colores, semilla, número de peligros y si son terminales).
    - Genera el entorno.
    - Resuelve el MDP con Value Iteration.
    - Muestra entorno, política y una simulación.
    
    Returns:
        None: No devuelve nada; ejecuta el flujo principal e imprime por pantalla.
    """
    global USE_COLOR

    print_banner("PROYECTO FIA: BUSCANDO AL CORONEL KURTZ (PARTE 2 - RÍO MDP)")

    USE_COLOR = pedir_si_no("¿Desea usar colores en la consola? [s/n] (por defecto SÍ se usarán): ", por_defecto=True)

    seed = pedir_semilla()
    if seed is not None:
        random.seed(seed)

    nrows, ncols, nislas = 7, 6, 2
    npeligros = pedir_entero("Número de casillas peligrosas 'P' (ENTER = 0): ", por_defecto=0, minimo=0)
    hazard_terminal = True
    if npeligros > 0:
        hazard_terminal = pedir_si_no(
            "¿Las casillas peligrosas son terminales (muerte)? [s/n] (por defecto SÍ): ",
            por_defecto=True,
        )

    env = generar_entorno(
        nrows=nrows,
        ncols=ncols,
        nislas=nislas,
        npeligros=npeligros,
        hazard_terminal=hazard_terminal,
        hazard_penalty=-100.0,
    )

    print_section("Entorno generado")
    mostrar_entorno(env)
    mostrar_strength(env)

    print_section("Resolviendo MDP (Value Iteration)")
    V, pi = value_iteration(env, gamma=0.95, theta=1e-6)
    mostrar_politica(env, pi)

    print_section("Simulación siguiendo la política")
    path = simular(env, pi, max_steps=200, verbose=True)
    hazards: set[State] = env.get("hazards", set())
    hazard_terminal = bool(env.get("hazard_terminal", True))
    etiqueta = "(EXIT)" if path[-1] == env["exit"] else ("(PELIGRO)" if (hazard_terminal and (path[-1] in hazards)) else "")
    print("\nEstado final:", path[-1], etiqueta)

    # Render final con agente en última posición
    print_section("Entorno (posición final)")
    mostrar_entorno(env, agente=path[-1])

if __name__ == "__main__":
    main()