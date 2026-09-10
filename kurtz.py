import random

#------------------------------------------------------------
# 1) Movimiento en rejilla 4-conexa
#------------------------------------------------------------

DIRS = { 
    "U": (-1, 0),  # arriba
    "D": (1, 0),   # abajo
    "L": (0, -1),  # izquierda
    "R": (0, 1),   # derecha
}

ALL_DIRS = ("U", "D", "L", "R")
KEY_TO_DIR = {"w": "U", "s": "D", "a": "L", "d": "R"}
DIR_TO_KEY = {"U": "w", "D": "s", "L": "a", "R": "d"}

# Flechas para recomendaciones en modo manual (formato compacto tipo enunciado)
DIR_ARROW = {"U": "^", "D": "v", "L": "<", "R": ">"}
# Lo usamos cuando hay empates en la frontera
# Primero derecha, luego abajo, luego izquierda y finalmente arriba.
FRONTIER_DIR_ORDER = ("R", "D", "L", "U")

#------------------------------------------------------------
# Colores ANSI para el tablero 
#------------------------------------------------------------
# Por defecto activado. Si tu terminal no soporta ANSI, ponlo a False.
USE_COLOR = True

_ANSI_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM  = "\033[2m"

_RED    = "\033[31m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_BLUE   = "\033[34m"
_CYAN   = "\033[36m"


def paint(txt: str, style: str) -> str:
    """Aplica estilo ANSI al texto si USE_COLOR=True."""
    if (not USE_COLOR) or (not style):
        return txt
    return f"{style}{txt}{_ANSI_RESET}"


def color_for_tag(raw_tag: str) -> str:
    """Decide el color según la etiqueta real (sin padding).

    La prioridad es importante cuando hay combinaciones (p.ej. P?E?):
    si hay peligro, se colorea como peligro.
    """
    t = raw_tag.strip()
    if not t:
        return ""

    # Peligros deducidos con certeza
    if ("P!" in t) or ("S!" in t):
        return _BOLD + _RED

    # Peligros posibles
    if ("P?" in t) or ("S?" in t) or (t == "?"):
        return _YELLOW

    # Salida / candidatas (si no hay peligro)
    if (t == "E") or ("E!" in t):
        return _BOLD + _CYAN
    if "E?" in t:
        return _CYAN

    # Capitán (CW / CWK + subíndices)
    if t.startswith("CW"):
        return _BOLD + _GREEN

    # Visitadas / seguras (según tu leyenda actual)
    if t == "v":
        return _GREEN
    if t == "✓":
        return _BLUE

    # Desconocidas
    if t == "*":
        return _DIM

    return ""


def colorize_cell(padded_text: str, raw_tag: str) -> str:
    """Colorea una celda YA formateada a ancho fijo (padded_text)."""
    return paint(padded_text, color_for_tag(raw_tag))



def print_banner(title: str) -> None:
    """Imprime el título principal del programa (sin marco).

    En versiones anteriores se mostraba un "marco" de '=' alrededor del título.
    Aquí lo dejamos más limpio para que la salida sea más compacta.
    """
    print(f"\n{title}\n")

def print_section(title: str) -> None:
    """Imprime un título de sección para separar bloques en consola.

    No afecta a la lógica del juego: solo mejora la legibilidad de la salida
    (mapa, leyendas, modo de ejecución, etc.).

    Args:
        title: Texto del encabezado a mostrar.
    """
    print(f"\n--- {title} ---")

#------------------------------------------------------------
# 2) Utilidades de rejilla (1-indexado)
#------------------------------------------------------------

def esta_en_tablero(tam: int, celda: tuple[int, int]) -> bool:
    """Comprueba si una celda está dentro del tablero tam×tam (1-indexado).

    Args:
        tam: Tamaño del tablero.
        celda: Celda (fila, col) con fila y columna en 1..tam.

    Returns:
        True si 1<=fila<=tam y 1<=col<=tam; False en caso contrario.
    """
    fila, col = celda
    return 1 <= fila <= tam and 1 <= col <= tam

def mover_posicion(celda: tuple[int, int], direccion: str) -> tuple[int, int]:
    """Devuelve la celda resultante de aplicar un movimiento ortogonal.

    Nota: no comprueba límites; usa esta_en_tablero() si lo necesitas.

    Args:
        celda: Celda (fila, col).
        direccion: Dirección en {"U","D","L","R"}.

    Returns:
        Nueva celda (fila, col) tras aplicar DIRS[direccion].
    """
    df, dc = DIRS[direccion]
    return (celda[0] + df, celda[1] + dc)

def vecinos_ortogonales(tam: int, celda: tuple[int, int]) -> list[tuple[int, int]]:
    """Devuelve los vecinos válidos 4-conexos de una celda (1-indexado).

    Args:
        tam: Tamaño del tablero.
        celda: Celda (fila, col).

    Returns:
        Lista de vecinos dentro del tablero (arriba/abajo/izquierda/derecha).
    """
    candidatas = [
        mover_posicion(celda, "U"),
        mover_posicion(celda, "D"),
        mover_posicion(celda, "L"),
        mover_posicion(celda, "R"),
    ]

    vecinos = []
    for v in candidatas:
        if esta_en_tablero(tam, v):
            vecinos.append(v)
    return vecinos

def todas_las_celdas(tam: int) -> list[tuple[int, int]]:
    """Lista de todas las celdas del tablero (1..tam).

    Args:
        tam: Tamaño del tablero.

    Returns:
        Lista [(1,1), (1,2), ..., (tam,tam)].
    """
    celdas: list[tuple[int, int]] = []
    for fila in range(1, tam + 1):
        for col in range(1, tam + 1):
            celdas.append((fila, col))
    return celdas

def distancia_manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Distancia Manhattan entre dos celdas.

    Se usa como heurística en GBFS y A* (rejilla 4-conexa con coste 1 por paso).

    Args:
        a: Celda (fila, col).
        b: Celda (fila, col).

    Returns:
        |a.fila-b.fila| + |a.col-b.col|.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def format_pos_set(ps: set[tuple[int, int]], limit: int = 10) -> str:
    """Formatea un conjunto de celdas para mostrarlo por consola sin ruido.

    Args:
        ps: Conjunto de posiciones (fila,col).
        limit: Máximo de celdas a listar explícitamente antes de resumir.
    Returns:
        Texto con la lista ordenada o un resumen tipo "N celdas (ej: ...)".
    """
    if not ps:
        return "[]"
    items = sorted(ps)
    if len(items) <= limit:
        return "[" + ", ".join(str(p) for p in items) + "]"
    return f"{len(items)} celdas (ej: " + ", ".join(str(p) for p in items[:limit]) + ", ...)"


def format_percept(per: list[bool]) -> str:
    """Convierte el percepto a texto legible.

    Orden interno del percepto (como lo devuelve `calcular_percepto()`):
        [Brisa, Ronquido, Resplandor, ParedU, ParedD, ParedL, ParedR, Grito]

    Orden mostrado por consola:
        Brisa, Ronquido, Resplandor, Grito,
        Pared_arriba (^), Pared_abajo (v), Pared_izq (<), Pared_dcha (>)
    """
    order = [
        ("Brisa", 0),
        ("Ronquido", 1),
        ("Resplandor", 2),
        ("Grito", 7),
        ("Pared_arriba (^)", 3),
        ("Pared_abajo (v)", 4),
        ("Pared_izq (<)", 5),
        ("Pared_dcha (>)", 6),
    ]
    parts = [f"{name}={int(bool(per[idx]))}" for name, idx in order]
    return "Percepto: [" + ", ".join(parts) + "]"


def print_percept(per: list[bool]) -> None:
    """Imprime el percepto de forma legible."""
    print(format_percept(per))

def unico_de_conjunto(s: set[tuple[int, int]]) -> tuple[int, int] | None:
    """Devuelve el único elemento de un conjunto si existe.
    
    Esta función es útil para saber si una hipótesis está ya determinada con certeza
    (por ejemplo, si solo queda una salida candidata o un único soldado candidato).
    
    Args:
        s: Conjunto de posiciones.
    
    Returns:
        El único elemento de `s` si `len(s) == 1`; en caso contrario, None.
    """
    if len(s) != 1:
        return None
    elem = None
    for x in s:
        elem = x
    return elem


#------------------------------------------------------------
# 3) Mundo real (oculto) y dinámica del juego
#------------------------------------------------------------

def elegir_posiciones_elementos(n: int, inicio: tuple[int, int]) -> tuple[set[tuple[int, int]], tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Elige posiciones aleatorias para los elementos del mundo (parte estática).

    Devuelve:
        - precipicios: conjunto con 3 celdas
        - soldado: una celda
        - salida: una celda
        - kurtz: una celda

    Todas son distintas entre sí y distintas de `inicio`.
    """
    celdas = todas_las_celdas(n)
    disponibles = [p for p in celdas if p != inicio]

    precipicios = set(random.sample(disponibles, 3))
    disponibles = [p for p in disponibles if p not in precipicios]

    soldado = random.choice(disponibles)
    disponibles.remove(soldado)

    salida = random.choice(disponibles)
    disponibles.remove(salida)

    kurtz = random.choice(disponibles)

    return precipicios, soldado, salida, kurtz


def crear_estado_inicial_agente(inicio: tuple[int, int]) -> dict[str, object]:
    """Construye el estado dinámico inicial del agente (sin tocar el mundo)."""
    return {
        "agent": inicio,
        "alive": True,
        "kurtz_found": False,
        "grenade": True,
        "soldier_alive": True,
        "last_scream": False,   # Grito=1 solo el turno posterior a granada efectiva
        "exit_seen": False,     # se marca True tras pisar la salida
    }


def crear_mundo(n: int = 6, inicio: tuple[int, int] = (1, 1), *, start: tuple[int, int] | None = None) -> dict[str, object]:
    """Crea un mundo aleatorio válido (Parte 1) y deja el estado listo para jugar.

    Coloca, en celdas distintas y distintas de inicio:
      - 3 precipicios
      - 1 soldado
      - 1 salida
      - 1 Kurtz

    Además inicializa el estado dinámico del agente.

    Nota:
        La generación es aleatoria “pura” (una única tirada con la semilla fijada en `main`).
        No se añaden restricciones extra alrededor de la casilla inicial.

    Args:
        n: Tamaño del tablero (por defecto 6).
        inicio: Celda inicial (por defecto (1,1)).

    Returns:
        Diccionario con el mundo y estado del agente.
    """
    if n * n < 7:
        raise ValueError(
            "Tablero demasiado pequeño: se necesitan al menos 7 celdas distintas "
            "(inicio + 3 pits + soldado + salida + Kurtz)."
        )

    if start is not None:
        inicio = start

    precipicios, soldado, salida, kurtz = elegir_posiciones_elementos(n, inicio)

    mundo = {
        # estático
        "n": n,
        "start": inicio,
        "pits": precipicios,
        "soldier": soldado,
        "exit": salida,
        "kurtz": kurtz,
    }
    mundo.update(crear_estado_inicial_agente(inicio))
    return mundo


def crear_mundo_inicio_seguro(n: int = 6, inicio: tuple[int, int] = (1, 1)) -> dict[str, object]:
    """Genera un mundo aleatorio evitando un inicio "imposible".

    Repite la generación hasta que NINGUNA celda adyacente a `inicio` sea:
      - un precipicio, ni
      - el soldado (si está vivo).

    Esto no cambia las reglas del enunciado; solo evita casos en los que, desde el
    primer turno, el jugador no tenga ninguna opción razonable.

    Args:
        n: Tamaño del tablero (n x n).
        inicio: Celda inicial.

    Returns:
        Un diccionario `mundo` listo para jugar.
    """
    while True:
        mundo = crear_mundo(n, inicio=inicio)
        vecinos_inicio = set(vecinos_ortogonales(int(mundo["n"]), inicio))

        if (set(mundo["pits"]) & vecinos_inicio) or (mundo["soldier"] in vecinos_inicio):
            continue

        return mundo


def hay_brisa(mundo: dict[str, object], adyacentes: list[tuple[int, int]]) -> bool:
    """True si alguna celda adyacente contiene un precipicio."""
    return any(q in mundo["pits"] for q in adyacentes)


def hay_ronquido(mundo: dict[str, object], adyacentes: list[tuple[int, int]]) -> bool:
    """True si el soldado está vivo y en una celda adyacente."""
    if not bool(mundo["soldier_alive"]):
        return False
    return any(q == mundo["soldier"] for q in adyacentes)


def hay_resplandor(mundo: dict[str, object], posicion: tuple[int, int], adyacentes: list[tuple[int, int]]) -> bool:
    """True si estamos en la salida o si la salida está en una celda adyacente."""
    if posicion == mundo["exit"]:
        return True
    return any(q == mundo["exit"] for q in adyacentes)


def detectar_paredes(posicion: tuple[int, int], n: int) -> tuple[bool, bool, bool, bool]:
    """Devuelve (pared_arriba, pared_abajo, pared_izquierda, pared_derecha)."""
    fila, col = posicion
    pared_arriba = (fila == 1)
    pared_abajo = (fila == n)
    pared_izquierda = (col == 1)
    pared_derecha = (col == n)
    return pared_arriba, pared_abajo, pared_izquierda, pared_derecha


def consumir_grito(mundo: dict[str, object]) -> bool:
    """Lee el grito del turno y lo reinicia (dura solo un percepto)."""
    grito = bool(mundo["last_scream"])
    mundo["last_scream"] = False
    return grito


def calcular_percepto(mundo: dict[str, object]) -> list[bool]:
    """Calcula el percepto del agente en su celda actual.

    Percepto:
      [Brisa, Ronquido, Resplandor, ParedU, ParedD, ParedL, ParedR, Grito]

    Args:
        mundo: Mundo real (incluye posición actual y estado dinámico).
    Returns:
        Lista de 8 booleanos.
    """
    n = int(mundo["n"])
    posicion = mundo["agent"]
    adyacentes = vecinos_ortogonales(n, posicion)

    brisa = hay_brisa(mundo, adyacentes)
    ronquido = hay_ronquido(mundo, adyacentes)
    resplandor = hay_resplandor(mundo, posicion, adyacentes)

    pared_arriba, pared_abajo, pared_izquierda, pared_derecha = detectar_paredes(posicion, n)
    grito = consumir_grito(mundo)

    return [brisa, ronquido, resplandor, pared_arriba, pared_abajo, pared_izquierda, pared_derecha, grito]


def actualizar_kurtz(mundo: dict[str, object]) -> None:
    """Actualiza el estado de Kurtz si el agente entra en su celda (y lo hace 'viajar' tras encontrarlo)."""
    if (not bool(mundo["kurtz_found"])) and (mundo["agent"] == mundo["kurtz"]):
        mundo["kurtz_found"] = True

    # Si ya se encontró, Kurtz viaja contigo (detalle útil para el estado)
    if bool(mundo["kurtz_found"]):
        mundo["kurtz"] = mundo["agent"]


def actualizar_salida_vista(mundo: dict[str, object]) -> None:
    """Marca que la salida ya se ha pisado (si procede)."""
    if mundo["agent"] == mundo["exit"]:
        mundo["exit_seen"] = True


def comprobar_muerte(mundo: dict[str, object]) -> None:
    """Comprueba si el agente muere al entrar en la celda actual (precipicio o soldado vivo)."""
    if mundo["agent"] in mundo["pits"]:
        mundo["alive"] = False
        return

    if bool(mundo["soldier_alive"]) and (mundo["agent"] == mundo["soldier"]):
        mundo["alive"] = False
        return


def accion_mover(mundo: dict[str, object], d: str) -> None:
    """Acción: mover una celda en dirección d.

    Reglas:
    - Si choca con pared: no se mueve.
    - Si entra en pit: muere.
    - Si entra en soldado vivo: muere.
    - Si entra en Kurtz: lo encuentra (y a partir de ahí Kurtz viaja con el agente).
    - Si pisa la salida: exit_seen=True.

    Args:
        mundo: Mundo real (se modifica in-place).
        d: Dirección {"U","D","L","R"}.
    """
    if not bool(mundo["alive"]):
        return

    n = int(mundo["n"])
    siguiente = mover_posicion(mundo["agent"], d)

    if not esta_en_tablero(n, siguiente):
        return

    mundo["agent"] = siguiente

    actualizar_kurtz(mundo)
    actualizar_salida_vista(mundo)
    comprobar_muerte(mundo)


def accion_granada(mundo: dict[str, object], d: str) -> None:
    """Acción: lanzar granada (un solo uso) a una celda adyacente.

    Si mata al soldado, el siguiente percepto incluye Grito=1.

    Args:
        mundo: Mundo real (se modifica in-place).
        d: Dirección objetivo {"U","D","L","R"}.
    """
    if not bool(mundo["alive"]):
        return
    if not bool(mundo["grenade"]):
        return

    mundo["grenade"] = False

    n = int(mundo["n"])
    objetivo = mover_posicion(mundo["agent"], d)

    if not esta_en_tablero(n, objetivo):
        return

    if bool(mundo["soldier_alive"]) and objetivo == mundo["soldier"]:
        mundo["soldier_alive"] = False
        mundo["last_scream"] = True


def accion_salir(mundo: dict[str, object]) -> bool:
    """Acción: salir.

    Victoria si (está en salida) y (Kurtz encontrado).

    Args:
        mundo: Mundo real.
    Returns:
        True si misión completada; False si no.
    """
    if not bool(mundo["alive"]):
        return False
    if mundo["agent"] != mundo["exit"]:
        return False
    return bool(mundo["kurtz_found"])


#------------------------------------------------------------
#------------------------------------------------------------
# 4) Base de conocimiento (KB) e inferencia
#------------------------------------------------------------

def crear_kb(n: int, inicio: tuple[int, int]) -> dict[str, object]:
    """Crea la base de conocimiento (KB) inicial del capitán.

    La KB es el "estado mental" del agente: todo lo que cree/sabe a partir de lo
    observado. Aquí guardamos dos tipos de información:

    1) Observaciones por celda visitada (lo que devuelve `calcular_percepto()`):
       - Brisa (cerca de precipicio)
       - Ronquido (cerca del soldado si está vivo)
       - Resplandor (cerca de la salida o en la propia salida)
       - Grito (turno posterior a una granada efectiva)

    2) Inferencias globales (lo que deducimos al combinar observaciones):
       - `pit_worlds`: asignaciones posibles de EXACTAMENTE 3 precipicios
         consistentes con todas las brisas observadas.
       - `soldier_cand`: celdas donde podría estar el soldado (si está vivo).
       - `exit_cand`: celdas donde podría estar la salida.
       - `soldier_known` / `exit_known`: si los candidatos se reducen a 1 celda,
         guardamos esa celda aquí (sirve para propagar restricciones cruzadas).

    Args:
        n: Tamaño del tablero.
        inicio: Celda inicial (1-indexado), típicamente (1,1).

    Returns:
        Diccionario con la estructura de la KB.
    """
    return {
        "n": n,
        "start": inicio,
        "visited": set(),

        # Observaciones locales (solo definidas en celdas visitadas)
        "breeze_obs": {},  # pos -> bool
        "snore_obs": {},   # pos -> bool
        "glow_obs": {},    # pos -> bool
        "scream_obs": {},  # pos -> bool

        # Estado y candidatos inferidos
        "soldier_alive": True,

        # Si se reduce a 1 candidato, lo guardamos aquí para coherencia entre inferencias.
        "soldier_known": None,
        "exit_known": None,

        "pit_worlds": [],       # lista de sets (cada set es una asignación de 3 pits)
        "soldier_cand": set(),  # candidatos consistentes del soldado
        "exit_cand": set(),     # candidatos consistentes de la salida
    }


def actualizar_kb(
    kb: dict[str, object],
    posicion: tuple[int, int],
    percepto: list[bool],
    soldado_vivo: bool,
) -> None:
    """Actualiza la KB con el percepto observado y recalcula inferencias.

    Esta función se llama una vez por turno, justo después de obtener el percepto
    en la celda actual. Guarda la observación en la KB y luego vuelve a ejecutar
    las rutinas de inferencia (precipicios, soldado y salida).

    Args:
        kb: Base de conocimiento (se modifica in-place).
        posicion: Posición actual del agente (1-indexado).
        percepto: Percepto devuelto por `calcular_percepto()`, con el orden:
            [Brisa, Ronquido, Resplandor, ParedU, ParedD, ParedL, ParedR, Grito]
        soldado_vivo: Estado real del soldado (sirve para saber si siguen aplicando ronquidos).

    Returns:
        None. La KB queda actualizada.
    """
    kb["visited"].add(posicion)
    kb["breeze_obs"][posicion] = bool(percepto[0])
    kb["snore_obs"][posicion] = bool(percepto[1])
    kb["glow_obs"][posicion] = bool(percepto[2])
    kb["scream_obs"][posicion] = bool(percepto[7])
    kb["soldier_alive"] = bool(soldado_vivo)

    inferir_todo(kb)


def inferir_todo(kb: dict[str, object]) -> None:
    """Recalcula todas las inferencias a partir de la KB actual.

    Agrupa en un único punto las tres deducciones principales:
    - precipicios (enumeración de mundos consistentes con brisas),
    - soldado (candidatos consistentes con ronquidos si está vivo),
    - salida (candidatos consistentes con resplandor).

    Nota:
        Hay dependencias cruzadas entre inferencias (por ejemplo, si deducimos con certeza
        la salida o el soldado, esas celdas no pueden ser precipicio). Para que esa coherencia
        se refleje en el mismo turno, iteramos unas pocas veces hasta estabilizar.

    Args:
        kb: Base de conocimiento (se modifica in-place).
    """
    estado_previo = None
    for _ in range(3):
        inferir_precipicios(kb)
        inferir_soldado(kb)
        inferir_salida(kb)

        estado_actual = (
            kb.get("soldier_known"),
            kb.get("exit_known"),
            frozenset(kb.get("soldier_cand", set())),
            frozenset(kb.get("exit_cand", set())),
            len(kb.get("pit_worlds", [])),
        )
        if estado_actual == estado_previo:
            break
        estado_previo = estado_actual


def inferir_precipicios(kb: dict[str, object]) -> None:
    """Infiera posiciones posibles de precipicios enumerando mundos consistentes.

    Modelo (Parte 1):
    - En el tablero hay EXACTAMENTE 3 precipicios.
    - Si en una celda visitada se observa Brisa=0, entonces NINGÚN vecino suyo es precipicio.
    - Si se observa Brisa=1, entonces AL MENOS un vecino suyo es precipicio.

    Estrategia:
    Construimos una lista de celdas candidatas y enumeramos todas las combinaciones
    de 3 celdas (n=6 es pequeño). Nos quedamos con las que satisfacen todas las
    restricciones de brisa. El resultado se guarda en `kb["pit_worlds"]`.

    Coherencia entre inferencias:
        Si ya hemos deducido con certeza la celda del soldado o de la salida,
        esa celda no puede ser un precipicio, así que la excluimos de la enumeración.

    Args:
        kb: Base de conocimiento (se modifica in-place).
    """
    n = int(kb["n"])
    visitadas = set(kb["visited"])

    descartadas = set()
    zonas_con_brisa: list[set[tuple[int, int]]] = []

    for celda, hay_brisa in kb["breeze_obs"].items():
        vecinos = set(vecinos_ortogonales(n, celda))
        if hay_brisa:
            zonas_con_brisa.append(vecinos)
        else:
            descartadas |= vecinos

    celdas_prohibidas = set()
    if kb.get("soldier_known") is not None:
        celdas_prohibidas.add(kb["soldier_known"])
    if kb.get("exit_known") is not None:
        celdas_prohibidas.add(kb["exit_known"])

    candidatas: list[tuple[int, int]] = []
    for celda in todas_las_celdas(n):
        if (celda not in visitadas) and (celda not in descartadas) and (celda not in celdas_prohibidas):
            candidatas.append(celda)

    mundos: list[set[tuple[int, int]]] = []
    m = len(candidatas)

    # Enumeración explícita de combinaciones de 3 (rápido para n=6)
    for i in range(m - 2):
        for j in range(i + 1, m - 1):
            for k in range(j + 1, m):
                precipicios = {candidatas[i], candidatas[j], candidatas[k]}

                ok = True
                # Brisa=1 -> al menos un pit adyacente
                for vecinos in zonas_con_brisa:
                    if len(precipicios & vecinos) == 0:
                        ok = False
                        break
                if not ok:
                    continue

                # Brisa=0 -> ningún pit adyacente
                for celda, hay_brisa in kb["breeze_obs"].items():
                    if not hay_brisa:
                        if len(precipicios & set(vecinos_ortogonales(n, celda))) > 0:
                            ok = False
                            break
                if not ok:
                    continue

                mundos.append(precipicios)

    kb["pit_worlds"] = mundos


def precipicios_posibles(kb: dict[str, object]) -> set[tuple[int, int]]:
    """Devuelve las celdas que podrían contener un precipicio.

    Una celda "puede" ser precipicio si aparece en al menos uno de los mundos
    consistentes enumerados en `kb["pit_worlds"]`.

    Args:
        kb: Base de conocimiento.

    Returns:
        Conjunto de posiciones que son pit posible.
    """
    union = set()
    for mundo in kb["pit_worlds"]:
        union |= set(mundo)
    return union


def precipicios_certeza(kb: dict[str, object]) -> set[tuple[int, int]]:
    """Devuelve las celdas que son precipicio con certeza.

    Una celda es pit seguro si aparece en TODOS los mundos consistentes de
    `kb["pit_worlds"]`. Si todavía no hay mundos consistentes, no se puede asegurar
    nada y se devuelve el conjunto vacío.

    Args:
        kb: Base de conocimiento.

    Returns:
        Conjunto de posiciones que son pit seguro.
    """
    mundos = kb["pit_worlds"]
    if not mundos:
        return set()

    interseccion = None
    for mundo in mundos:
        if interseccion is None:
            interseccion = set(mundo)
        else:
            interseccion &= set(mundo)
    return set() if interseccion is None else interseccion


def es_segura_contra_precipicios(kb: dict[str, object], celda: tuple[int, int]) -> bool:
    """Comprueba si una celda es segura respecto a precipicios.

    Definición usada:
    - `celda` es segura (contra pits) si NO aparece en ningún mundo consistente de pits.
    - Si aún no hay mundos consistentes enumerados, no podemos demostrar seguridad.

    Args:
        kb: Base de conocimiento.
        celda: Posición a evaluar.

    Returns:
        True si `celda` está demostrablemente libre de precipicio; False en caso contrario.
    """
    mundos = kb["pit_worlds"]
    if not mundos:
        return False
    for mundo in mundos:
        if celda in mundo:
            return False
    return True


def inferir_soldado(kb: dict[str, object]) -> None:
    """Deduce candidatos del soldado compatibles con los ronquidos observados.

    Suposición:
    - Si el soldado está vivo, Ronquido=1 en una celda implica que el soldado está
      en algún vecino 4-conexo.
    - Ronquido=0 implica que ninguno de los vecinos es el soldado.

    Además:
    - El soldado no puede estar en una celda ya visitada (si entras ahí, mueres).
    - El soldado no puede estar en un precipicio seguro.

    Args:
        kb: Base de conocimiento (se modifica in-place).
    """
    if not bool(kb["soldier_alive"]):
        kb["soldier_cand"] = set()
        kb["soldier_known"] = None
        return

    n = int(kb["n"])
    visitadas = set(kb["visited"])
    candidatos = set(todas_las_celdas(n))

    # Si el soldado estuviera en una visitada, el agente habría muerto al entrar
    candidatos -= visitadas

    # Si una celda es pit seguro, no puede ser soldado
    candidatos -= precipicios_certeza(kb)

    prohibidas = set()
    zonas_obligatorias: list[set[tuple[int, int]]] = []

    for celda, hay_ronquido in kb["snore_obs"].items():
        vecinos = set(vecinos_ortogonales(n, celda))
        if hay_ronquido:
            zonas_obligatorias.append(vecinos)
        else:
            prohibidas |= vecinos

    candidatos -= prohibidas

    if zonas_obligatorias:
        interseccion = set(zonas_obligatorias[0])
        for zona in zonas_obligatorias[1:]:
            interseccion &= zona
        candidatos &= interseccion

    kb["soldier_cand"] = candidatos
    kb["soldier_known"] = unico_de_conjunto(candidatos)


def inferir_salida(kb: dict[str, object]) -> None:
    """Deduce candidatos de salida consistentes con el resplandor observado.

    Modelo:
    - Resplandor=1 en una celda implica que la salida está en esa celda o en alguno
      de sus vecinos (zona de distancia Manhattan <= 1).
    - Resplandor=0 implica que la salida NO está en esa zona.

    Args:
        kb: Base de conocimiento (se modifica in-place).
    """
    n = int(kb["n"])
    candidatos = set(todas_las_celdas(n))

    # Si una celda es pit seguro, no puede ser salida
    candidatos -= precipicios_certeza(kb)

    for celda, hay_resplandor in kb["glow_obs"].items():
        zona = set(vecinos_ortogonales(n, celda))
        zona.add(celda)
        if hay_resplandor:
            candidatos &= zona
        else:
            candidatos -= zona

    kb["exit_cand"] = candidatos
    kb["exit_known"] = unico_de_conjunto(candidatos)


def hay_resplandor_observado(kb: dict[str, object]) -> bool:
    """Indica si se ha observado alguna vez Resplandor=1.

    Se usa principalmente para decidir si tiene sentido mostrar "E?" en el mapa.
    Mientras no hayamos visto resplandor, enseñar candidatos de salida suele ser
    ruido.

    Args:
        kb: Base de conocimiento.

    Returns:
        True si existe alguna observación con Resplandor=1; False si no.
    """
    for celda in kb["glow_obs"]:
        if bool(kb["glow_obs"][celda]):
            return True
    return False


def es_segura_contra_soldado(kb: dict[str, object], celda: tuple[int, int]) -> bool:
    """Comprueba si una celda es segura respecto al soldado con certeza.

    - Si el soldado ya está muerto, todas las celdas son seguras respecto a él.
    - Si está vivo, una celda es "segura" si NO pertenece al conjunto de candidatos
      consistentes (`kb["soldier_cand"]`).

    Args:
        kb: Base de conocimiento.
        celda: Posición a evaluar.

    Returns:
        True si `celda` está demostrablemente libre de soldado; False en caso contrario.
    """
    if not bool(kb["soldier_alive"]):
        return True
    return celda not in kb["soldier_cand"]


def es_segura(kb: dict[str, object], celda: tuple[int, int]) -> bool:
    """Comprueba si una celda es demostrablemente segura para moverse.

    Criterio:
    - Una celda visitada se considera segura (si hubieras muerto, el episodio habría terminado).
    - Una celda no visitada es segura si es segura respecto a precipicios Y respecto al soldado.

    Args:
        kb: Base de conocimiento.
        celda: Posición a evaluar.

    Returns:
        True si el agente puede entrar con certeza de no morir; False si no.
    """
    if celda in kb["visited"]:
        return True
    return es_segura_contra_precipicios(kb, celda) and es_segura_contra_soldado(kb, celda)


def celdas_seguras(kb: dict[str, object]) -> set[tuple[int, int]]:
    """Devuelve el conjunto de celdas demostrablemente seguras.

    Incluye todas las visitadas y aquellas no visitadas que el razonamiento actual
    marca como seguras (ni precipicio posible ni soldado posible).

    Args:
        kb: Base de conocimiento.

    Returns:
        Conjunto de posiciones seguras.
    """
    n = int(kb["n"])
    seguras = set()
    for celda in todas_las_celdas(n):
        if es_segura(kb, celda):
            seguras.add(celda)
    return seguras
# 5) Visualización del conocimiento
#------------------------------------------------------------

def celdas_frontera(kb: dict[str, object]) -> set[tuple[int, int]]:
    """Calcula la frontera de exploración del agente.
    
    Definición práctica:
    - Frontera = celdas NO visitadas que son vecinas 4-conexas de alguna visitada.
    
    Esto sirve para mostrar en el mapa qué celdas son "alcanzables en un paso"
    desde lo ya explorado, y etiquetarlas con P?/S?/E? cuando proceda.
    
    Args:
        kb: Base de conocimiento.
    
    Returns:
        Conjunto de posiciones que forman la frontera.
    """
    n = int(kb["n"])
    visitadas = kb["visited"]
    frontera = set()
    for v in visitadas:
        for nb in vecinos_ortogonales(n, v):
            if nb not in visitadas:
                frontera.add(nb)
    return frontera


def hay_evidencia_brisa_local(kb: dict[str, object], p: tuple[int, int]) -> bool:
    """True si hay alguna celda visitada con Brisa=1 adyacente a p."""
    n = int(kb["n"])
    for v, b in kb["breeze_obs"].items():
        if b and (p in vecinos_ortogonales(n, v)):
            return True
    return False


def hay_evidencia_ronquido_local(kb: dict[str, object], p: tuple[int, int]) -> bool:
    """True si hay alguna celda visitada con Ronquido=1 adyacente a p."""
    n = int(kb["n"])
    for v, s in kb["snore_obs"].items():
        if s and (p in vecinos_ortogonales(n, v)):
            return True
    return False


def etiqueta_combinada(poss: list[str]) -> str:
    """Construye una etiqueta compacta para una celda de frontera.

    En una misma celda pueden coexistir varias posibilidades (p.ej. "precipicio posible"
    y "salida candidata"). Para que se vea claro, mantenemos el '?' en cada símbolo:

      - Una sola posibilidad :  "P?" / "S?" / "E?"
      - Varias posibilidades :  "P?S?" / "P?E?" / "S?E?" / "P?S?E?"
      - Sin evidencias       :  "?"

    Args:
        poss: Lista de letras en {"P","S","E"}.

    Returns:
        Etiqueta compacta.
    """
    if not poss:
        return "?"
    # Orden estable para que siempre se vea igual
    order = {"P": 0, "S": 1, "E": 2}
    uniq = []
    for x in sorted(set(poss), key=lambda t: order.get(t, 99)):
        if x in ("P", "S", "E"):
            uniq.append(x)
    return "".join([x + "?" for x in uniq]) if uniq else "?"


def formatear_celda(texto: str, ancho_celda: int) -> str:
    """Formatea una etiqueta de celda a ancho fijo y aplica color (si está activado).

    Importante:
        El padding se hace ANTES de aplicar códigos ANSI para no desalinear la tabla.

    Args:
        texto: Etiqueta base (sin padding).
        ancho_celda: Ancho fijo de celda.

    Returns:
        Texto a ancho fijo (posiblemente coloreado).
    """
    texto_base = texto
    if len(texto) > ancho_celda:
        texto = texto[: ancho_celda - 1] + "+"
    texto_relleno = texto.ljust(ancho_celda)
    return colorize_cell(texto_relleno, texto_base)


def etiqueta_capitan(world: dict[str, object], kb: dict[str, object], agent: tuple[int, int]) -> str:
    """Etiqueta del capitán en la celda actual, con 'subíndices' de estímulos."""
    base = "CWK" if bool(world["kurtz_found"]) else "CW"

    b = bool(kb["breeze_obs"].get(agent, False))
    r = bool(kb["snore_obs"].get(agent, False))
    g = bool(kb["glow_obs"].get(agent, False))
    s = bool(kb["scream_obs"].get(agent, False))

    suf = ""
    if b:
        suf += "B"
    if r:
        suf += "R"

    on_exit = bool(world["exit_seen"]) and (agent == world["exit"])
    if g and not on_exit:
        suf += "L"  # Luz/Resplandor (cerca de la salida)
    if on_exit:
        suf += "E"  # Encima de la salida (ya descubierta)

    if s:
        suf += "G"  # Grito

    return base + suf


def accion_a_tecla(act: str) -> str:
    """Convierte una acción interna (U/D/L/R, G?, X) a la tecla WASD / g(...) / e."""
    if act in DIRS:
        return DIR_TO_KEY[act]
    if act.startswith("G") and len(act) == 2 and act[1] in DIRS:
        return f"g({DIR_TO_KEY[act[1]]})"
    if act == "X":
        return "e"
    return act


def plan_a_teclas(plan: list[str]) -> str:
    """Plan como secuencia de teclas (separadas por espacios)."""
    return " ".join([accion_a_tecla(a) for a in plan])


def valor_nodo_traza(method: str, g_cost: dict[tuple, int], state: tuple, goal_h) -> int:
    """Valor mostrado para un nodo en el trazado de búsqueda.

    - BFS/DFS: g (coste acumulado)
    - GBFS: h (heurística)
    - A*: g + h

    Nota:
        El objetivo NO se pasa como coordenada: `goal_h(pos)` devuelve la distancia Manhattan
        al objetivo (heurística).
    """
    pos, _, _, _ = state
    g = g_cost.get(state, 0)
    if method == "gbfs":
        return int(goal_h(pos))
    if method == "astar":
        return g + int(goal_h(pos))
    return g

def formatear_nodos_traza(nodes: list[tuple[tuple[int, int], int]]) -> str:
    """Formatea una lista de nodos como (r,c)(v), ..."""
    if not nodes:
        return "—"
    return ", ".join([f"({p[0]},{p[1]})({v})" for (p, v) in nodes])


def snapshot_frontera_traza(
    method: str,
    frontier: list[tuple],
    open_list: list[tuple[int, int, tuple]],
    closed: set[tuple],
    g_cost: dict[tuple, int],
    goal_h,
    removed_pos: tuple[int, int],
    removed_val: int,
) -> list[tuple[tuple[int, int], int]]:
    """Snapshot de la frontera para el trazado (incluyendo el extraído al principio).

    Nota:
        Para que sea legible, colapsamos estados que estén en la misma celda y mostramos
        solo una entrada por (r,c).
    """
    out: list[tuple[tuple[int, int], int]] = []
    seen: set[tuple[int, int]] = set()

    # Incluimos primero el extraído (removed_pos)
    out.append((removed_pos, removed_val))
    seen.add(removed_pos)

    # Estados restantes en la frontera según el método
    if method in ("bfs", "dfs"):
        rest_states = frontier
    else:
        rest_states = [it[2] for it in sorted(open_list)]

    for st in rest_states:
        p = st[0]
        if p in seen:
            continue
        if st in closed:
            continue
        out.append((p, valor_nodo_traza(method, g_cost, st, goal_h)))
        seen.add(p)

    return out

def reconstruir_acciones_desde_padre(parent: dict[tuple, tuple[tuple, str]], start_state: tuple, end_state: tuple) -> list[str]:
    """Reconstruye lista de acciones desde start_state hasta end_state usando 'parent'."""
    out: list[str] = []
    cur = end_state
    while cur != start_state:
        prev, act = parent[cur]
        out.append(act)
        cur = prev
    out.reverse()
    return out


def mostrar_tablero(world: dict[str, object], kb: dict[str, object], per: list[bool] | None = None) -> None:
    """Imprime el tablero usando la notación del enunciado (mapa de conocimiento).

    Detalles de presentación:
    - El capitán se muestra como "CW" y, en su celda, se añaden letras de estímulo
      (por ejemplo "CWB" o "CWR"). Si coinciden varios estímulos, se concatenan.
    - Las celdas visitadas se marcan con "v" y las seguras no exploradas con "✓".
    - Los peligros deducidos con certeza se muestran como "P!" y "S!".
    - En frontera se muestran posibilidades "P?", "S?", "E?" o combinaciones.

    Nota:
        Este es el mapa de *conocimiento* del agente, no el mapa real oculto.

    Args:
        world: Mundo real (para saber dónde está el agente, si lleva a Kurtz, etc.).
        kb: Base de conocimiento (para saber qué se ha inferido).
    """
    n = int(world["n"])
    agent = world["agent"]
    visitadas = kb["visited"]
    frontera = celdas_frontera(kb)

    precipicios_seguro = precipicios_certeza(kb)
    precipicios_posibles_celdas = precipicios_posibles(kb)

    mostrar_candidatos_salida = hay_resplandor_observado(kb)
    candidatos_salida = kb["exit_cand"]
    candidatos_soldado = kb["soldier_cand"]

    ancho_celda = 6

    print_section("Conocimiento del agente sobre el PALACIO")
    print("Información relevante del mapa:")
    print("  P = precipicio | S = soldado | E = salida")
    print("  CW / CWK : capitán (sin / con el coronel Kurtz)")
    print("  CWB/CWR… : estímulos de la celda actual (B=Brisa, R=Ronquido, L=Resplandor, G=Grito)")
    print("  v        : celdas visitada")
    print("  ✓        : celda segura que todavía no se han explorado")
    print("  *        : celda desconocida")
    print("  E        : salida (solo se marca como tal tras pisarla)")
    print("  E? / E!  : candidata(s) a salida (E! = única candidata)")
    print("  P! / S!  : peligro deducido con certeza")
    print("  P?/S? y combinaciones (P?S?/P?E?/S?E?/P?S?E?): posibilidades en frontera")
    print("")

    # Cabecera columnas
    cabecera = "     " + "".join(formatear_celda(f"{c:>2d}", ancho_celda) for c in range(1, n + 1))
    print(cabecera)
    print("     " + "-" * (ancho_celda * n))

    for r in range(1, n + 1):
        fila = []
        for c in range(1, n + 1):
            p = (r, c)

            # 1) Celda del agente (con subíndices)
            if p == agent:
                fila.append(formatear_celda(etiqueta_capitan(world, kb, agent), ancho_celda))
                continue

            # 2) Salida real pisada: si ya se ha encontrado, se marca de forma persistente
            if bool(world["exit_seen"]) and p == world["exit"]:
                fila.append(formatear_celda("E", ancho_celda))
                continue

            # 3) Visitadas (exploradas)
            if p in visitadas:
                fila.append(formatear_celda("v", ancho_celda))
                continue

            # 4) Peligros deducidos con certeza
            if p in precipicios_seguro:
                fila.append(formatear_celda("P!", ancho_celda))
                continue

            # 5) Candidatos (posibles / únicos) según evidencias locales
            tags: list[str] = []

            if (p in precipicios_posibles_celdas) and hay_evidencia_brisa_local(kb, p):
                tags.append("P?")

            if bool(kb["soldier_alive"]):
                if (len(candidatos_soldado) == 1) and (p in candidatos_soldado):
                    tags.append("S!")
                elif (p in candidatos_soldado) and hay_evidencia_ronquido_local(kb, p):
                    tags.append("S?")

            if (len(candidatos_salida) == 1) and (p in candidatos_salida):
                tags.append("E!")
            elif mostrar_candidatos_salida and (p in candidatos_salida):
                tags.append("E?")

            if tags:
                fila.append(formatear_celda("".join(tags), ancho_celda))
                continue

            # 6) Seguras no exploradas (inferidas, pero aún no visitadas)
            if es_segura(kb, p):
                fila.append(formatear_celda("✓", ancho_celda))
                continue

            # 7) Desconocida total
            fila.append(formatear_celda("*", ancho_celda))

        print(f"{r:>3d} | " + "".join(fila))

    print("")
    imprimir_resumen_kb(world, kb, per)

def imprimir_resumen_kb(world: dict[str, object], kb: dict[str, object], per: list[bool] | None = None) -> None:
    """Imprime un resumen del estado actual y de lo que la KB está manejando.

    Incluye:
    - Estado del agente (posición, vivo/muerto, Kurtz encontrado, granada, soldado vivo).
    - Número de modelos de precipicios consistentes (para medir ambigüedad).
    - Conjuntos de posibles posiciones del soldado y de la salida.

    Args:
        world: Mundo real.
        kb: Base de conocimiento.
    """
    pos = world["agent"]
    vivo = bool(world["alive"])
    kurtz_rescatado = bool(world["kurtz_found"])
    granada_disponible = bool(world["grenade"])
    soldado_vivo = bool(world["soldier_alive"])

    print("Estado del agente:")
    print(f"  Posición: {pos}")
    print(f"  Vivo: {'sí' if vivo else 'no'}")
    print(f"  Kurtz rescatado: {'sí' if kurtz_rescatado else 'no'}")
    print(f"  Granada disponible: {'sí' if granada_disponible else 'no'}")
    print(f"  Soldado vivo: {'sí' if soldado_vivo else 'no'}")

    if bool(world.get("exit_seen")):
        print(f"  Salida descubierta en: {world['exit']}")

    # Perceptos actuales (lo que el capitán "siente" en esta celda)
    if per is not None:
        print("Perceptos:")
        print(f"  Brisa: {'sí' if per[0] else 'no'}")
        print(f"  Ronquido: {'sí' if per[1] else 'no'}")
        print(f"  Resplandor: {'sí' if per[2] else 'no'}")
        print(f"  Grito: {'sí' if per[7] else 'no'}")
        print(f"  Pared arriba (^): {'sí' if per[3] else 'no'}")
        print(f"  Pared abajo (v): {'sí' if per[4] else 'no'}")
        print(f"  Pared izquierda (<): {'sí' if per[5] else 'no'}")
        print(f"  Pared derecha (>): {'sí' if per[6] else 'no'}")

    # Orden pedido: pits -> soldado -> salida
    print(f"Modelos pits consistentes: {len(kb['pit_worlds'])}")

    if bool(kb["soldier_alive"]):
        sc = kb["soldier_cand"]
        extra = f"(Hay {len(sc)} candidatos)"
        print(f"Soldado {extra}: {sorted(sc) if sc else '—'}")
    else:
        print("Soldado: — (muerto)")

    ec = kb["exit_cand"]
    extra_e = f"(Hay {len(ec)} candidatos)"
    print(f"Salida {extra_e}: {sorted(ec) if ec else '—'}")

def recomendar_movimientos(world: dict[str, object], kb: dict[str, object]) -> None:
    """Recomienda movimientos (modo manual).

    - Primero muestra los vecinos adyacentes demostrablemente seguros.
    - Además, lista (si existen) celdas seguras no visitadas según la KB.
    """
    n = int(world["n"])
    pos = world["agent"]

    dir_texto = {"U": "arriba", "D": "abajo", "L": "izquierda", "R": "derecha"}

    # 1) Vecinos seguros adyacentes (recomendación inmediata)
    vecinos_seguros: list[tuple[str, tuple[int, int]]] = []
    for d in ("R", "D", "L", "U"):
        q = mover_posicion(pos, d)
        if esta_en_tablero(n, q) and es_segura(kb, q):
            vecinos_seguros.append((d, q))

    if vecinos_seguros:
        print("Recomendación de movimientos:")
        for d, q in vecinos_seguros:
            print(f"- {dir_texto[d]} (pulse '{DIR_TO_KEY[d]}') -> {q}")
    else:
        print("Recomendación de movimientos: ninguna con certeza")

    # 2) Celdas seguras no visitadas (visión global)
    todas_seguras = celdas_seguras(kb)
    no_visitadas = sorted([p for p in todas_seguras if p not in kb["visited"]])
    if no_visitadas:
        texto = ", ".join(str(p) for p in no_visitadas)
        print("Seguras no visitadas (según KB):", texto)

#------------------------------------------------------------
# 6) Planificación de caminos (sin imports extra)
#------------------------------------------------------------

def vecinos_permitidos(n: int, permitidas: set[tuple[int, int]], celda: tuple[int, int]) -> list[tuple[int, int]]:
    """Vecinos de celda restringidos al conjunto de celdas permitidas.

    Args:
        n: Tamaño del tablero.
        permitidas: Conjunto de celdas por las que está permitido planificar (seguras).
        celda: Celda de la que queremos vecinos.
    Returns:
        Lista de vecinos 4-conexos que además están en 'permitidas'.
    """
    vecinos = []
    for vecino in vecinos_ortogonales(n, celda):
        if vecino in permitidas:
            vecinos.append(vecino)
    return vecinos
def planificar_camino_permitido(
    n: int,
    origen: tuple[int, int],
    destino: tuple[int, int],
    permitidas: set[tuple[int, int]],
    metodo: str,
    objetivo_heuristica: tuple[int, int] | None = None,
) -> list[tuple[int, int]] | None:
    """Planifica un camino origen->destino sobre un conjunto de celdas permitidas.

    Nota:
        Esta es la "frontera" interna del algoritmo de búsqueda (BFS/DFS/GBFS/A*),
        no la frontera global de exploración del mapa.

    Sobre GBFS/A*:
        Si no se proporciona `objetivo_heuristica`, la heurística se toma como 0 para que
        el algoritmo se degrade (GBFS ~ búsqueda no informada; A* ~ Dijkstra con coste uniforme).

    Args:
        n: Tamaño del tablero.
        origen: Origen.
        destino: Destino.
        permitidas: Conjunto de celdas por las que se permite planificar.
        metodo: "bfs" | "dfs" | "gbfs" | "astar".
        objetivo_heuristica: Celda usada para Manhattan (opcional).

    Returns:
        Lista de celdas (incluye origen y destino) o None si no hay camino.
    """
    metodo = metodo.lower()

    if origen not in permitidas:
        return None
    if destino not in permitidas:
        return None

    # --- BFS / DFS ---
    if metodo in ("bfs", "dfs"):
        frontera: list[tuple[int, int]] = [origen]
        en_frontera: set[tuple[int, int]] = {origen}
        explorados: set[tuple[int, int]] = set()
        padre: dict[tuple[int, int], tuple[int, int]] = {}

        while frontera:
            u = frontera.pop(0) if metodo == "bfs" else frontera.pop()
            en_frontera.discard(u)

            if u == destino:
                break

            explorados.add(u)
            for v in vecinos_permitidos(n, permitidas, u):
                if (v not in explorados) and (v not in en_frontera):
                    padre[v] = u
                    frontera.append(v)
                    en_frontera.add(v)

        return reconstruir_camino(padre, origen, destino)

    # --- GBFS / A* (con monticulo) ---
    if metodo in ("gbfs", "astar"):
        hg = objetivo_heuristica
        desempate = 0

        # monticulo: (prio, desempate, g, node)  -- en gbfs prio=h; en astar prio=g+h
        monticulo: list[tuple[int, int, int, tuple[int, int]]] = []
        padre: dict[tuple[int, int], tuple[int, int]] = {}
        mejor_g: dict[tuple[int, int], int] = {origen: 0}
        cerrados: set[tuple[int, int]] = set()

        h0 = distancia_manhattan(origen, hg) if hg is not None else 0
        prio0 = h0 if metodo == "gbfs" else (0 + h0)
        heap_insertar(monticulo, (prio0, desempate, 0, origen))

        while monticulo:
            _, _, g, u = heap_extraer(monticulo)

            if u in cerrados:
                continue
            cerrados.add(u)

            if u == destino:
                break

            gu = mejor_g[u]
            for v in vecinos_permitidos(n, permitidas, u):
                if v in cerrados:
                    continue
                gv = gu + 1
                if gv < mejor_g.get(v, 10**9):
                    mejor_g[v] = gv
                    padre[v] = u
                    desempate += 1
                    hv = distancia_manhattan(v, hg) if hg is not None else 0
                    prio_v = hv if metodo == "gbfs" else (gv + hv)
                    heap_insertar(monticulo, (prio_v, desempate, gv, v))

        return reconstruir_camino(padre, origen, destino)

    raise ValueError("Método no soportado: " + str(metodo))



def indice_min_primer_componente(lst: list[tuple]) -> int:
    """Índice del elemento con menor primer componente (t[0]).

    Nota:
        Se implementa a mano para evitar imports extra (heapq, etc.).

    Args:
        lst: Lista de tuplas comparables por el primer componente.
    Returns:
        Índice i tal que lst[i][0] es mínimo.
    """
    mejor_i = 0
    for i in range(1, len(lst)):
        if lst[i][0] < lst[mejor_i][0]:
            mejor_i = i
    return mejor_i



#------------------------------------------------------------
# Mini-heap (cola de prioridad) sin imports
#------------------------------------------------------------
# Usamos estas funciones para GBFS/A* sin depender de heapq.
# El heap almacena tuplas comparables, por ejemplo (f, tie, state).
# - f  : prioridad principal
# - tie: contador creciente para desempates estables

def heap_insertar(monticulo: list[tuple], elemento: tuple) -> None:
    """Inserta `elemento` en un min-monticulo representado como lista."""
    monticulo.append(elemento)
    i = len(monticulo) - 1
    # sift-up
    while i > 0:
        padre_idx = (i - 1) // 2
        if monticulo[padre_idx] <= monticulo[i]:
            break
        monticulo[padre_idx], monticulo[i] = monticulo[i], monticulo[padre_idx]
        i = padre_idx


def heap_extraer(monticulo: list[tuple]) -> tuple:
    """Extrae y devuelve el mínimo de un min-monticulo (monticulo no vacío)."""
    raiz = monticulo[0]
    ultimo = monticulo.pop()
    if monticulo:
        monticulo[0] = ultimo
        # sift-down
        i = 0
        n = len(monticulo)
        while True:
            izq = 2 * i + 1
            der = izq + 1
            if izq >= n:
                break
            j = izq
            if der < n and monticulo[der] < monticulo[izq]:
                j = der
            if monticulo[i] <= monticulo[j]:
                break
            monticulo[i], monticulo[j] = monticulo[j], monticulo[i]
            i = j
    return raiz

def reconstruir_camino(padre: dict[tuple[int, int], tuple[int, int]], origen: tuple[int, int], destino: tuple[int, int]) -> list[tuple[int, int]] | None:
    """Reconstruye un camino desde `origen` hasta `destino` usando el diccionario `padre`.
    
    Convención:
    - `padre[v] = u` indica que llegamos a `v` desde `u`.
    - Si `destino` no tiene padre (y no es origen), no existe camino.
    
    Args:
        padre: Diccionario de predecesores.
        origen: Nodo inicial.
        destino: Nodo objetivo.
    
    Returns:
        Lista de nodos [origen, ..., destino] si se puede reconstruir; None si no.
    """
    if destino == origen:
        return [origen]
    if destino not in padre:
        return None

    camino = [destino]
    actual = destino
    while actual != origen:
        actual = padre[actual]
        camino.append(actual)
    camino.reverse()
    return camino


def planificar_camino(
    kb: dict[str, object],
    origen: tuple[int, int],
    destino: tuple[int, int],
    metodo: str,
    objetivo_heuristica: tuple[int, int] | None = None,
) -> list[tuple[int, int]] | None:
    """Planifica un camino `origen -> destino` restringido a celdas seguras.

    Envoltorio sobre `planificar_camino_permitido(...)` usando como conjunto permitido el
    conjunto de celdas demostrablemente seguras según la KB.

    Args:
        kb: Base de conocimiento.
        origen: Origen.
        destino: Destino.
        metodo: "bfs" | "dfs" | "gbfs" | "astar".
        objetivo_heuristica: Celda usada para Manhattan (opcional).

    Returns:
        Lista de celdas (incluye origen y destino) o None si no hay camino seguro.
    """
    n = int(kb["n"])
    permitidas = celdas_seguras(kb)
    if destino not in permitidas:
        return None
    return planificar_camino_permitido(n, origen, destino, permitidas, metodo, objetivo_heuristica=objetivo_heuristica)


def camino_a_acciones(camino: list[tuple[int, int]]) -> list[str]:
    """Convierte un camino de celdas en una secuencia de acciones U/D/L/R.

    Args:
        camino: Lista [p0,p1,...] con celdas consecutivas (movimientos ortogonales).
    Returns:
        Lista de direcciones ["U","R",...] (vacía si camino tiene <2 celdas).
    """
    if not camino or len(camino) < 2:
        return []

    acciones = []
    for a, b in zip(camino, camino[1:]):
        dr = b[0] - a[0]
        dc = b[1] - a[1]
        for d in DIRS:
            x, y = DIRS[d]
            if (dr, dc) == (x, y):
                acciones.append(d)
                break
    return acciones


def contar_vecinos_no_visitados(kb: dict[str, object], p: tuple[int, int]) -> int:
    """Cuenta vecinos no visitados (heurística para desempatar al explorar).

    Idea:
        Si dos objetivos están a la misma distancia, preferimos el que "abre" más posibilidades.

    Args:
        kb: Base de conocimiento.
        p: Celda candidata.
    Returns:
        Número de vecinos 4-conexos de p que aún no se han visitado.
    """
    n = int(kb["n"])
    visitadas = kb["visited"]
    contador = 0
    for vecino in vecinos_ortogonales(n, p):
        if vecino not in visitadas:
            contador += 1
    return contador


def elegir_objetivo_exploracion(kb: dict[str, object], actual: tuple[int, int]) -> tuple[int, int] | None:
    """Elige una celda segura no visitada para explorar.

    Criterio:
        1) Distancia REAL (BFS) dentro del subgrafo de celdas seguras alcanzables.
        2) Desempate: más vecinos no visitados (abre más frontera).

    Args:
        kb: Base de conocimiento.
        actual: Posición actual del agente.
    Returns:
        Celda objetivo o None si no quedan seguras no visitadas alcanzables.
    """
    seguras = celdas_seguras(kb)
    no_visitadas = [p for p in seguras if p not in kb["visited"]]
    if not no_visitadas:
        return None

    n = int(kb["n"])

    distancia = {actual: 0}
    cola = [actual]
    idx_cola = 0

    while idx_cola < len(cola):
        u = cola[idx_cola]
        idx_cola += 1
        for v in vecinos_ortogonales(n, u):
            if (v in seguras) and (v not in distancia):
                distancia[v] = distancia[u] + 1
                cola.append(v)

    mejor = None
    mejor_clave = None

    for p in no_visitadas:
        if p not in distancia:
            continue
        clave = (distancia[p], -contar_vecinos_no_visitados(kb, p), p[0], p[1])
        if (mejor is None) or (clave < mejor_clave):
            mejor = p
            mejor_clave = clave

    return mejor



def elegir_objetivo_salida(kb: dict[str, object], actual: tuple[int, int]) -> tuple[int, int] | None:
    """Elige un objetivo razonable para buscar la salida usando solo la KB.

    Prioridad:
      1) `exit_known` si existe y es segura.
      2) La candidata de salida segura más cercana (distancia BFS dentro de seguras).

    Devuelve None si no hay ninguna candidata segura alcanzable.
    """
    n = int(kb["n"])
    seguras = celdas_seguras(kb)

    salida_cierta = kb.get("exit_known")
    if (salida_cierta is not None) and (salida_cierta in seguras):
        return salida_cierta

    candidatas = [p for p in kb["exit_cand"] if p in seguras]
    if not candidatas:
        return None

    distancia = {actual: 0}
    cola = [actual]
    idx_cola = 0
    while idx_cola < len(cola):
        u = cola[idx_cola]
        idx_cola += 1
        for v in vecinos_ortogonales(n, u):
            if (v in seguras) and (v not in distancia):
                distancia[v] = distancia[u] + 1
                cola.append(v)

    mejor = None
    mejor_clave = None
    for p in candidatas:
        if p not in distancia:
            continue
        clave = (distancia[p], p[0], p[1])
        if (mejor is None) or (clave < mejor_clave):
            mejor = p
            mejor_clave = clave
    return mejor



def intentar_lanzar_granada(world: dict[str, object], kb: dict[str, object]) -> str | None:
    """Decide si conviene lanzar la granada (si es una acción segura).

    Si el soldado está deducido con certeza (`soldier_known`) y es adyacente,
    se lanza la granada en su dirección.

    Returns:
        Una cadena representando la acción ("gw"/"ga"/"gs"/"gd") si se lanzó, o None.
    """
    if (not bool(world["grenade"])) or (not bool(world["soldier_alive"])):
        return None

    posicion_soldado = kb.get("soldier_known")
    if posicion_soldado is None:
        return None

    posicion_agente = world["agent"]
    dr = posicion_soldado[0] - posicion_agente[0]
    dc = posicion_soldado[1] - posicion_agente[1]

    for d in DIRS:
        x, y = DIRS[d]
        if (dr, dc) == (x, y):
            accion_granada(world, d)
            return "g" + accion_a_tecla(d)

    return None


def instantanea_kb(kb: dict[str, object]) -> tuple:
    """Devuelve una 'foto' inmutable de la KB para poder usarla dentro de un estado.

    Guardamos lo mínimo que define el conocimiento acumulado:
      - visited
      - observaciones (brisa/ronquido/resplandor/grito)

    Nota: los candidatos (pit_worlds / soldier_cand / exit_cand) NO se guardan,
    porque se recalculan al reconstruir la KB con `inferir_todo()`.

    Args:
        kb: KB actual.

    Returns:
        Tupla inmutable con (visited, breeze_obs, snore_obs, glow_obs, scream_obs).
    """
    visitadas_t = tuple(sorted(kb["visited"]))
    brisa_t = tuple(sorted(kb["breeze_obs"].items()))
    ronquido_t = tuple(sorted(kb["snore_obs"].items()))
    resplandor_t = tuple(sorted(kb["glow_obs"].items()))
    grito_t = tuple(sorted(kb["scream_obs"].items()))
    return (visitadas_t, brisa_t, ronquido_t, resplandor_t, grito_t)


def kb_desde_instantanea(n: int, start: tuple[int, int], instantanea: tuple, soldado_vivo: bool) -> dict[str, object]:
    """Reconstruye una KB completa a partir de un snapshot.

    Args:
        n: Tamaño del tablero.
        start: Celda inicial (1-indexado).
        instantanea: Snapshot devuelto por `_kb_snapshot`.
        soldado_vivo: Estado del soldado en este estado de planificación.

    Returns:
        KB reconstruida y con inferencias recalculadas.
    """
    visitadas_t, brisa_t, ronquido_t, resplandor_t, grito_t = instantanea
    kb = crear_kb(n, start)
    kb["visited"] = set(visitadas_t)
    kb["breeze_obs"] = dict(brisa_t)
    kb["snore_obs"] = dict(ronquido_t)
    kb["glow_obs"] = dict(resplandor_t)
    kb["scream_obs"] = dict(grito_t)
    kb["soldier_alive"] = bool(soldado_vivo)

    inferir_todo(kb)
    return kb


def percepto_simulado(*_args, **_kwargs) -> list[bool]:
    """Percepto simulado (DEPRECADO).

    En una versión anterior se simulaban perceptos durante la planificación consultando el
    mundo real (mapa oculto). Eso NO está permitido: el agente solo puede usar perceptos
    cuando realmente está en la celda.

    Esta función se deja como "stub" para evitar usos accidentales en el planificador.
    """
    return [False, False, False, False, False, False, False, False]

def clave_estado(
    posicion: tuple[int, int],
    granada: bool,
    soldado_vivo: bool,
    instantanea: tuple,
) -> tuple:
    """Crea una clave de estado hasheable para el planificador."""
    return (posicion, bool(granada), bool(soldado_vivo), instantanea)


def heuristica(posicion: tuple[int, int], goal_h, metodo: str) -> int:
    """Heurística para GBFS/A*: distancia Manhattan al objetivo de la fase.

    El objetivo NO se pasa como coordenada: se usa una función `goal_h(posicion)` que devuelve
    esa distancia (heurística).
    """
    if metodo in ("gbfs", "astar"):
        return int(goal_h(posicion))
    return 0

def planificar_fase(
    world: dict[str, object],
    start_state: tuple,
    objetivo_h,
    metodo: str,
    trazar: bool = False,
    nombre_fase: str = "",
) -> tuple[list[str] | None, tuple | None]:
    """Planifica (sin ejecutar) una fase: ir desde `start_state` hasta el objetivo.

    Estado de planificación = (posicion, granada, soldado_vivo, instantanea_kb)

    Regla importante:
      Solo se generan movimientos a celdas adyacentes que la KB marca como seguras.

    Nota sobre el objetivo (sin mapa oculto):
      - NO se pasa la coordenada del objetivo.
      - `goal_h(posicion)` define la heurística (por ejemplo, distancia Manhattan al objetivo elegido).
      - El objetivo se considera alcanzado cuando `goal_h(posicion) == 0`.

    Args:
        world: Mundo real (solo se usa para n y la celda inicial).
        start_state: Estado inicial del planificador.
        goal_h: Función que devuelve la distancia Manhattan al objetivo desde `posicion`.
        metodo: "bfs" | "dfs" | "gbfs" | "astar"
        trazar: Si True, imprime el proceso de búsqueda al extraer de la frontera.
        nombre_fase: Texto para cabecera de la fase.

    Returns:
        (lista_de_acciones, estado_final) o (None, None) si no hay plan.
    """
    n = int(world["n"])
    inicio = world["start"]
    metodo = metodo.lower()

    # Alias para mantener compatibilidad interna
    goal_h = objetivo_h


    padre: dict[tuple, tuple[tuple, str]] = {}
    coste_g: dict[tuple, int] = {start_state: 0}
    cerrados: set[tuple] = set()

    pos_exploradas: set[tuple[int, int]] = set()
    pos_frontera: set[tuple[int, int]] = set()

    # Frontera según el método
    frontera: list[tuple] = []                    # BFS/DFS
    lista_abierta: list[tuple[int, int, tuple]] = []  # GBFS/A*: heap (f, desempate, state)
    desempate = 0

    # Insertar estado inicial
    pos_frontera.add(start_state[0])
    if metodo in ("bfs", "dfs"):
        frontera.append(start_state)
    else:
        h0 = heuristica(start_state[0], goal_h, metodo)
        f0 = h0  # en gbfs es h; en astar será g+h (g=0 aquí)
        if metodo == "astar":
            f0 = 0 + h0
        desempate += 1
        heap_insertar(lista_abierta, (f0, desempate, start_state))

    if trazar and nombre_fase:
        print(f"\n[Plan:{nombre_fase}]")

    if trazar:
        if metodo == "gbfs":
            print("Valor: h = Manhattan al objetivo")
        elif metodo == "astar":
            print("Valor: f = g + h (coste + heurística)")
        else:
            print("Valor: g = profundidad (coste acumulado)")
        print("Step | Frontier | Removed | Explored")
        print()

    paso = 0
    orden_exploradas: list[tuple[tuple[int, int], int]] = []
    exploradas_vistas: set[tuple[int, int]] = set()

    while True:
        # Pop siguiente
        if metodo == "bfs":
            if not frontera:
                return None, None
            s = frontera.pop(0)
        elif metodo == "dfs":
            if not frontera:
                return None, None
            s = frontera.pop()
        else:
            if not lista_abierta:
                return None, None
            _, _, s = heap_extraer(lista_abierta)

        if s in cerrados:
            continue

        posicion, granada, soldado_vivo, instantanea = s

        pos_frontera.discard(posicion)
        pos_exploradas.add(posicion)

        valor_extraido = valor_nodo_traza(metodo, coste_g, s, goal_h)

        if trazar:
            elementos_frontera = snapshot_frontera_traza(
                metodo, frontera, lista_abierta, cerrados, coste_g, goal_h, posicion, valor_extraido
            )
            if posicion not in exploradas_vistas:
                exploradas_vistas.add(posicion)
                orden_exploradas.append((posicion, valor_extraido))
            print(
                f"{paso:>4d} | {formatear_nodos_traza(elementos_frontera)} | "
                f"{formatear_nodos_traza([(posicion, valor_extraido)])} | {formatear_nodos_traza(orden_exploradas)}"
            )
            paso += 1

        # ¿Objetivo alcanzado? (h==0)
        if int(goal_h(posicion)) == 0:
            return reconstruir_acciones_desde_padre(padre, start_state, s), s

        cerrados.add(s)

        kb_actual = kb_desde_instantanea(n, inicio, instantanea, soldado_vivo=soldado_vivo)

        estado_granada = None  # (state, kb, instantanea, soldado_vivo) si decidimos lanzar granada aquí

        # 1) Acción GRANADA (solo si se ha deducido soldado con certeza y es adyacente)
        if granada and soldado_vivo:
            sc = kb_actual["soldier_cand"]
            if len(sc) == 1:
                s_cell = unico_de_conjunto(sc)
                if (s_cell is not None) and (distancia_manhattan(posicion, s_cell) == 1):
                    # Dirección hacia ese candidato (para reconstruir la acción G<dir>)
                    dr = s_cell[0] - posicion[0]
                    dc = s_cell[1] - posicion[1]
                    d = None
                    for dd, (x, y) in DIRS.items():
                        if (x, y) == (dr, dc):
                            d = dd
                            break

                    if d is not None:
                        # En planificación NO consultamos el mundo oculto.
                        # Si la KB ha deducido un único candidato, el disparo se modela como
                        # suficiente para "neutralizar" al soldado en el modelo del agente.
                        soldier_alive2 = False

                        snap2 = instantanea  # no obtenemos nuevas observaciones por lanzar granada
                        kb2 = kb_desde_instantanea(n, inicio, snap2, soldado_vivo=soldier_alive2)
                        estado2 = clave_estado(posicion, False, soldier_alive2, snap2)

                        if (estado2 not in padre) and (estado2 not in cerrados):
                            padre[estado2] = (s, f"G{d}")
                            coste_g[estado2] = coste_g.get(s, 0) + 1
                            estado_granada = (estado2, kb2, snap2, soldier_alive2)

        # 2) Movimientos a vecinos seguros (orden determinista)
        ramas: list[tuple[tuple, dict[str, object], tuple, bool, bool]] = [
            (s, kb_actual, instantanea, granada, soldado_vivo)
        ]
        if estado_granada is not None:
            estado_g, kb_g, snap_g, soldier_alive_g = estado_granada
            ramas.append((estado_g, kb_g, snap_g, False, soldier_alive_g))

        for st_base, kb_base, snap_base, grenade_base, soldier_alive_base in ramas:
            pos_base = st_base[0]
            g_base = coste_g.get(st_base, coste_g.get(s, 0))

            for d in FRONTIER_DIR_ORDER:
                nxt = mover_posicion(pos_base, d)
                if not esta_en_tablero(n, nxt):
                    continue

                # Solo movemos a celdas que la KB marca como seguras.
                if not es_segura(kb_base, nxt):
                    continue

                # En planificación NO comprobamos pits/soldado del mundo real ni simulamos perceptos.
                snap2 = snap_base
                estado2 = clave_estado(nxt, grenade_base, soldier_alive_base, snap2)

                # Evitamos insertar duplicados: una vez descubierto un estado, no lo reinsertamos
                if estado2 in padre or estado2 in cerrados:
                    continue

                padre[estado2] = (st_base, d)
                coste_g[estado2] = g_base + 1

                # Push según el método
                pos_frontera.add(nxt)
                if metodo in ("bfs", "dfs"):
                    frontera.append(estado2)
                else:
                    g = coste_g[estado2]
                    h = heuristica(nxt, goal_h, metodo)
                    f = h if metodo == "gbfs" else (g + h)
                    desempate += 1
                    heap_insertar(lista_abierta, (f, desempate, estado2))

def pedir_opcion(pregunta: str, opciones: list[str]) -> str:
    """Solicita por consola una opción dentro de un conjunto permitido.
    
    La comparación se hace en minúsculas para que el usuario pueda escribir
    "Manual"/"manual" sin problemas.
    
    Args:
        pregunta: Texto que se muestra al pedir la opción.
        opciones: Lista de opciones válidas (se devuelven tal cual).
    
    Returns:
        La opción elegida (exactamente una de `opciones`).
    """
    opciones_min = [c.lower() for c in opciones]
    while True:
        entrada = input(pregunta).strip().lower()
        if entrada in opciones_min:
            return opciones[opciones_min.index(entrada)]
        print("Opciones válidas: " + ", ".join(opciones))


def pedir_si_no(pregunta: str, por_defecto: bool = False) -> bool:
    """Pregunta por consola una respuesta sí/no.
    
    Admite entradas comunes: s/si/sí/y/yes y n/no.
    Si el usuario pulsa ENTER, se usa el valor por defecto.
    
    Args:
        pregunta: Texto a mostrar.
        por_defecto: Valor a devolver si el usuario pulsa ENTER.
    
    Returns:
        True para sí; False para no.
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


def pedir_semilla() -> int | None:
    """Pide una semilla opcional para reproducir el mismo mapa.

    - ENTER  -> None (mapa aleatorio)
    - Entero -> se devolverá el entero (y luego se llamará a random.seed)

    La idea es evitar casos raros: si el usuario escribe algo inválido, se vuelve
    a pedir la semilla.

    Returns:
        Entero con la semilla, o None si se desea aleatoriedad.
    """
    while True:
        entrada = input("Semilla (ENTER = aleatoria; escribe un entero para repetir el mismo tablero): ").strip()
        if entrada == "":
            return None
        try:
            return int(entrada)
        except ValueError:
            print("Semilla inválida: introduce un entero o pulsa ENTER.")


def ejecutar_manual(world: dict[str, object], kb: dict[str, object]) -> None:
    """Ejecuta el juego en modo manual (control por teclado).
    
    En cada turno:
    1) Se calcula el percepto real en la celda actual.
    2) Se actualiza la KB y se recomputan inferencias.
    3) Se imprime el mapa de conocimiento y el percepto.
    4) El usuario elige una acción: mover, lanzar granada o intentar salir.
    
    Args:
        world: Mundo real (se modifica in-place).
        kb: Base de conocimiento (se modifica in-place).
    """
    print_section("Modo MANUAL")
    print("Funcionamiento del tablero: ")
    print("- Para realizar movimientos: w=arriba, a=izquierda, s=abajo, d=derecha")
    print("- e para intentar salir (solo funciona si estás en la salida y ya llevas a Kurtz)")
    print("- t para terminar la partida (abandona la misión)")
    while True:
        if not bool(world["alive"]):
            mostrar_tablero(world, kb)
            print("\nHas muerto. Fin.")
            return

        percepto = calcular_percepto(world)
        actualizar_kb(kb, world["agent"], percepto, bool(world["soldier_alive"]))

        mostrar_tablero(world, kb, percepto)
        recomendar_movimientos(world, kb)

        comando = input("\nComando (w/a/s/d mover, g granada, e salir, t terminar)> ").strip().lower()

        if comando == "t":
            print("Partida terminada por el usuario.")
            return

        if comando == "e":
            if accion_salir(world):
                mostrar_tablero(world, kb)
                print("\nMisión completada. Has salido con Kurtz.")
                return
            print("No estás en la salida (o aún no has encontrado a Kurtz).")
            continue

        if comando == "g":
            if not bool(world["grenade"]):
                print("No te queda granada.")
                continue
            tecla_dir = input("Dirección granada (w=arriba, a=izq, s=abajo, d=dcha)> ").strip().lower()
            if tecla_dir not in KEY_TO_DIR:
                print("Dirección inválida.")
                continue
            accion_granada(world, KEY_TO_DIR[tecla_dir])
            continue

        if comando in KEY_TO_DIR:
            accion_mover(world, KEY_TO_DIR[comando])
            continue

        print("Comando no reconocido.")


def imprimir_resumen_auto(acciones_ejecutadas: list[str], posiciones_recorridas: list[tuple[int, int]]) -> None:
    """Imprime un resumen compacto de la trayectoria real del modo automático."""
    print()
    if acciones_ejecutadas:
        print("[Resumen Auto] Acciones ejecutadas:", " ".join(acciones_ejecutadas))
    else:
        print("[Resumen Auto] Acciones ejecutadas: (ninguna)")
    print("[Resumen Auto] Trayectoria (posiciones):", " -> ".join(str(p) for p in posiciones_recorridas))


def _percepto_en_posicion(mundo: dict[str, object], pos: tuple[int, int]) -> list[bool]:
    """Percepto en una posición arbitraria SIN modificar el mundo.

    Se usa exclusivamente durante la planificación del modo automático para
    "consultar" perceptos de nodos en frontera/explorados sin mover al agente real.

    Importante:
      - No se consume `last_scream` (en planificación no se modela el grito temporal).
      - No altera ninguna variable del mundo.
    """
    n = int(mundo["n"])
    ady = vecinos_ortogonales(n, pos)

    brisa = any(q in mundo["pits"] for q in ady)

    # En planificación, el ronquido refleja el estado actual del mundo (soldado vivo o no).
    # La planificación puede suponer el uso de granada, pero el percepto consultado aquí
    # es "oracular" y no depende del orden temporal del plan.
    ronquido = False
    if bool(mundo["soldier_alive"]):
        ronquido = any(q == mundo["soldier"] for q in ady)

    resplandor = (pos == mundo["exit"]) or any(q == mundo["exit"] for q in ady)

    pared_u, pared_d, pared_l, pared_r = detectar_paredes(pos, n)
    grito = False

    return [brisa, ronquido, resplandor, pared_u, pared_d, pared_l, pared_r, grito]


def _observar_si_no_visto(mundo: dict[str, object], kb_plan: dict[str, object], pos: tuple[int, int]) -> None:
    """Añade el percepto de `pos` a la KB de planificación si aún no estaba observado."""
    if pos in kb_plan["visited"]:
        return
    per = _percepto_en_posicion(mundo, pos)
    # En planificación mantenemos la inferencia del soldado activa (soldado_vivo=True)
    # y tratamos el estado del soldado como parte del estado de búsqueda.
    actualizar_kb(kb_plan, pos, per, soldado_vivo=True)


def _es_muerte_segura(kb_plan: dict[str, object], pos: tuple[int, int]) -> bool:
    """True si la KB demuestra que `pos` es mortal con certeza (pit seguro o soldado seguro)."""
    if pos in precipicios_certeza(kb_plan):
        return True
    if bool(kb_plan.get("soldier_alive", True)):
        s = kb_plan.get("soldier_known")
        if (s is not None) and (s == pos):
            return True
    return False


def _es_segura_en_estado(kb_plan: dict[str, object], pos: tuple[int, int], soldado_vivo_estado: bool) -> bool:
    """Seguridad para entrar en `pos` considerando (posiblemente) que el soldado ya está muerto."""
    if pos in kb_plan["visited"]:
        return True

    # Seguridad contra precipicios (independiente del estado del soldado)
    if not es_segura_contra_precipicios(kb_plan, pos):
        return False

    # Si el soldado está muerto en este estado, ya no restringe el movimiento.
    if not bool(soldado_vivo_estado):
        return True

    return es_segura_contra_soldado(kb_plan, pos)


def _direccion_entre(a: tuple[int, int], b: tuple[int, int]) -> str | None:
    """Devuelve la dirección U/D/L/R que lleva de a->b si son adyacentes, si no None."""
    dr = b[0] - a[0]
    dc = b[1] - a[1]
    for d, (x, y) in DIRS.items():
        if (dr, dc) == (x, y):
            return d
    return None


def _reconstruir_plan(padre: dict[tuple, tuple[tuple, str]], inicio: tuple, fin: tuple) -> list[str]:
    """Reconstruye el plan (lista de acciones) desde `inicio` hasta `fin`."""
    acciones: list[str] = []
    s = fin
    while s != inicio:
        prev, act = padre[s]
        acciones.append(act)
        s = prev
    acciones.reverse()
    return acciones


def _candidatos_riesgo(kb_plan: dict[str, object], forzadas: set[tuple[int, int]]) -> list[tuple[int, int]]:
    """Celdas de frontera con etiqueta '?' (inciertas), excluyendo las mortalmente seguras."""
    cand: list[tuple[int, int]] = []
    for p in sorted(celdas_frontera(kb_plan)):
        if p in kb_plan["visited"]:
            continue
        if p in forzadas:
            continue
        if es_segura(kb_plan, p):
            continue
        if _es_muerte_segura(kb_plan, p):
            continue
        cand.append(p)
    return cand


def _elegir_riesgo(cands: list[tuple[int, int]], goal: tuple[int, int]) -> tuple[int, int]:
    """Elige candidato de riesgo con desempate determinista: menor h, luego (fila,col)."""
    mejor = None
    mejor_clave = None
    for p in cands:
        clave = (distancia_manhattan(p, goal), p[0], p[1])
        if (mejor is None) or (clave < mejor_clave):
            mejor = p
            mejor_clave = clave
    return mejor  # type: ignore[return-value]


def _buscar_ruta(
    mundo: dict[str, object],
    kb_plan: dict[str, object],
    estado_inicio: tuple[tuple[int, int], bool, bool],
    goal: tuple[int, int],
    metodo: str,
    forzadas: set[tuple[int, int]],
    trazar: bool = False,
    nombre_fase: str = "",
) -> tuple[list[str] | None, tuple[tuple[int, int], bool, bool] | None]:
    """Búsqueda sobre estados (pos, granada, soldado_vivo) usando KB que se va enriqueciendo.

    Durante la búsqueda:
      - Se "observa" (se consulta percepto) de nodos al entrar en frontera y al extraerlos.
      - Solo se generan movimientos a celdas seguras o a celdas forzadas (riesgo aceptado).
      - Se modela la granada como acción G<dir> cuando el soldado está deducido con certeza y es adyacente.
    """
    metodo = metodo.lower()
    goal_h = lambda p, obj=goal: distancia_manhattan(p, obj)

    inicio_pos, inicio_granada, inicio_soldado = estado_inicio

    # Asegurar percepto del inicio
    _observar_si_no_visto(mundo, kb_plan, inicio_pos)

    padre: dict[tuple, tuple[tuple, str]] = {}
    g_cost: dict[tuple, int] = {estado_inicio: 0}
    cerrados: set[tuple] = set()

    def _valor(st: tuple) -> int:
        """Valor de trazado compatible con estados (pos, granada, soldado_vivo)."""
        g = g_cost.get(st, 0)
        h = int(goal_h(st[0]))
        if metodo == "gbfs":
            return h
        if metodo == "astar":
            return g + h
        return g

    if trazar and nombre_fase:
        print(f"\n[Plan:{nombre_fase}] método={metodo}")
        print("Step | Frontier | Removed | Explored")
        print()

    paso = 0
    exploradas_orden: list[tuple[tuple[int, int], int]] = []
    exploradas_vistas: set[tuple[int, int]] = set()

    if metodo in ("bfs", "dfs"):
        frontera: list[tuple] = [estado_inicio]
        idx = 0
        while True:
            if metodo == "bfs":
                if idx >= len(frontera):
                    break
                s = frontera[idx]
                idx += 1
            else:
                if not frontera:
                    break
                s = frontera.pop()

            if s in cerrados:
                continue

            pos, tiene_granada, soldado_vivo = s

            _observar_si_no_visto(mundo, kb_plan, pos)

            if pos not in exploradas_vistas:
                exploradas_vistas.add(pos)
                exploradas_orden.append((pos, _valor(s)))

            if trazar:
                # Para mantener el trazado útil sin copiar el del otro código:
                # mostramos solo posiciones y su "valor" (g/h/f) en el orden actual.
                frontera_show = []
                for st in frontera[idx:] if metodo == "bfs" else frontera:
                    if st in cerrados:
                        continue
                    frontera_show.append((st[0], _valor(st)))
                removed_val = _valor(s)
                print(
                    f"{paso:>4d} | {formatear_nodos_traza(frontera_show)} | "
                    f"{formatear_nodos_traza([(pos, removed_val)])} | {formatear_nodos_traza(exploradas_orden)}"
                )
                paso += 1

            if pos == goal:
                return _reconstruir_plan(padre, estado_inicio, s), s  # type: ignore[arg-type]

            cerrados.add(s)

            # Acción granada (si procede)
            if tiene_granada and soldado_vivo:
                s_pos = kb_plan.get("soldier_known")
                if (s_pos is not None) and (distancia_manhattan(pos, s_pos) == 1):
                    d = _direccion_entre(pos, s_pos)
                    if d is not None:
                        s2 = (pos, False, False)
                        if (s2 not in padre) and (s2 not in cerrados):
                            padre[s2] = (s, f"G{d}")
                            g_cost[s2] = g_cost[s] + 1
                            frontera.append(s2)
                            _observar_si_no_visto(mundo, kb_plan, pos)

            # Movimientos
            for d in FRONTIER_DIR_ORDER:
                nxt = mover_posicion(pos, d)
                if not esta_en_tablero(int(mundo["n"]), nxt):
                    continue
                if (nxt not in forzadas) and (not _es_segura_en_estado(kb_plan, nxt, soldado_vivo)):
                    continue

                s2 = (nxt, tiene_granada, soldado_vivo)
                if (s2 in cerrados) or (s2 in padre):
                    continue
                padre[s2] = (s, d)
                g_cost[s2] = g_cost[s] + 1
                frontera.append(s2)
                _observar_si_no_visto(mundo, kb_plan, nxt)

        return None, None

    # GBFS / A*
    abierta: list[tuple[int, int, tuple]] = []
    desempate = 0

    def push(st: tuple) -> None:
        nonlocal desempate
        g = g_cost.get(st, 0)
        h = int(goal_h(st[0]))
        f = h if metodo == "gbfs" else (g + h)
        desempate += 1
        heap_insertar(abierta, (f, desempate, st))

    push(estado_inicio)

    while abierta:
        f_val, _, s = heap_extraer(abierta)
        if s in cerrados:
            continue

        pos, tiene_granada, soldado_vivo = s

        _observar_si_no_visto(mundo, kb_plan, pos)

        if pos not in exploradas_vistas:
            exploradas_vistas.add(pos)
            exploradas_orden.append((pos, _valor(s)))

        if trazar:
            # Snapshot ligero de la frontera (heap) filtrando cerrados
            frontera_show = []
            for (ff, _, st) in abierta:
                if st in cerrados:
                    continue
                frontera_show.append((st[0], _valor(st)))
            removed_val = _valor(s)
            print(
                f"{paso:>4d} | {formatear_nodos_traza(frontera_show)} | "
                f"{formatear_nodos_traza([(pos, removed_val)])} | {formatear_nodos_traza(exploradas_orden)}"
            )
            paso += 1

        if pos == goal:
            return _reconstruir_plan(padre, estado_inicio, s), s  # type: ignore[arg-type]

        cerrados.add(s)

        # Acción granada (si procede)
        if tiene_granada and soldado_vivo:
            s_pos = kb_plan.get("soldier_known")
            if (s_pos is not None) and (distancia_manhattan(pos, s_pos) == 1):
                d = _direccion_entre(pos, s_pos)
                if d is not None:
                    s2 = (pos, False, False)
                    if (s2 not in padre) and (s2 not in cerrados):
                        padre[s2] = (s, f"G{d}")
                        g_cost[s2] = g_cost[s] + 1
                        push(s2)

        for d in FRONTIER_DIR_ORDER:
            nxt = mover_posicion(pos, d)
            if not esta_en_tablero(int(mundo["n"]), nxt):
                continue
            if (nxt not in forzadas) and (not _es_segura_en_estado(kb_plan, nxt, soldado_vivo)):
                continue

            s2 = (nxt, tiene_granada, soldado_vivo)
            if (s2 in cerrados) or (s2 in padre):
                continue
            padre[s2] = (s, d)
            g_cost[s2] = g_cost[s] + 1
            push(s2)
            _observar_si_no_visto(mundo, kb_plan, nxt)

    return None, None


def _clonar_kb_para_plan(kb: dict[str, object]) -> dict[str, object]:
    """Copia ligera de la KB para usarla en planificación sin contaminar la KB real."""
    kb2 = crear_kb(int(kb["n"]), kb["start"])
    kb2["visited"] = set(kb["visited"])
    kb2["breeze_obs"] = dict(kb["breeze_obs"])
    kb2["snore_obs"] = dict(kb["snore_obs"])
    kb2["glow_obs"] = dict(kb["glow_obs"])
    kb2["scream_obs"] = dict(kb["scream_obs"])
    kb2["soldier_alive"] = bool(kb.get("soldier_alive", True))
    inferir_todo(kb2)
    return kb2


def planificar_objetivo_auto(
    mundo: dict[str, object],
    kb_plan: dict[str, object],
    estado_inicio: tuple[tuple[int, int], bool, bool],
    goal: tuple[int, int],
    metodo: str,
    nombre_fase: str,
    trazar: bool,
) -> tuple[list[str] | None, tuple[tuple[int, int], bool, bool] | None, bool]:
    """Planifica una ruta completa hasta `goal`, pudiendo pedir al usuario asumir riesgo ('?')."""
    forzadas: set[tuple[int, int]] = set()
    risky_used = False

    while True:
        visitadas_antes = len(kb_plan["visited"])

        acciones, estado_fin = _buscar_ruta(
            mundo=mundo,
            kb_plan=kb_plan,
            estado_inicio=estado_inicio,
            goal=goal,
            metodo=metodo,
            forzadas=forzadas,
            trazar=trazar,
            nombre_fase=nombre_fase,
        )

        if acciones is not None:
            return acciones, estado_fin, risky_used

        # Si durante la búsqueda hemos observado nuevas celdas, reintentamos (la KB ha cambiado).
        if len(kb_plan["visited"]) > visitadas_antes:
            continue

        # Atasco real: no hay ruta en lo que es demostrablemente seguro.
        candidatos = _candidatos_riesgo(kb_plan, forzadas)
        if not candidatos:
            return None, None, risky_used

        print(
            f"[Auto:{nombre_fase}] No hay estados demostrablemente seguros para expandir. "
            "Solo quedan celdas con '?' (riesgo)."
        )
        if not pedir_si_no("¿Quieres arriesgar expandiendo UNA celda '?'? [s/n] (por defecto n): ", por_defecto=False):
            return None, None, risky_used

        elegido = _elegir_riesgo(candidatos, goal)
        print(f"[Auto:{nombre_fase}] Asumiendo riesgo: se añadirá {elegido} a la búsqueda.")
        forzadas.add(elegido)
        _observar_si_no_visto(mundo, kb_plan, elegido)
        risky_used = True


def ejecutar_auto(
    world: dict[str, object],
    kb: dict[str, object],
    metodo_busqueda: str,
    max_pasos: int = 500,
    verbose: bool = True,
) -> None:
    """Modo automático: PLANIFICAR TODO (Kurtz -> Salida) y luego EJECUTAR.

    Requisitos implementados:
      - Se planifica completamente antes de ejecutar.
      - Fase 1: planificar hasta Kurtz.
      - Fase 2: reiniciar frontera/explorados (búsqueda nueva) sin perder perceptos y planificar hasta la salida.
      - Durante la planificación se permite consultar perceptos de nodos en frontera y explorados.
      - Si no quedan estados seguros, se pregunta al usuario si quiere arriesgar expandiendo una celda con '?'.

    Nota: la implementación del planificador NO replica la del fichero `kurtz.py`:
      - Aquí se usa un bucle de planificación por "rondas" con KB creciente y un conjunto de celdas forzadas (riesgo).
      - La búsqueda interna opera sobre estados (pos, granada, soldado_vivo) e incorpora la acción G<dir>.
    """
    metodo = metodo_busqueda.lower()

    # --- Percepción inicial REAL (antes de planificar) ---
    per0 = calcular_percepto(world)
    actualizar_kb(kb, world["agent"], per0, soldado_vivo=world["soldier_alive"])

    if verbose:
        print()
        mostrar_tablero(world, kb, per0)
        recomendar_movimientos(world, kb)

    # --- KB separada para planificación ---
    kb_plan = _clonar_kb_para_plan(kb)

    estado_inicio = (world["agent"], bool(world["grenade"]), bool(world["soldier_alive"]))

    # --- Fase 1: hasta Kurtz ---
    acciones1, estado_kurtz, risky1 = planificar_objetivo_auto(
        mundo=world,
        kb_plan=kb_plan,
        estado_inicio=estado_inicio,
        goal=world["kurtz"],
        metodo=metodo,
        nombre_fase="Kurtz",
        trazar=bool(verbose),
    )
    if acciones1 is None or estado_kurtz is None:
        print("[Auto] No se ha encontrado un plan hasta Kurtz con la información disponible.")
        return

    # --- Fase 2: hasta salida (reinicia búsqueda, conserva perceptos en kb_plan) ---
    acciones2, estado_salida, risky2 = planificar_objetivo_auto(
        mundo=world,
        kb_plan=kb_plan,
        estado_inicio=estado_kurtz,
        goal=world["exit"],
        metodo=metodo,
        nombre_fase="Salida",
        trazar=bool(verbose),
    )
    if acciones2 is None or estado_salida is None:
        print("[Auto] No se ha encontrado un plan hasta la salida con la información disponible.")
        return

    plan_total = list(acciones1) + list(acciones2) + ["X"]

    if verbose:
        print("\n=== PLAN COMPLETO (antes de ejecutar) ===")
        print("Fase 1 (Kurtz):", plan_a_teclas(acciones1))
        print("Fase 2 (Salida):", plan_a_teclas(acciones2 + ["X"]))
        print("Total:", plan_a_teclas(plan_total))
        print("\n=== EJECUCIÓN ===\n")

    # --- Ejecución REAL del plan ---
    acciones_ejecutadas: list[str] = []
    posiciones_recorridas: list[tuple[int, int]] = [world["agent"]]

    pasos = 0
    for act in plan_total:
        if not bool(world["alive"]):
            break

        pasos += 1
        if pasos > max_pasos:
            print("[Auto] Límite de pasos alcanzado. Abortando.")
            imprimir_resumen_auto(acciones_ejecutadas, posiciones_recorridas)
            return

        if act == "X":
            ok = accion_salir(world)
            acciones_ejecutadas.append("X")
            posiciones_recorridas.append(world["agent"])
            if ok:
                if verbose:
                    mostrar_tablero(world, kb)
                print("[Auto] ¡Misión completada! (has salido con Kurtz).")
            else:
                print("[Auto] Acción 'salir' inválida (no estás en la salida o falta Kurtz).")
            imprimir_resumen_auto(acciones_ejecutadas, posiciones_recorridas)
            return

        if act.startswith("G") and len(act) == 2 and act[1] in DIRS:
            accion_granada(world, act[1])
            acciones_ejecutadas.append(act)
            posiciones_recorridas.append(world["agent"])
        elif act in DIRS:
            accion_mover(world, act)
            acciones_ejecutadas.append(act)
            posiciones_recorridas.append(world["agent"])
        else:
            print(f"[Auto] Acción inesperada en el plan: {act!r}. Abortando.")
            imprimir_resumen_auto(acciones_ejecutadas, posiciones_recorridas)
            return

        if not bool(world["alive"]):
            if verbose:
                mostrar_tablero(world, kb)
            print("[Auto] Has muerto durante la ejecución del plan.")
            if risky1 or risky2:
                print("[Auto] Nota: durante la planificación se aceptó riesgo (expansión de '?').")
            imprimir_resumen_auto(acciones_ejecutadas, posiciones_recorridas)
            return

        per = calcular_percepto(world)
        actualizar_kb(kb, world["agent"], per, soldado_vivo=world["soldier_alive"])

        if verbose:
            mostrar_tablero(world, kb, per)
            recomendar_movimientos(world, kb)

    print("[Auto] Fin del plan sin completar la misión (faltó 'X' o no se pudo salir).")
    imprimir_resumen_auto(acciones_ejecutadas, posiciones_recorridas)


def main() -> None:
    """Punto de entrada del programa.
    
    - Muestra cabecera.
    - Pregunta el modo (manual/auto) y, en automático, el método de búsqueda.
    - Permite activar/desactivar colores en consola (opcional).
    - Permite fijar semilla para reproducibilidad.
    - Crea el mundo, inicializa KB y ejecuta el bucle correspondiente.
    """
    global USE_COLOR
    print_banner("PROYECTO FIA: BUSCANDO AL CORONEL KURTZ")

    mode = pedir_opcion("En que modo desea jugar (escoja manual/auto): ", ["manual", "auto"])

    metodo_busqueda= "bfs"
    verbose = True
    if mode == "auto":
        metodo_busqueda= pedir_opcion("Elige búsqueda [bfs/dfs/gbfs/astar]: ", ["bfs", "dfs", "gbfs", "astar"])
        verbose = not pedir_si_no("¿Modo silencioso (menos prints)? [s/n] (por defecto n): ", por_defecto=False)

    USE_COLOR = pedir_si_no("¿Desea usar colores en la consola? [s/n] (por defecto SÍ se usarán): ", por_defecto=True)

    seed = pedir_semilla()
    if seed is not None:
        random.seed(seed)

    world = crear_mundo(6, start=(1, 1))
    kb = crear_kb(int(world["n"]), world["start"])

    if mode == "manual":
        ejecutar_manual(world, kb)
    else:
        ejecutar_auto(world, kb, metodo_busqueda=metodo_busqueda, max_pasos=500, verbose=verbose)

if __name__ == "__main__":
    main()
