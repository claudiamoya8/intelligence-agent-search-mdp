#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# Puede existir un `kurtz.py` no compatible (o con nombres distintos).
# Si lo importamos "a ciegas", el programa arranca y luego revienta con AttributeError. Por eso:
#
#   1) probamos `kurtz` y `kurtz_bueno`,
#   2) verificamos que tenga las funciones mínimas que usamos,
#   3) si no, seguimos intentando el siguiente.
#
def _cargar_parte1():
    """Importa el módulo de Parte 1 válido (kurtz.py).

Args:
    (sin parámetros)

Returns:
    object: Módulo de la Parte 1 importado (kurtz) que expone las funciones de consola requeridas.

Raises:
    ImportError: Si no se encuentra un módulo de Parte 1 compatible ('kurtz.py') o le faltan funciones requeridas.
    """
    candidatos = ("kurtz",)
    requeridas = (
        "print_banner",
        "print_section",
        "pedir_opcion",
        "pedir_si_no",
        "pedir_semilla",
        "paint",
        "random",
        "vecinos_ortogonales",
        "mover_posicion",
        "esta_en_tablero",
        "distancia_manhattan",
    )
    for nombre in candidatos:
        try:
            mod = __import__(nombre)
        except ImportError:
            continue
        if all(hasattr(mod, fn) for fn in requeridas):
            return mod
    raise ImportError(
        "No se encontró un módulo de Parte 1 compatible. "
        "Asegúrate de tener 'kurtz.py' en el mismo directorio "
        "y que contenga las funciones de consola (print_banner, pedir_opcion, etc.)."
    )

p1 = _cargar_parte1()


# -----------------------------------------------------------------------------
# Tipos y utilidades básicas
# -----------------------------------------------------------------------------

Pos = tuple[int, int]  # (fila, col) 1-indexado


def todas_las_celdas(n: int) -> list[Pos]:
    """Devuelve todas las celdas (1-indexadas) de un tablero n×n.

Args:
    n (int): Tamaño del tablero (n×n).

Returns:
    list[Pos]: Lista de celdas (fila, columna) 1-indexadas.
    """
    return [(r, c) for r in range(1, n + 1) for c in range(1, n + 1)]


def zona_estimulo(n: int, loc: Pos) -> set[Pos]:
    """Zona donde se detecta el estímulo de un elemento ubicado en ``loc``.

Notas:
    Según el enunciado, un estímulo se percibe en la propia celda del elemento y en sus vecinos ortogonales (4-conexos), es decir: {loc} ∪ vecinos_ortogonales(loc).

Args:
    n (int): Tamaño del tablero (n×n).
    loc (Pos): Celda (fila, columna) donde está el elemento en la rejilla (1-indexada).

Returns:
    set[Pos]: Conjunto de celdas (fila, columna) 1-indexadas.
    """
    z = set(p1.vecinos_ortogonales(n, loc))
    z.add(loc)
    return z


def normalizar(dist: dict[Pos, float]) -> dict[Pos, float]:
    """Normaliza una distribución discreta (si suma 0, la deja tal cual).

Args:
    dist (dict[Pos, float]): Distribución discreta {celda: probabilidad}.

Returns:
    dict[Pos, float]: Distribución normalizada para que la suma sea 1 (si la suma era 0, se devuelve sin cambios).
    """
    s = 0.0
    for v in dist.values():
        s += float(v)
    if s <= 0.0:
        return dist
    return {k: float(v) / s for (k, v) in dist.items()}


def prior_uniforme(dominio: list[Pos]) -> dict[Pos, float]:
    """Prior uniforme sobre un dominio (lista de celdas).

Args:
    dominio (list[Pos]): Lista de celdas sobre las que se define una distribución discreta.

Returns:
    dict[Pos, float]: Mapa {celda: probabilidad} asociado al cálculo realizado.
    """
    if not dominio:
        return {}
    pr = 1.0 / float(len(dominio))
    return {p: pr for p in dominio}


# -----------------------------------------------------------------------------
# Mundo real (oculto)
# -----------------------------------------------------------------------------


def crear_mundo_bayes(n: int = 6, inicio: Pos = (1, 1)) -> dict[str, object]:
    """Crea un mundo Bayesiano aleatorio (mapa real oculto).

Args:
    n (int): Tamaño del tablero (n×n).
    inicio (Pos): Celda inicial del capitán (fila, columna) 1-indexada.

Returns:
    dict[str, object]: Mundo real oculto con posiciones de elementos y estado dinámico del episodio.

Raises:
    RuntimeError: Si no se consigue construir un mundo válido tras varios intentos.
    ValueError: Si algún parámetro es inválido (por ejemplo, un destino fuera del tablero o un método desconocido).
    """
    if n < 3:
        raise ValueError("n debe ser >= 3")
    if not p1.esta_en_tablero(n, inicio):
        raise ValueError("inicio fuera del tablero")

    celdas = todas_las_celdas(n)
    dominio_sin_inicio = [p for p in celdas if p != inicio]

    # Trampas (solapables)
    f = p1.random.choice(dominio_sin_inicio)
    p = p1.random.choice(dominio_sin_inicio)
    d = p1.random.choice(dominio_sin_inicio)
    traps: dict[str, set[Pos]] = {"F": {f}, "P": {p}, "D": {d}}

    celdas_trampa = set()
    for s in traps.values():
        celdas_trampa |= set(s)

    seguras = [x for x in dominio_sin_inicio if x not in celdas_trampa]
    if not seguras:
        raise RuntimeError("No hay celdas seguras para colocar M/S/CK.")

    soldier = p1.random.choice(seguras)
    exit_pos = p1.random.choice(seguras)
    kurtz = p1.random.choice(seguras)

    return {
        "n": n,
        "start": inicio,
        "agent": inicio,
        "alive": True,
        "kurtz_found": False,
        "grenade": True,
        "soldier_alive": True,
        "last_scream": False,   # Grito=1 solo el turno posterior a granada efectiva
        "exit_seen": False,     # se marca True tras pisar la salida
        "exit_known": None,     # Pos si se ha pisado la salida
        # elementos reales:
        "traps": traps,
        "soldier": soldier,
        "exit": exit_pos,
        "kurtz": kurtz,
    }


def en_trampa(world: dict[str, object], pos: Pos) -> bool:
    """Devuelve True si `pos` contiene alguna trampa real.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    pos (Pos): Celda (fila, columna) 1-indexada.

Returns:
    bool: True si la celda contiene alguna trampa real; False en caso contrario.
    """
    traps: dict[str, set[Pos]] = world["traps"]
    for s in traps.values():
        if pos in s:
            return True
    return False


def comprobar_muerte_y_eventos(world: dict[str, object]) -> None:
    """Actualiza el estado del mundo tras estar en la celda actual.

Notas:
    - Si pisa trampa: muere.
    - Si pisa soldado vivo: muere.
    - Si pisa CK: lo rescata.
    - Si pisa salida: la descubre (aunque solo puede salir si ya lleva a CK).

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    if not bool(world["alive"]):
        return

    pos: Pos = world["agent"]

    if en_trampa(world, pos):
        world["alive"] = False
        return

    if bool(world["soldier_alive"]) and (pos == world["soldier"]):
        world["alive"] = False
        return

    if pos == world["kurtz"]:
        world["kurtz_found"] = True

    if pos == world["exit"]:
        world["exit_seen"] = True
        world["exit_known"] = pos


# -----------------------------------------------------------------------------
# Perceptos (Bayes)
# -----------------------------------------------------------------------------


def calcular_percepto_bayes(world: dict[str, object]) -> list[bool]:
    """Calcula el percepto en la celda actual.

Notas:
    Orden del percepto (enunciado): [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].
    Grito es transitorio: solo vale 1 el turno posterior a una granada efectiva.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.

Returns:
    list[bool]: Percepto codificado como lista de booleanos en el orden del enunciado.
    """
    n = int(world["n"])
    pos: Pos = world["agent"]

    traps: dict[str, set[Pos]] = world["traps"]
    locF = next(iter(traps["F"]))
    locP = next(iter(traps["P"]))
    locD = next(iter(traps["D"]))

    eF = pos in zona_estimulo(n, locF)
    eP = pos in zona_estimulo(n, locP)
    eD = pos in zona_estimulo(n, locD)

    eM = False
    if bool(world["soldier_alive"]):
        eM = pos in zona_estimulo(n, world["soldier"])

    eS = pos in zona_estimulo(n, world["exit"])

    r, c = pos
    pared_up = (r == 1)
    pared_down = (r == n)
    pared_left = (c == 1)
    pared_right = (c == n)

    grito = bool(world.get("last_scream", False))
    world["last_scream"] = False  # consumo del evento

    return [eF, eP, eD, eM, eS, pared_up, pared_down, pared_left, pared_right, grito]


def format_percept_bayes(per: list[bool]) -> str:
    """Devuelve el percepto formateado con la notación del enunciado (Parte 2).

Notas:
    El string incluye los nombres en el mismo orden que el percepto: eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→ y Grito.

Args:
    per (list[bool]): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].

Returns:
    str: Representación en texto del resultado.
    """
    order = [
        ("e_F?", 0),
        ("e_P?", 1),
        ("e_D?", 2),
        ("e_M?", 3),
        ("e_S?", 4),
        ("Pared↑?", 5),
        ("Pared↓?", 6),
        ("Pared←?", 7),
        ("Pared→?", 8),
        ("Grito?", 9),
    ]

    s = "Percepto: ["
    k = 0
    while k < len(order):
        name, idx = order[k]
        s = s + name + "=" + str(int(bool(per[idx])))
        if k != len(order) - 1:
            s = s + ", "
        k += 1
    s = s + "]"
    return s


# -----------------------------------------------------------------------------
# KB Bayesiana (posteriors)
# -----------------------------------------------------------------------------


def crear_kb_bayes(n: int, start: Pos) -> dict[str, object]:
    """Inicializa la KB con priors uniformes (sin conocimiento previo).

Args:
    n (int): Tamaño del tablero (n×n).
    start (Pos): Celda inicial del capitán (fila, columna) 1-indexada.

Returns:
    dict[str, object]: KB inicial con priors uniformes y estructuras de seguimiento (visitadas/observaciones).
    """
    dominio = [p for p in todas_las_celdas(n) if p != start]
    return {
        "n": n,
        "start": start,
        "visited": {start},
        "obs": {},
        "posterior_F": prior_uniforme(dominio),
        "posterior_P": prior_uniforme(dominio),
        "posterior_D": prior_uniforme(dominio),
        "posterior_M": prior_uniforme(dominio),
        "posterior_S": prior_uniforme(dominio),
        "posterior_CK": prior_uniforme(dominio),
    }


def actualizar_posterior_determinista(
    n: int,
    dist: dict[Pos, float],
    observacion: bool,
    celda_actual: Pos,
) -> dict[Pos, float]:
    """Actualiza una posterior usando la verosimilitud determinista del enunciado.

Args:
    n (int): Tamaño del tablero (n×n).
    dist (dict[Pos, float]): Distribución discreta {celda: probabilidad}.
    observacion (bool): Observación booleana del estímulo (True si se percibe, False si no).
    celda_actual (Pos): Celda desde la que se realiza la observación/percepción.

Returns:
    dict[Pos, float]: Mapa {celda: probabilidad} asociado al cálculo realizado.
    """
    out: dict[Pos, float] = {}
    for loc, pr in dist.items():
        en_z = celda_actual in zona_estimulo(n, loc)
        like = 1.0 if (en_z == observacion) else 0.0
        out[loc] = float(pr) * like
    return normalizar(out)


def imponer_no_trampa_en_visitadas(kb: dict[str, object]) -> None:
    """Si el capitán ha visitado una celda y sigue vivo, ahí no había trampa.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    visited: set[Pos] = kb["visited"]
    for key in ("posterior_F", "posterior_P", "posterior_D"):
        dist: dict[Pos, float] = kb[key]
        for p in visited:
            if p in dist:
                dist[p] = 0.0
        kb[key] = normalizar(dist)


def prob_hay_alguna_trampa(kb: dict[str, object], celda: Pos) -> float:
    """Aprox. P(hay al menos una trampa en celda) suponiendo independencia F/P/D.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    celda (Pos): Parámetro de la función.

Returns:
    float: Probabilidad aproximada calculada a partir de los posteriors actuales.
    """
    pF = float(kb["posterior_F"].get(celda, 0.0))
    pP = float(kb["posterior_P"].get(celda, 0.0))
    pD = float(kb["posterior_D"].get(celda, 0.0))
    return 1.0 - (1.0 - pF) * (1.0 - pP) * (1.0 - pD)



def _peso_seguridad_exacto_para_celda(
    dominio: list[Pos],
    postF: dict[Pos, float],
    postP: dict[Pos, float],
    postD: dict[Pos, float],
    celda: Pos,
) -> float:
    """Peso EXACTO para imponer 'M/S no pueden estar en celdas con trampas'.

Notas:
    El PDF indica que (M, S, CK) están en celdas sin trampas, aunque pueden coincidir entre sí.
    Como las trampas (F, P, D) son inciertas, esto se traduce en un prior inducido:

        w(c) = E_{F,P,D}[ 1(c es segura) / |Safe(F,P,D)| ]

    donde Safe(F,P,D) es el conjunto de celdas candidatas libres de *alguna* trampa
    (las trampas pueden solaparse, así que se toma unión).

    Este cálculo evita aproximaciones del tipo (1 - P(trampa)) y hace que los mapas de
    posterior para M y S sean coherentes con el modelo generativo.

    Complejidad: O(N^4) en el peor caso (tres bucles sobre dominio y uno para contar Safe),
    pero con N=36 es perfectamente asumible.

Args:
    dominio (list[Pos]): Lista de celdas sobre las que se define una distribución discreta.
    postF (dict[Pos, float]): Posterior de la ubicación de la trampa F (fuego).
    postP (dict[Pos, float]): Posterior de la ubicación de la trampa P (pinchos).
    postD (dict[Pos, float]): Posterior de la ubicación de la trampa D (dardos).
    celda (Pos): Parámetro de la función.

Returns:
    float: Valor numérico calculado por la función.
    """
    total = 0.0
    # Enumeración exacta de combinaciones (locF, locP, locD).
    for locF, pF in postF.items():
        if pF <= 0.0:
            continue
        for locP, pP in postP.items():
            if pP <= 0.0:
                continue
            for locD, pD in postD.items():
                if pD <= 0.0:
                    continue
                prob = float(pF) * float(pP) * float(pD)
                if prob <= 0.0:
                    continue

                traps = {locF, locP, locD}

                # Cuenta de celdas seguras disponibles para M/S.
                safe_count = 0
                for p in dominio:
                    if p not in traps:
                        safe_count += 1
                if safe_count <= 0:
                    continue

                # Si celda no es segura en esta realización, contribución 0.
                if celda in traps:
                    continue

                total += prob * (1.0 / float(safe_count))
    return float(total)


def _pesos_seguridad_exactos_cache(kb: dict[str, object]) -> dict[Pos, float]:
    """Pesos exactos para "celda segura" (M/S/CK), con *cache* y versión rápida.

Notas:
    En el modelo, el soldado / salida / Kurtz se colocan uniformemente entre las celdas
    libres de trampas. Dado un triple (F, P, D), la probabilidad de cada celda segura
    es 1 / (#celdas seguras) y 0 en las celdas con trampa.

    Para evitar el coste O(|F||P||D||dominio|), usamos el truco:
      - cada triple añade +A a *todas* las celdas,
      - y luego restamos A solo en las 1–3 celdas de trampa del triple,
    donde A = P(F)P(P)P(D) / (#seguras).

    Con esto pasamos a O(|F||P||D|) con un factor constante pequeño, que acelera
    mucho el arranque (donde se recalculan posteriors varias veces).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    dict[Pos, float]: Mapa {celda: probabilidad} asociado al cálculo realizado.
    """
    postF: dict[Pos, float] = kb["posterior_F"]
    postP: dict[Pos, float] = kb["posterior_P"]
    postD: dict[Pos, float] = kb["posterior_D"]

    sig = (id(postF), id(postP), id(postD))
    if kb.get("_w_safe_sig") == sig and isinstance(kb.get("_w_safe_cache"), dict):
        return kb["_w_safe_cache"]  # type: ignore[return-value]

    n = int(kb["n"])

    # Dominio "real" sin la celda de inicio (donde no pueden estar τ, M, S ni CK).
    dominio: list[Pos]
    if isinstance(kb.get("_dominio_no_start"), list):
        dominio = kb["_dominio_no_start"]  # type: ignore[assignment]
    else:
        start: Pos = kb["start"]
        dominio = [p for p in todas_las_celdas(n) if p != start]
        kb["_dominio_no_start"] = dominio

    # Mapa celda -> índice (para actualizar deltas en O(1))
    idx_map: dict[Pos, int]
    if isinstance(kb.get("_dominio_idx"), dict):
        idx_map = kb["_dominio_idx"]  # type: ignore[assignment]
    else:
        idx_map = {p: i for i, p in enumerate(dominio)}
        kb["_dominio_idx"] = idx_map

    listF = [(p, float(w)) for (p, w) in postF.items() if float(w) > 0.0]
    listP = [(p, float(w)) for (p, w) in postP.items() if float(w) > 0.0]
    listD = [(p, float(w)) for (p, w) in postD.items() if float(w) > 0.0]

    dom_len = len(dominio)
    if dom_len <= 0:
        return {}

    w_all = 0.0
    delta = [0.0] * dom_len

    for locF, pF in listF:
        for locP, pP in listP:
            pFP = pF * pP
            if pFP <= 0.0:
                continue
            for locD, pD in listD:
                prob = pFP * pD
                if prob <= 0.0:
                    continue

                # Número de celdas con trampa en el triple (1..3)
                traps = 1
                if locP != locF:
                    traps += 1
                if locD != locF and locD != locP:
                    traps += 1

                safe_count = dom_len - traps
                if safe_count <= 0:
                    continue

                A = prob / float(safe_count)

                # A se añade a todas las celdas y se resta solo en las de trampa
                w_all += A
                delta[idx_map[locF]] -= A
                if locP != locF:
                    delta[idx_map[locP]] -= A
                if locD != locF and locD != locP:
                    delta[idx_map[locD]] -= A

    w_map = {p: (w_all + delta[idx_map[p]]) for p in dominio}

    kb["_w_safe_sig"] = sig
    kb["_w_safe_cache"] = w_map
    return w_map
def reponderar_por_no_trampas(kb: dict[str, object], clave: str) -> None:
    """Repondera posterior_M / posterior_S / posterior_CK usando Bayes EXACTO, pero eficiente.

Notas:
    Una implementación directa calcularía w(c) por celda y repetiría mucho trabajo.
    Aquí se calcula un mapa w(c) una sola vez (cacheado) y se aplica al posterior pedido.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    clave (str): Clave dentro de la KB (por ejemplo, 'posterior_M' o 'posterior_S') a reponderar.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    w_map = _pesos_seguridad_exactos_cache(kb)

    dist: dict[Pos, float] = kb[clave]
    out: dict[Pos, float] = {}
    for celda, pr in dist.items():
        out[celda] = float(pr) * float(w_map.get(celda, 0.0))
    kb[clave] = normalizar(out)



def imponer_no_kurtz_en_visitadas(kb: dict[str, object]) -> None:
    """Si aún no hemos rescatado a Kurtz, no puede estar en celdas ya visitadas.

Notas:
    Justificación: al entrar en una celda, si CK estuviera allí, lo habríamos rescatado
    inmediatamente (no hay incertidumbre observacional sobre CK una vez pisamos su celda).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    visited: set[Pos] = kb["visited"]
    dist: dict[Pos, float] = kb["posterior_CK"]
    for p in visited:
        if p in dist:
            dist[p] = 0.0
    kb["posterior_CK"] = normalizar(dist)


def imponer_no_soldado_en_visitadas(kb: dict[str, object]) -> None:
    """Si el soldado está vivo, no puede estar en celdas que ya visitamos (seguimos vivos).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    visited: set[Pos] = kb["visited"]
    dist: dict[Pos, float] = kb["posterior_M"]
    for p in visited:
        if p in dist:
            dist[p] = 0.0
    kb["posterior_M"] = normalizar(dist)


def fijar_salida_descubierta(kb: dict[str, object], exit_pos: Pos) -> None:
    """Si ya hemos pisado la salida, su posterior colapsa a una delta.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    exit_pos (Pos): Celda donde está la salida (fila, columna) 1-indexada.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    dist: dict[Pos, float] = kb["posterior_S"]
    for p in list(dist.keys()):
        dist[p] = 0.0
    if exit_pos in dist:
        dist[exit_pos] = 1.0
    kb["posterior_S"] = normalizar(dist)


def actualizar_kb_bayes(kb: dict[str, object], world: dict[str, object], per: list[bool]) -> None:
    """Actualiza la KB con el percepto actual (in-place).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    per (list[bool]): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    n = int(kb["n"])
    pos: Pos = world["agent"]

    kb["visited"].add(pos)

    # Trampas
    kb["posterior_F"] = actualizar_posterior_determinista(n, kb["posterior_F"], bool(per[0]), pos)
    kb["posterior_P"] = actualizar_posterior_determinista(n, kb["posterior_P"], bool(per[1]), pos)
    kb["posterior_D"] = actualizar_posterior_determinista(n, kb["posterior_D"], bool(per[2]), pos)

    imponer_no_trampa_en_visitadas(kb)

    # Soldado
    if bool(world["soldier_alive"]):
        kb["posterior_M"] = actualizar_posterior_determinista(n, kb["posterior_M"], bool(per[3]), pos)
        imponer_no_soldado_en_visitadas(kb)
        reponderar_por_no_trampas(kb, "posterior_M")

    # Salida
    kb["posterior_S"] = actualizar_posterior_determinista(n, kb["posterior_S"], bool(per[4]), pos)
    reponderar_por_no_trampas(kb, "posterior_S")

    # Kurtz (CK): no tiene estímulo propio; su posterior solo cambia por restricciones
    # estructurales (no puede estar en trampas) y por descarte al visitar celdas.
    if not bool(world["kurtz_found"]):
        imponer_no_kurtz_en_visitadas(kb)
        reponderar_por_no_trampas(kb, "posterior_CK")
    else:
        # Si ya lo rescatamos, lo tratamos como observado: CK está "con nosotros".
        kb["posterior_CK"] = {world["agent"]: 1.0}

    if world.get("exit_known") is not None:
        fijar_salida_descubierta(kb, world["exit_known"])


# -----------------------------------------------------------------------------
# Riesgo y celdas permitidas
# -----------------------------------------------------------------------------


def riesgo_trampas(kb: dict[str, object]) -> dict[Pos, float]:
    """Mapa de riesgo P(hay alguna trampa) para cada celda del dominio.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    dict[Pos, float]: Mapa {celda: probabilidad} con el riesgo asociado a cada celda.
    """
    out: dict[Pos, float] = {}
    for p in kb["posterior_F"].keys():
        out[p] = prob_hay_alguna_trampa(kb, p)
    return out


def riesgo_muerte(kb: dict[str, object], world: dict[str, object]) -> dict[Pos, float]:
    """Mapa de riesgo de morir al entrar en una celda.

Notas:
    Como el soldado no puede compartir celda con trampas, los sucesos son disjuntos:
    P(muerte) = P(trampa) + P(soldado) (acotado a 1).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.

Returns:
    dict[Pos, float]: Mapa {celda: probabilidad} con el riesgo asociado a cada celda.
    """
    rt = riesgo_trampas(kb)
    out: dict[Pos, float] = {}

    soldado_vivo = bool(world["soldier_alive"])
    distM: dict[Pos, float] = kb["posterior_M"]

    for p, pt in rt.items():
        pm = float(distM.get(p, 0.0)) if soldado_vivo else 0.0
        out[p] = 1.0 if (pt + pm) >= 1.0 else (pt + pm)

    # La celda inicial (start) no está en el dominio de los posteriors; añadimos 0 por comodidad.
    start: Pos = kb["start"]
    out[start] = 0.0
    return out


def celdas_permitidas(kb: dict[str, object], world: dict[str, object], p_umbral: float) -> set[Pos]:
    """Celdas por las que el automático permite planificar.

Notas:
    Incluye siempre las celdas visitadas. Además, añade celdas con riesgo < p_umbral y, si la salida ya se ha descubierto, la permite aunque su riesgo sea alto.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.

Returns:
    set[Pos]: Conjunto de celdas (fila, columna) 1-indexadas.
    """
    visited: set[Pos] = kb["visited"]
    permitidas = set(visited)

    rm = riesgo_muerte(kb, world)
    for p, r in rm.items():
        if r < float(p_umbral):
            permitidas.add(p)

    if world.get("exit_known") is not None:
        permitidas.add(world["exit_known"])

    return permitidas


# -----------------------------------------------------------------------------
# Impresión (mapas + resumen) con estilo similar a Parte 1
# -----------------------------------------------------------------------------


def _estilo_prob(valor: float) -> str:
    """Estilo ANSI en función del valor (paleta discreta, fácil de leer).

Notas:
    La paleta es discreta y está pensada para lectura rápida en consola; asigna estilos ANSI en función de umbrales del valor.

Args:
    valor (float): Valor numérico asociado (p.ej., probabilidad) usado para colorear/formatear.

Returns:
    str: Representación en texto del resultado.
    """
    v = float(valor)
    if v <= 0.05:
        return p1._DIM
    if v <= 0.20:
        return p1._BLUE
    if v <= 0.40:
        return p1._CYAN
    if v <= 0.60:
        return p1._YELLOW
    return p1._BOLD + p1._RED


def _etiqueta_cw(world: dict[str, object], per: list[bool] | None) -> str:
    """Etiqueta del capitán incluyendo estímulos en su celda.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    per (list[bool] | None): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].

Returns:
    str: Representación en texto del resultado.
    """
    base = "CWK" if bool(world["kurtz_found"]) else "CW"
    if per is None:
        return base

    letras: list[str] = []
    if per[0]:
        letras.append("F")
    if per[1]:
        letras.append("P")
    if per[2]:
        letras.append("D")
    if per[3]:
        letras.append("M")
    if per[4]:
        letras.append("S")
    if per[9]:
        letras.append("G")

    # Construimos sin usar .join (restricción del proyecto).
    s = base
    k = 0
    while k < len(letras):
        s = s + letras[k]
        k += 1
    return s


def _concat_con_sep(items: list[str], sep: str) -> str:
    """Concatena una lista de strings usando un separador, sin usar .join.

Notas:
    El proyecto impone la restricción de no utilizar '.join', por lo que esta función centraliza la concatenación para evitar repetir bucles.

Args:
    items (list[str]): Lista de strings a concatenar.
    sep (str): Separador a insertar entre elementos concatenados.

Returns:
    str: Representación en texto del resultado.
    """
    if not items:
        return ""
    s = items[0]
    k = 1
    while k < len(items):
        s = s + sep + items[k]
        k += 1
    return s


def _celda_padded(txt: str, ancho: int) -> str:
    """Ajusta un texto a un ancho fijo (rellena con espacios y recorta).

Args:
    txt (str): Texto a formatear/mostrar.
    ancho (int): Ancho objetivo (número de caracteres) para formateo en consola.

Returns:
    str: Representación en texto del resultado.
    """
    return txt.ljust(ancho)[:ancho]


def _celda_prob(txt: str, ancho: int, valor: float | None = None, tag: str | None = None) -> str:
    """Formatea una celda con color.

Notas:
    Si se proporciona 'tag', se prioriza un estilo fijo (por ejemplo, CW, salida, visitada). Si no, y se da 'valor', el color depende del rango de probabilidad.

Args:
    txt (str): Texto a formatear/mostrar.
    ancho (int): Ancho objetivo (número de caracteres) para formateo en consola.
    valor (float | None): Valor numérico asociado (p.ej., probabilidad) usado para colorear/formatear.
    tag (str | None): Etiqueta semántica para asignar un estilo fijo (p.ej., 'CW', 'S', 'v').

Returns:
    str: Representación en texto del resultado.
    """
    raw = txt.strip()
    if raw == "":
        # Evita celdas visualmente "vacías" en consola.
        raw = "·"
    style = ""

    if tag is not None:
        t = tag
        if t.startswith("CW"):
            style = p1._BOLD + p1._GREEN
        elif t == "v":
            style = p1._GREEN
        elif t == "S":
            style = p1._BOLD + p1._CYAN
        elif t == "✓":
            style = p1._BOLD + p1._GREEN
        elif t == "*":
            style = p1._DIM

    if (not style) and (valor is not None):
        style = _estilo_prob(valor)

    return p1.paint(_celda_padded(raw, ancho), style)


def imprimir_mapa_probabilidades(
    titulo: str,
    world: dict[str, object],
    dist: dict[Pos, float],
    per: list[bool] | None = None,
    ancho_celda: int = 6,
) -> None:
    """Imprime una distribución discreta como tabla con cabecera de filas/columnas.

Args:
    titulo (str): Título del bloque/tabla a imprimir.
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    dist (dict[Pos, float]): Distribución discreta {celda: probabilidad}.
    per (list[bool] | None): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].
    ancho_celda (int): Ancho (en caracteres) usado para cada celda del mapa impreso.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    n = int(world["n"])
    agent: Pos = world["agent"]

    print(titulo)
    print("  (Valores en [0,1]. El capitán se marca como CW/CWK + estímulos.)")
    print("")

    cabecera = "     "
    c = 1
    while c <= n:
        cabecera = cabecera + _celda_prob(f"{c:>2d}", ancho_celda, tag="*")
        c += 1
    print(cabecera)
    print("     " + "-" * (ancho_celda * n))

    for r in range(1, n + 1):
        fila = []
        for c in range(1, n + 1):
            p = (r, c)
            if p == agent:
                fila.append(_celda_prob(_etiqueta_cw(world, per), ancho_celda, tag="CW"))
            else:
                v = float(dist.get(p, 0.0))
                fila.append(_celda_prob(f"{v:.2f}", ancho_celda, valor=v))
        s_fila = ""
        k = 0
        while k < len(fila):
            s_fila = s_fila + fila[k]
            k += 1
        print(f"{r:>3d} | " + s_fila)
    print("")


def mostrar_mapas_bayes(world: dict[str, object], kb: dict[str, object], per: list[bool]) -> None:
    """Muestra los mapas pedidos en el enunciado: Trampas (cualquiera), Soldado, Salida.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    per (list[bool]): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    p1.print_section("Mapas de probabilidad (Bayes)")

    imprimir_mapa_probabilidades("Trampas (F∪P∪D): P(hay alguna trampa)", world, riesgo_trampas(kb), per=per)
    imprimir_mapa_probabilidades("Militar (M)", world, kb["posterior_M"], per=per)
    imprimir_mapa_probabilidades("Salida (S)", world, kb["posterior_S"], per=per)



def hay_evidencia_estimulos_alrededor(kb: dict[str, object], celda: Pos) -> bool:
    """Devuelve True si hay evidencia de estímulos alrededor de ``celda``.

Notas:
    Interpretación (estilo Parte 1):
    - Consideramos que hay "evidencia" si existe algún vecino ortogonal de ``celda`` que
      haya sido visitado y en el que se haya observado algún estímulo positivo
      (eF/eP/eD/eM/eS).

    Esto se usa únicamente para la notación visual '.' (celda potencialmente peligrosa
    pero sin señales alrededor conocidas todavía).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    celda (Pos): Parámetro de la función.

Returns:
    bool: True si se cumple la condición indicada; False en caso contrario.
    """
    n = int(kb["n"])
    obs: dict[Pos, list[bool]] = kb.get("obs", {})
    visited: set[Pos] = kb["visited"]

    for v in p1.vecinos_ortogonales(n, celda):
        if v in visited:
            per_v = obs.get(v)
            if per_v is None:
                continue
            # [eF, eP, eD, eM, eS, ...]
            if bool(per_v[0]) or bool(per_v[1]) or bool(per_v[2]) or bool(per_v[3]) or bool(per_v[4]):
                return True
    return False


def imprimir_mapa_conocimiento_qm(
    world: dict[str, object],
    kb: dict[str, object],
    per: list[bool] | None,
    p_umbral: float = 0.20,
    ancho_celda: int = 6,
) -> None:
    """Imprime un mapa compacto con la notación `?`/`!`/`.` como en la Parte 1.

Notas:
    Este mapa NO sustituye a los mapas de probabilidad (que sí se piden en el PDF); es una vista compacta para tener una salida parecida a la Parte 1.
    Reglas de notación (estilo Parte 1):
     - '!' : muerte segura (P(muerte)=1).
     - '?' : riesgo no nulo (0 < P(muerte) <= p_umbral).
     - '.' : celda no visitada sin evidencia de estímulos alrededor (aún no hay señales concluyentes).
     - '*' : celda no permitida para planificar (riesgo alto y no visitada).
     - 'v' : celda visitada.
     - 'CW'/'CWK' : capitán (con o sin Kurtz).

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    per (list[bool] | None): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.
    ancho_celda (int): Ancho (en caracteres) usado para cada celda del mapa impreso.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    n = int(world["n"])
    agent: Pos = world["agent"]
    visited: set[Pos] = kb["visited"]

    rm = riesgo_muerte(kb, world)

    p1.print_section("Mapa de conocimiento (notación tipo Parte 1)")
    print("Leyenda:")
    print("  ! : muerte segura (P=1)")
    print(f"  ? : riesgo bajo/moderado (0 < P <= p={p_umbral:.2f})")
    print(f"  . : NO segura (P > p={p_umbral:.2f}) y sin evidencia de estímulos alrededor")
    print("  v : visitada")
    print("  ✓ : segura (P=0)")
    print("  S : salida descubierta")
    print("  CW / CWK : capitán (sin / con Kurtz)")
    print("")

    cabecera = "     "
    c = 1
    while c <= n:
        cabecera = cabecera + _celda_prob(f"{c:>2d}", ancho_celda, tag="*")
        c += 1
    print(cabecera)
    print("     " + "-" * (ancho_celda * n))

    for r in range(1, n + 1):
        fila = []
        for c in range(1, n + 1):
            p = (r, c)
            if p == agent:
                fila.append(_celda_prob(_etiqueta_cw(world, per), ancho_celda, tag="CW"))
                continue
            if (world.get("exit_known") is not None) and (p == world["exit_known"]):
                fila.append(_celda_prob("S", ancho_celda, tag="S"))
                continue
            if p in visited:
                fila.append(_celda_prob("v", ancho_celda, tag="v"))
                continue

            prob = float(rm.get(p, 0.0))
            if prob >= 0.999999:
                fila.append(_celda_prob("!", ancho_celda, valor=prob))
            elif prob <= 0.0:
                # celda segura según el conocimiento actual (riesgo 0)
                fila.append(_celda_prob("✓", ancho_celda, valor=prob, tag="✓"))
            elif prob > p_umbral and (not hay_evidencia_estimulos_alrededor(kb, p)):
                fila.append(_celda_prob(".", ancho_celda, valor=prob))
            else:
                fila.append(_celda_prob("?", ancho_celda, valor=prob))

        s_fila = ""
        k = 0
        while k < len(fila):
            s_fila = s_fila + fila[k]
            k += 1
        print(f"{r:>3d} | " + s_fila)
    print("\n")
def imprimir_mapa_riesgo_coloreado(
    world: dict[str, object],
    kb: dict[str, object],
    per: list[bool] | None,
    p_umbral: float,
    ancho_celda: int = 6,
) -> None:
    """Mapa compacto de decisión: riesgo de muerte (coloreado) + marcas útiles.

Notas:
    Este mapa es el más visual, así que conviene que sea *el último que sale* en cada turno.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    per (list[bool] | None): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.
    ancho_celda (int): Ancho (en caracteres) usado para cada celda del mapa impreso.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    n = int(world["n"])
    agent: Pos = world["agent"]
    visited: set[Pos] = kb["visited"]

    rm = riesgo_muerte(kb, world)

    p1.print_section("Mapa de riesgo (para decidir movimientos)")
    print("Leyenda rápida:")
    print("  F/P/D: tipos de trampa | M: militar | S: salida")
    print("  CW / CWK : capitán (sin / con Kurtz)")
    print("  v        : celda ya visitada")
    print(f"  Colores: riesgo de muerte (permitida si riesgo < p = {p_umbral:.2f})")
    print("          <=0.05 gris | <=0.20 azul | <=0.40 cian | <=0.60 amarillo | >0.60 rojo")
    print("")

    cabecera = "     "
    c = 1
    while c <= n:
        cabecera = cabecera + _celda_prob(f"{c:>2d}", ancho_celda, tag="*")
        c += 1
    print(cabecera)
    print("     " + "-" * (ancho_celda * n))

    for r in range(1, n + 1):
        fila = []
        for c in range(1, n + 1):
            p = (r, c)
            if p == agent:
                fila.append(_celda_prob(_etiqueta_cw(world, per), ancho_celda, tag="CW"))
            elif (world.get("exit_known") is not None) and (p == world["exit_known"]):
                fila.append(_celda_prob("S", ancho_celda, tag="S"))
            elif p in visited:
                fila.append(_celda_prob("v", ancho_celda, tag="v"))
            else:
                v = float(rm.get(p, 0.0))
                fila.append(_celda_prob(f"{v:.2f}", ancho_celda, valor=v))
        s_fila = ""
        k = 0
        while k < len(fila):
            s_fila = s_fila + fila[k]
            k += 1
        print(f"{r:>3d} | " + s_fila)
    print("")


def _resumen_candidatos(dist: dict[Pos, float], max_items: int = 12) -> tuple[int, list[Pos]]:
    """Devuelve (n_candidatos, lista_acotada) de celdas con probabilidad > 0.

Args:
    dist (dict[Pos, float]): Distribución discreta {celda: probabilidad}.
    max_items (int): Máximo de elementos a devolver/mostrar en el resumen.

Returns:
    tuple[int, list[Pos]]: Par (n_candidatos, lista_acotada) con las celdas que tienen probabilidad > 0.
    """
    cands = [p for (p, v) in dist.items() if float(v) > 0.0]
    cands.sort()
    return len(cands), cands[:max_items]


def imprimir_resumen_bayes(world: dict[str, object], kb: dict[str, object], per: list[bool]) -> None:
    """Resumen de estado + percepto + tamaños de soporte (útil para el PDF).

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    per (list[bool]): Percepto como lista de booleanos en el orden [eF, eP, eD, eM, eS, Pared↑, Pared↓, Pared←, Pared→, Grito].

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    pos: Pos = world["agent"]

    print("Estado del agente:")
    print(f"  Posición: {pos}")
    print(f"  Vivo: {'sí' if bool(world['alive']) else 'no'}")
    print(f"  Kurtz rescatado: {'sí' if bool(world['kurtz_found']) else 'no'}")
    print(f"  Granada disponible: {'sí' if bool(world['grenade']) else 'no'}")
    print(f"  Soldado vivo: {'sí' if bool(world['soldier_alive']) else 'no'}")
    if world.get("exit_known") is not None:
        print(f"  Salida descubierta en: {world['exit_known']}")

    print(format_percept_bayes(per))

    # Orden similar a Parte 1: primero trampas, luego soldado, luego salida.
    nF, listaF = _resumen_candidatos(kb["posterior_F"], max_items=8)
    nP, listaP = _resumen_candidatos(kb["posterior_P"], max_items=8)
    nD, listaD = _resumen_candidatos(kb["posterior_D"], max_items=8)
    print("Trampas compatibles (celdas con probabilidad > 0):")
    print(f"  F: {nF}  (ej.: {listaF}{' ...' if nF > len(listaF) else ''})")
    print(f"  P: {nP}  (ej.: {listaP}{' ...' if nP > len(listaP) else ''})")
    print(f"  D: {nD}  (ej.: {listaD}{' ...' if nD > len(listaD) else ''})")

    nM, listaM = _resumen_candidatos(kb["posterior_M"])
    print(f"Militar (M) (Hay {nM} candidatos): {listaM if nM else '—'}{' ...' if nM > len(listaM) else ''}")

    nS, listaS = _resumen_candidatos(kb["posterior_S"])
    print(f"Salida (S) (Hay {nS} candidatos): {listaS if nS else '—'}{' ...' if nS > len(listaS) else ''}")

    if not bool(world["kurtz_found"]):
        nCK, listaCK = _resumen_candidatos(kb["posterior_CK"])
        print(f"Kurtz (CK) (Hay {nCK} candidatos): {listaCK if nCK else '—'}{' ...' if nCK > len(listaCK) else ''}")
    else:
        print("Kurtz (CK): rescatado (va con CWK)")


# -----------------------------------------------------------------------------
# Acciones del juego
# -----------------------------------------------------------------------------


def accion_mover(world: dict[str, object], direccion: str) -> None:
    """Mueve al capitán si la acción es válida; si choca con pared, se queda.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    direccion (str): Dirección de movimiento o lanzamiento: 'U', 'D', 'L' o 'R'.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    n = int(world["n"])
    pos: Pos = world["agent"]
    nxt = p1.mover_posicion(pos, direccion)
    if not p1.esta_en_tablero(n, nxt):
        nxt = pos
    world["agent"] = nxt
    comprobar_muerte_y_eventos(world)


def accion_granada(world: dict[str, object], direccion: str) -> None:
    """Lanza la granada a la celda contigua en la dirección indicada.

Notas:
    Si el soldado está en la celda objetivo, la granada lo elimina y se marca el percepto transitorio 'Grito'.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    direccion (str): Dirección de movimiento o lanzamiento: 'U', 'D', 'L' o 'R'.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    if not bool(world["grenade"]):
        return

    n = int(world["n"])
    pos: Pos = world["agent"]
    target = p1.mover_posicion(pos, direccion)

    world["grenade"] = False

    if not p1.esta_en_tablero(n, target):
        return

    if bool(world["soldier_alive"]) and (target == world["soldier"]):
        world["soldier_alive"] = False
        world["last_scream"] = True


def accion_salir(world: dict[str, object]) -> bool:
    """Intenta salir del palacio.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.

Returns:
    bool: True si la misión se completa (se está en la salida real y Kurtz ya fue rescatado).
    """
    if not bool(world["kurtz_found"]):
        return False
    return world["agent"] == world["exit"]


# -----------------------------------------------------------------------------
# Planificación (BFS/DFS/GBFS/A*) con traza estilo Parte 1
# -----------------------------------------------------------------------------


def _valor_traza(metodo: str, g: int, h: int) -> int:
    """Calcula el valor mostrado en la traza según el método de búsqueda.

Args:
    metodo (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    g (int): Coste acumulado (profundidad/coste desde el origen).
    h (int): Heurística h (distancia Manhattan al objetivo).

Returns:
    int: Entero calculado por la función.
    """
    if metodo == "gbfs":
        return h
    if metodo == "astar":
        return g + h
    return g


def _snapshot_frontera_simple(
    metodo: str,
    frontera_bfsdfs: list[Pos],
    heap: list[tuple[int, int, Pos, int]],
    cerrados: set[Pos],
    removed: tuple[Pos, int],
    g_cost: dict[Pos, int],
) -> list[tuple[Pos, int]]:
    """Snapshot de frontera para traza (incluye el extraído al principio).

Args:
    metodo (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    frontera_bfsdfs (list[Pos]): Frontera (cola/pila) usada en BFS/DFS durante la planificación.
    heap (list[tuple[int, int, Pos, int]]): Cola de prioridad usada en GBFS/A* durante la planificación.
    cerrados (set[Pos]): Conjunto de nodos cerrados/ya expandidos en la búsqueda.
    removed (tuple[Pos, int]): Nodo extraído de la frontera en el paso actual (con su valor de traza).
    g_cost (dict[Pos, int]): Coste acumulado g por celda.

Returns:
    list[tuple[Pos, int]]: Resultado de la operación.
    """
    out: list[tuple[Pos, int]] = [removed]
    seen: set[Pos] = {removed[0]}

    if metodo in ("bfs", "dfs"):
        for p in frontera_bfsdfs:
            if p in cerrados or p in seen:
                continue
            gv = int(g_cost.get(p, 0))
            out.append((p, gv))
            seen.add(p)
    else:
        for prio, tie, p, g in sorted(heap):
            if p in cerrados or p in seen:
                continue
            out.append((p, int(prio)))
            seen.add(p)

    return out


def planificar_camino_trazado(
    n: int,
    origen: Pos,
    destino: Pos,
    permitidas: set[Pos],
    metodo: str,
    trazar: bool = False,
    nombre_fase: str = "",
    collector: list[str] | None = None,
) -> list[str] | None:
    """Planifica un camino y devuelve una lista de acciones ('U','D','L','R').

Notas:
    Si 'trazar' es True, imprime (o acumula) el razonamiento en el formato: Step | Frontier | Removed | Explored.

Args:
    n (int): Tamaño del tablero (n×n).
    origen (Pos): Celda origen (fila, columna) 1-indexada.
    destino (Pos): Celda destino (fila, columna) 1-indexada.
    permitidas (set[Pos]): Conjunto de celdas por las que se permite planificar (seguras/visitadas según el umbral).
    metodo (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    trazar (bool): Si True, imprime (o recoge) la traza de la búsqueda en formato tabla.
    nombre_fase (str): Nombre de la fase para etiquetas en trazas/mensajes (p.ej., 'Kurtz', 'Salida').
    collector (list[str] | None): Lista opcional donde se acumulan líneas de traza (en vez de imprimir).

Returns:
    list[str] | None: Plan como lista de acciones ('U','D','L','R' y/o 'G*'). Devuelve None si no se encuentra un plan válido.

Raises:
    ValueError: Si algún parámetro es inválido (por ejemplo, un destino fuera del tablero o un método desconocido).
    """
    if origen == destino:
        return []

    if metodo not in ("bfs", "dfs", "gbfs", "astar"):
        raise ValueError("Método inválido. Usa bfs/dfs/gbfs/gbfs/astar.")

    def _emit(line: str) -> None:
        """Emite una línea de traza si la planificación está en modo trazado.

        Args:
            line (str): Línea ya formateada a imprimir/registrar.

        Returns:
            None: No devuelve nada; imprime y opcionalmente añade al collector.
        """
        if not trazar:
            return
        print(line)
        if collector is not None:
            collector.append(line)

    if trazar:
        if nombre_fase:
            _emit(f"\n=== PLANIFICACIÓN A {nombre_fase.upper()} ===")
        if metodo == "gbfs":
            _emit("Valor: h = distancia Manhattan al objetivo")
        elif metodo == "astar":
            _emit("Valor: f = g + h (coste + heurística)")
        else:
            _emit("Valor: g = profundidad (coste acumulado)")
        _emit("Step | Frontier | Removed | Explored")

    padre: dict[Pos, Pos] = {}
    g_cost: dict[Pos, int] = {origen: 0}
    cerrados: set[Pos] = set()

    exploradas_orden: list[tuple[Pos, int]] = []
    exploradas_set: set[Pos] = set()

    paso = 0

    frontera_bfsdfs: list[Pos] = []
    heap: list[tuple[int, int, Pos, int]] = []  # (prio, tie, pos, g)
    tie = 0

    if metodo in ("bfs", "dfs"):
        frontera_bfsdfs.append(origen)
    else:
        h0 = p1.distancia_manhattan(origen, destino)
        prio0 = _valor_traza(metodo, 0, h0)
        tie += 1
        heap.append((prio0, tie, origen, 0))

    while True:
        # 1) Extraer siguiente
        if metodo == "bfs":
            if not frontera_bfsdfs:
                return None
            u = frontera_bfsdfs.pop(0)
            gu = int(g_cost.get(u, 0))
            val_u = _valor_traza(metodo, gu, p1.distancia_manhattan(u, destino))
        elif metodo == "dfs":
            if not frontera_bfsdfs:
                return None
            u = frontera_bfsdfs.pop()
            gu = int(g_cost.get(u, 0))
            val_u = _valor_traza(metodo, gu, p1.distancia_manhattan(u, destino))
        else:
            if not heap:
                return None
            heap.sort()
            prio, _, u, gu = heap.pop(0)
            val_u = int(prio)

        if u in cerrados:
            continue

        # 2) Traza
        if trazar:
            if u not in exploradas_set:
                exploradas_set.add(u)
                exploradas_orden.append((u, val_u))

            snapshot = _snapshot_frontera_simple(
                metodo,
                frontera_bfsdfs,
                heap,
                cerrados,
                (u, val_u),
                g_cost,
            )

            frontier_s = p1.formatear_nodos_traza(snapshot)
            removed_s = p1.formatear_nodos_traza([(u, val_u)])
            explored_s = p1.formatear_nodos_traza(exploradas_orden)
            _emit(f"{paso:>4d} | {frontier_s} | {removed_s} | {explored_s}")
            paso += 1

        if u == destino:
            break

        cerrados.add(u)

        # 3) Expandir
        for d in p1.FRONTIER_DIR_ORDER:
            v = p1.mover_posicion(u, d)
            if not p1.esta_en_tablero(n, v):
                continue
            if v not in permitidas:
                continue
            if v in cerrados:
                continue

            gv = int(gu) + 1
            if (v not in g_cost) or (gv < g_cost[v]):
                g_cost[v] = gv
                padre[v] = u

                if metodo in ("bfs", "dfs"):
                    frontera_bfsdfs.append(v)
                else:
                    hv = p1.distancia_manhattan(v, destino)
                    prio_v = _valor_traza(metodo, gv, hv)
                    tie += 1
                    heap.append((prio_v, tie, v, gv))

    if destino not in padre:
        return None

    # Reconstrucción de acciones
    acciones_rev: list[str] = []
    cur = destino
    while cur != origen:
        prev = padre[cur]
        dr = cur[0] - prev[0]
        dc = cur[1] - prev[1]
        if dr == -1 and dc == 0:
            acciones_rev.append("U")
        elif dr == 1 and dc == 0:
            acciones_rev.append("D")
        elif dr == 0 and dc == -1:
            acciones_rev.append("L")
        elif dr == 0 and dc == 1:
            acciones_rev.append("R")
        else:
            return None
        cur = prev

    acciones_rev.reverse()
    return acciones_rev


# -----------------------------------------------------------------------------
# Elección de objetivos (automático)
# -----------------------------------------------------------------------------


def elegir_objetivo_exploracion(kb: dict[str, object], world: dict[str, object], permitidas: set[Pos]) -> Pos | None:
    """Celda permitida no visitada lo más cercana; empate por menor riesgo.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    permitidas (set[Pos]): Conjunto de celdas por las que se permite planificar (seguras/visitadas según el umbral).

Returns:
    Pos | None: Celda seleccionada/objetivo. Devuelve None si no hay una candidata válida.
    """
    visited: set[Pos] = kb["visited"]
    rm = riesgo_muerte(kb, world)
    pos: Pos = world["agent"]

    candidatos: list[tuple[int, float, Pos]] = []
    for p in permitidas:
        if p in visited:
            continue
        candidatos.append((p1.distancia_manhattan(pos, p), float(rm.get(p, 0.0)), p))

    if not candidatos:
        return None

    candidatos.sort(key=lambda x: (x[0], x[1], x[2][0], x[2][1]))
    return candidatos[0][2]


def elegir_objetivo_salida(kb: dict[str, object], world: dict[str, object], permitidas: set[Pos]) -> Pos | None:
    """Objetivo de salida: si ya la conocemos, ir ahí; si no, ir al MAP dentro de permitidas.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    permitidas (set[Pos]): Conjunto de celdas por las que se permite planificar (seguras/visitadas según el umbral).

Returns:
    Pos | None: Celda seleccionada/objetivo. Devuelve None si no hay una candidata válida.
    """
    if world.get("exit_known") is not None:
        return world["exit_known"]

    distS: dict[Pos, float] = kb["posterior_S"]
    best_pos: Pos | None = None
    best_p = -1.0
    for p in permitidas:
        v = float(distS.get(p, 0.0))
        if v > best_p:
            best_p = v
            best_pos = p

    return best_pos


def decidir_granada_si_conveniente(world: dict[str, object], kb: dict[str, object]) -> str | None:
    """Lanza granada solo si el soldado está adyacente y prácticamente seguro (MAP ~ 1).

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    str | None: Dirección ('U','D','L','R') o None si no procede.
    """
    if not bool(world["grenade"]) or (not bool(world["soldier_alive"])):
        return None

    pos: Pos = world["agent"]
    distM: dict[Pos, float] = kb["posterior_M"]

    # MAP del soldado
    best_cell = max(distM.items(), key=lambda it: float(it[1]))[0]
    best_prob = float(distM[best_cell])

    # Umbral alto para no malgastar la granada
    if best_prob < 0.99:
        return None
    if p1.distancia_manhattan(pos, best_cell) != 1:
        return None

    dr = best_cell[0] - pos[0]
    dc = best_cell[1] - pos[1]
    if dr == -1 and dc == 0:
        return "U"
    if dr == 1 and dc == 0:
        return "D"
    if dr == 0 and dc == -1:
        return "L"
    if dr == 0 and dc == 1:
        return "R"
    return None


# -----------------------------------------------------------------------------
# Modos de ejecución
# -----------------------------------------------------------------------------


def ejecutar_manual(world: dict[str, object], kb: dict[str, object], p_umbral: float) -> None:
    """Partida en modo manual.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    p1.print_section("Modo MANUAL")
    print("Controles:")
    print("  w/a/s/d  -> mover (arriba/izq/abajo/dcha)")
    print("  g        -> lanzar granada (1 uso)")
    print("  x        -> salir (solo si estás en S y llevas a Kurtz)")
    print("  t        -> terminar")

    while True:
        per = calcular_percepto_bayes(world)
        actualizar_kb_bayes(kb, world, per)

        imprimir_resumen_bayes(world, kb, per)
        mostrar_mapas_bayes(world, kb, per)
        imprimir_mapa_conocimiento_qm(world, kb, per, p_umbral=p_umbral)
        # Mapa más visual al final
        imprimir_mapa_riesgo_coloreado(world, kb, per, p_umbral=p_umbral)

        if not bool(world["alive"]):
            print("\nHas muerto. Fin.")
            return

        comando = input("\nComando (w/a/s/d mover, g granada, x salir, t terminar)> ").strip().lower()

        if comando == "t":
            print("Partida terminada por el usuario.")
            return

        if comando == "x":
            if accion_salir(world):
                print("\nMisión completada. Has salido con Kurtz.")
                return
            print("No estás en la salida (o aún no has encontrado a Kurtz).")
            continue

        if comando == "g":
            if not bool(world["grenade"]):
                print("No te queda granada.")
                continue
            tecla_dir = input("Dirección granada (w=arriba, a=izq, s=abajo, d=dcha)> ").strip().lower()
            if tecla_dir not in p1.KEY_TO_DIR:
                print("Dirección inválida.")
                continue
            accion_granada(world, p1.KEY_TO_DIR[tecla_dir])
            continue

        if comando in p1.KEY_TO_DIR:
            accion_mover(world, p1.KEY_TO_DIR[comando])
            continue

        print("Comando inválido.")


def imprimir_resumen_auto(acciones: list[str], posiciones: list[Pos]) -> None:
    """Resumen final del modo automático.

Args:
    acciones (list[str]): Lista de acciones ejecutadas o planificadas.
    posiciones (list[Pos]): Lista de posiciones visitadas durante la ejecución.

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    p1.print_section("Resumen automático")
    acciones_txt = _concat_con_sep(acciones, " ") if acciones else "—"
    print(f"Acciones ejecutadas ({len(acciones)}): {acciones_txt}")
    print(f"Posiciones recorridas ({len(posiciones)}): {posiciones if posiciones else '—'}")


# -----------------------------------------------------------------------------
# Automático "planifica TODO" (estilo Kurtz, pero con umbral probabilístico p)
# -----------------------------------------------------------------------------

def _clonar_kb_bayes(kb: dict[str, object]) -> dict[str, object]:
    """Copia estructural de la KB (sin imports).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).

Returns:
    dict[str, object]: Copia independiente (para planificación/simulación sin tocar el estado real).
    """
    out: dict[str, object] = {}
    out["n"] = int(kb["n"])
    out["start"] = kb["start"]
    out["visited"] = set(kb["visited"])
    out["obs"] = dict(kb.get("obs", {}))
    # Posteriors (dict Pos->float)
    out["posterior_F"] = dict(kb["posterior_F"])
    out["posterior_P"] = dict(kb["posterior_P"])
    out["posterior_D"] = dict(kb["posterior_D"])
    out["posterior_M"] = dict(kb["posterior_M"])
    out["posterior_S"] = dict(kb["posterior_S"])
    out["posterior_CK"] = dict(kb["posterior_CK"])
    return out


def _clonar_mundo_plan(world: dict[str, object]) -> dict[str, object]:
    """Copia del mundo suficiente para simular (sin tocar el mundo real).

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.

Returns:
    dict[str, object]: Copia independiente (para planificación/simulación sin tocar el estado real).
    """
    return {
        "n": int(world["n"]),
        "start": world["start"],
        "agent": world["agent"],
        "alive": bool(world["alive"]),
        "kurtz_found": bool(world["kurtz_found"]),
        "grenade": bool(world["grenade"]),
        "soldier_alive": bool(world["soldier_alive"]),
        "last_scream": bool(world.get("last_scream", False)),
        "exit_seen": bool(world.get("exit_seen", False)),
        "exit_known": world.get("exit_known", None),
        # mapa real (solo lectura)
        "traps": world["traps"],
        "soldier": world["soldier"],
        "exit": world["exit"],
        "kurtz": world["kurtz"],
    }


def _direccion_hacia(origen: Pos, destino: Pos) -> str | None:
    """Devuelve U/D/L/R si `destino` es vecino ortogonal de `origen`.

Args:
    origen (Pos): Celda origen (fila, columna) 1-indexada.
    destino (Pos): Celda destino (fila, columna) 1-indexada.

Returns:
    str | None: Dirección ('U','D','L','R') o None si no procede.
    """
    dr = destino[0] - origen[0]
    dc = destino[1] - origen[1]
    if dr == -1 and dc == 0:
        return "U"
    if dr == 1 and dc == 0:
        return "D"
    if dr == 0 and dc == -1:
        return "L"
    if dr == 0 and dc == 1:
        return "R"
    return None


def _pos_soldado_casi_segura(kb: dict[str, object], umbral: float = 0.99) -> Pos | None:
    """Devuelve la posición MAP del soldado si su probabilidad es muy alta.

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    umbral (float): Probabilidad mínima para considerar una hipótesis como 'casi segura'.

Returns:
    Pos | None: Celda seleccionada/objetivo. Devuelve None si no hay una candidata válida.
    """
    distM: dict[Pos, float] = kb["posterior_M"]
    if not distM:
        return None
    best_cell = max(distM.items(), key=lambda it: float(it[1]))[0]
    if float(distM.get(best_cell, 0.0)) >= float(umbral):
        return best_cell
    return None


def _frontera_de_permitidas(n: int, permitidas: set[Pos]) -> set[Pos]:
    """Celdas no permitidas adyacentes a alguna permitida.

Args:
    n (int): Tamaño del tablero (n×n).
    permitidas (set[Pos]): Conjunto de celdas por las que se permite planificar (seguras/visitadas según el umbral).

Returns:
    set[Pos]: Conjunto de celdas (fila, columna) 1-indexadas.
    """
    out: set[Pos] = set()
    for u in permitidas:
        for v in p1.vecinos_ortogonales(n, u):
            if v not in permitidas:
                out.add(v)
    return out


def _mejor_para_forzar(
    kb: dict[str, object],
    world: dict[str, object],
    permitidas: set[Pos],
    ya_forzadas: set[Pos],
) -> tuple[Pos | None, float]:
    """Elige una celda candidata a 'forzar' (arriesgar) minimizando P(muerte).

Args:
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    permitidas (set[Pos]): Conjunto de celdas por las que se permite planificar (seguras/visitadas según el umbral).
    ya_forzadas (set[Pos]): Conjunto de celdas ya forzadas previamente para no repetir intentos.

Returns:
    tuple[Pos | None, float]: Resultado de la operación o None si no se puede determinar.
    """
    n = int(world["n"])
    rm = riesgo_muerte(kb, world)

    # Preferimos frontera (expansión incremental). Si no hay, miramos todo el dominio.
    candidatos = _frontera_de_permitidas(n, permitidas)
    if not candidatos:
        candidatos = set(rm.keys())

    mejor: Pos | None = None
    mejor_r = 2.0
    for p in candidatos:
        if p in permitidas or p in ya_forzadas:
            continue
        r = float(rm.get(p, 1.0))
        if r < mejor_r:
            mejor_r = r
            mejor = p
    return mejor, mejor_r


def _plan_con_granada(
    world: dict[str, object],
    kb: dict[str, object],
    destino: Pos,
    metodo_busqueda: str,
    p_umbral: float,
    forzadas: set[Pos],
    trazar: bool,
    nombre_fase: str,
    trazas: list[dict[str, object]],
) -> list[str] | None:
    """Intenta un plan 'ir a adyacente → granada → continuar' si el soldado es casi seguro.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    destino (Pos): Celda destino (fila, columna) 1-indexada.
    metodo_busqueda (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.
    forzadas (set[Pos]): Conjunto de celdas permitidas de forma excepcional (aunque superen el umbral).
    trazar (bool): Si True, imprime (o recoge) la traza de la búsqueda en formato tabla.
    nombre_fase (str): Nombre de la fase para etiquetas en trazas/mensajes (p.ej., 'Kurtz', 'Salida').
    trazas (list[dict[str, object]]): Lista donde se guardan las planificaciones internas (plan y traza) para depuración.

Returns:
    list[str] | None: Plan como lista de acciones ('U','D','L','R' y/o 'G*'). Devuelve None si no se encuentra un plan válido.
    """
    if (not bool(world["grenade"])) or (not bool(world["soldier_alive"])):
        return None

    soldado = _pos_soldado_casi_segura(kb, umbral=0.99)
    if soldado is None:
        return None

    n = int(world["n"])
    origen: Pos = world["agent"]

    # Permitidas con soldado vivo
    permitidas_vivo = set(celdas_permitidas(kb, world, p_umbral))
    permitidas_vivo.update(forzadas)

    mejores_acc: list[str] | None = None
    mejor_len = 10**9

    for adj in p1.vecinos_ortogonales(n, soldado):
        if not p1.esta_en_tablero(n, adj):
            continue
        if adj not in permitidas_vivo:
            continue

        tr1: list[str] = []
        plan1 = planificar_camino_trazado(
            n,
            origen,
            adj,
            permitidas_vivo,
            metodo_busqueda,
            trazar=bool(trazar),
            nombre_fase=f"{nombre_fase} (hasta adyacente a M)",
            collector=tr1,
        )
        if plan1 is None:
            continue

        dirg = _direccion_hacia(adj, soldado)
        if dirg is None:
            continue

        # Simular mundo con soldado muerto para la segunda fase del plan
        world2 = _clonar_mundo_plan(world)
        world2["agent"] = adj
        world2["grenade"] = False
        world2["soldier_alive"] = False

        permitidas_muerto = set(celdas_permitidas(kb, world2, p_umbral))
        permitidas_muerto.update(forzadas)
        # Tras granada, no necesitamos 'exit_known' para permitir el destino; lo gestiona la capa superior.

        tr2: list[str] = []
        plan2 = planificar_camino_trazado(
            n,
            adj,
            destino,
            permitidas_muerto,
            metodo_busqueda,
            trazar=bool(trazar),
            nombre_fase=f"{nombre_fase} (tras granada)",
            collector=tr2,
        )
        if plan2 is None:
            continue

        acc_total = list(plan1) + ["G" + dirg] + list(plan2)
        if len(acc_total) < mejor_len:
            mejor_len = len(acc_total)
            mejores_acc = acc_total

            # Guardar trazas explicativas (solo la mejor combinación)
            trazas.append(
                {
                    "fase": nombre_fase,
                    "metodo": metodo_busqueda,
                    "origen": origen,
                    "destino": destino,
                    "plan": list(acc_total),
                    "traza": tr1 + tr2,
                    "nota": "Plan con granada (soldado casi seguro)",
                }
            )

    return mejores_acc


def planificar_ruta_umbral(
    world: dict[str, object],
    kb: dict[str, object],
    destino: Pos,
    metodo_busqueda: str,
    p_umbral: float,
    trazar: bool = True,
    nombre_fase: str = "",
    trazas: list[dict[str, object]] | None = None,
) -> list[str] | None:
    """Planifica un camino completo con celdas 'seguras' definidas por P(muerte) < p_umbral.

Notas:
    Si no existe ruta usando solo celdas con riesgo < p_umbral, propone permitir una celda adicional de menor riesgo y pregunta confirmación al usuario.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    destino (Pos): Celda destino (fila, columna) 1-indexada.
    metodo_busqueda (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.
    trazar (bool): Si True, imprime (o recoge) la traza de la búsqueda en formato tabla.
    nombre_fase (str): Nombre de la fase para etiquetas en trazas/mensajes (p.ej., 'Kurtz', 'Salida').
    trazas (list[dict[str, object]] | None): Lista donde se guardan las planificaciones internas (plan y traza) para depuración.

Returns:
    list[str] | None: Plan como lista de acciones ('U','D','L','R' y/o 'G*'). Devuelve None si no se encuentra un plan válido.
    """
    if trazas is None:
        trazas = []

    n = int(world["n"])
    origen: Pos = world["agent"]

    if origen == destino:
        return []

    forzadas: set[Pos] = set()
    intentos = 0

    while True:
        intentos += 1
        permitidas = set(celdas_permitidas(kb, world, p_umbral))
        permitidas.update(forzadas)

        # Permitimos el objetivo si ya es visitado/seguro o si el usuario lo fuerza.
        if destino in forzadas:
            permitidas.add(destino)

        traza_plan: list[str] = []
        plan = planificar_camino_trazado(
            n,
            origen,
            destino,
            permitidas,
            metodo_busqueda,
            trazar=bool(trazar),
            nombre_fase=nombre_fase,
            collector=traza_plan,
        )

        if plan is not None:
            trazas.append(
                {
                    "fase": nombre_fase,
                    "metodo": metodo_busqueda,
                    "origen": origen,
                    "destino": destino,
                    "plan": list(plan),
                    "traza": traza_plan,
                    "intento": intentos,
                }
            )
            return list(plan)

        # Antes de pedir riesgo, intentamos desbloquear con granada si procede
        plan_g = _plan_con_granada(
            world,
            kb,
            destino,
            metodo_busqueda,
            p_umbral,
            forzadas,
            trazar,
            nombre_fase,
            trazas,
        )
        if plan_g is not None:
            return plan_g

        # No hay ruta: elegir mejor celda para forzar
        cand, r = _mejor_para_forzar(kb, world, permitidas, forzadas)
        if cand is None:
            return None

        # Notificar y preguntar
        print(
            f"[Auto:{nombre_fase}] No hay ruta usando solo celdas con P(muerte) < {p_umbral:.2f}. "
            f"La opción menos peligrosa para expandir es {cand} con P(muerte)≈{r:.3f}."
        )
        resp = input("¿Quieres permitir expandir esa celda (arriesgar)? (s/n) > ").strip().lower()
        if resp not in ("s", "si", "sí", "y", "yes"):
            return None

        forzadas.add(cand)
        # Si el destino es precisamente esa, lo forzamos también
        if cand == destino:
            forzadas.add(destino)


def planificar_mision_completa(
    world: dict[str, object],
    kb: dict[str, object],
    metodo_busqueda: str,
    p_umbral: float,
    trazar_plan: bool = True,
) -> tuple[list[str] | None, list[dict[str, object]]]:
    """Planifica TODA la misión (Kurtz → Salida) antes de ejecutar.

Notas:
    Planifica primero hasta Kurtz y luego hasta la salida. Para que la segunda fase use información coherente, simula en un clon la ejecución del primer plan y actualiza la KB clonada con los perceptos obtenidos.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    metodo_busqueda (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.
    trazar_plan (bool): Si True, imprime las planificaciones internas con su traza.

Returns:
    tuple[list[str] | None, list[dict[str, object]]]: Resultado de la operación o None si no se puede determinar.
    """
    trazas: list[dict[str, object]] = []

    world_p = _clonar_mundo_plan(world)
    kb_p = _clonar_kb_bayes(kb)

    # Percepción inicial (en la celda de inicio) para que la planificación tenga una KB coherente
    per0 = calcular_percepto_bayes(world_p)
    actualizar_kb_bayes(kb_p, world_p, per0)

    kurtz_real: Pos = world_p["kurtz"]
    exit_real: Pos = world_p["exit"]

    # 1) Plan a Kurtz
    plan1 = planificar_ruta_umbral(
        world_p,
        kb_p,
        kurtz_real,
        metodo_busqueda,
        p_umbral,
        trazar=bool(trazar_plan),
        nombre_fase="Kurtz",
        trazas=trazas,
    )
    if plan1 is None:
        return None, trazas

    # Simular (sin replantear) para acumular perceptos
    for act in plan1:
        if act.startswith("G"):
            accion_granada(world_p, act[1])
        else:
            accion_mover(world_p, act)

        per = calcular_percepto_bayes(world_p)
        actualizar_kb_bayes(kb_p, world_p, per)

        if not bool(world_p["alive"]):
            # Si muere aquí, no tiene sentido seguir planificando.
            break

    if not bool(world_p["alive"]):
        return list(plan1), trazas

    # 2) Plan a salida (reinicio implícito de frontera/explorados al llamar de nuevo al planificador)
    plan2 = planificar_ruta_umbral(
        world_p,
        kb_p,
        exit_real,
        metodo_busqueda,
        p_umbral,
        trazar=bool(trazar_plan),
        nombre_fase="Salida",
        trazas=trazas,
    )
    if plan2 is None:
        return None, trazas

    plan_total = list(plan1) + list(plan2) + ["X"]
    return plan_total, trazas

def ejecutar_auto(
    world: dict[str, object],
    kb: dict[str, object],
    metodo_busqueda: str,
    p_umbral: float = 0.20,
    max_pasos: int = 500,
    verbose: bool = True,
    trazar_plan: bool = True,
) -> dict[str, object]:
    """Modo automático (planifica todo y luego ejecuta).

Notas:
    El automático primero construye el plan completo (Kurtz → Salida) y después ejecuta la secuencia resultante. Puede insertar una acción de granada cuando el soldado es casi seguro y la granada está disponible.

Args:
    world (dict[str, object]): Diccionario con el mundo real oculto y el estado del episodio.
    kb (dict[str, object]): Base de conocimiento Bayesiana (posteriors, visitadas y observaciones).
    metodo_busqueda (str): Identificador del método de búsqueda ('bfs', 'dfs', 'gbfs', 'astar').
    p_umbral (float): Umbral de riesgo: una celda se considera planificable si P(muerte) < p_umbral.
    max_pasos (int): Límite de pasos para evitar bucles en la ejecución automática.
    verbose (bool): Si True, muestra salida detallada durante el modo automático.
    trazar_plan (bool): Si True, imprime las planificaciones internas con su traza.

Returns:
    dict[str, object]: Resumen de la ejecución automática (acciones, posiciones y trazas internas).
    """
    p1.print_section("Modo AUTOMÁTICO")
    print(f"Umbral de riesgo p = {p_umbral:.2f} (seguro si P(muerte) < p)")

    acciones: list[str] = []
    posiciones: list[Pos] = [world["agent"]]
    trazas: list[dict[str, object]] = []

    # 1) Planificar TODO antes de mover
    plan_total, trazas_plan = planificar_mision_completa(
        world=world,
        kb=kb,
        metodo_busqueda=metodo_busqueda,
        p_umbral=p_umbral,
        trazar_plan=bool(trazar_plan),
    )
    trazas.extend(trazas_plan)

    if plan_total is None:
        print("[Auto] No se ha podido construir un plan completo con el umbral dado.")
        imprimir_resumen_auto(acciones, posiciones)
        print(f"Planificaciones internas: {len(trazas)}")
        return {"acciones": acciones, "posiciones": posiciones, "trazas": trazas}

    if verbose:
        plan_txt = _concat_con_sep(plan_total, " ") if plan_total else "—"
        print(f"[Auto] Plan completo calculado ({len(plan_total)} acciones): {plan_txt}")

    # 2) Ejecutar el plan SIN replantear (máximo `max_pasos` por seguridad)
    for i, act in enumerate(plan_total[: int(max_pasos)]):
        if not bool(world["alive"]):
            print("\n[Auto] El agente ha muerto. Fin.")
            break

        # Percibir y actualizar (informativo; no afecta a decisiones porque no se replantea)
        per = calcular_percepto_bayes(world)
        actualizar_kb_bayes(kb, world, per)

        if verbose:
            imprimir_resumen_bayes(world, kb, per)
            mostrar_mapas_bayes(world, kb, per)
            imprimir_mapa_conocimiento_qm(world, kb, per, p_umbral=p_umbral)
            imprimir_mapa_riesgo_coloreado(world, kb, per, p_umbral=p_umbral)

        if act == "X":
            ok = accion_salir(world)
            acciones.append("X")
            posiciones.append(world["agent"])
            if ok:
                print("\n[Auto] ¡Misión completada! (acción 'x' en la salida con Kurtz)")
            else:
                print("\n[Auto] Se intentó salir ('x'), pero no era válido en este estado.")
            break

        if act.startswith("G"):
            dirg = act[1] if len(act) > 1 else ""
            if dirg not in ("U", "D", "L", "R"):
                print(f"[Auto] Acción de granada inválida en el plan: {act!r}. Abortando.")
                break
            accion_granada(world, dirg)
            acciones.append("G" + dirg)
            posiciones.append(world["agent"])
            continue

        # Movimiento
        if act not in ("U", "D", "L", "R"):
            print(f"[Auto] Acción inválida en el plan: {act!r}. Abortando.")
            break

        acciones.append(act)
        accion_mover(world, act)
        posiciones.append(world["agent"])

    imprimir_resumen_auto(acciones, posiciones)
    print(f"Planificaciones internas: {len(trazas)}")
    return {"acciones": acciones, "posiciones": posiciones, "trazas": trazas}



# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main() -> None:
    """Punto de entrada del programa.

Args:
    (sin parámetros)

Returns:
    None: No devuelve nada; su efecto es actualizar estructuras y/o imprimir por pantalla.
    """
    p1.print_banner("PROYECTO FIA: BUSCANDO AL CORONEL KURTZ (PARTE 2 - BAYES)")

    modo = p1.pedir_opcion("¿Modo de juego? [manual/auto]: ", ["manual", "auto"])

    metodo_busqueda = "bfs"
    verbose = True
    trazar_plan = True

    if modo == "auto":
        metodo_busqueda = p1.pedir_opcion("Búsqueda [bfs/dfs/gbfs/astar]: ", ["bfs", "dfs", "gbfs", "astar"])
        verbose = not p1.pedir_si_no("¿Modo silencioso (menos prints)? [s/n] (por defecto n): ", por_defecto=False)
        trazar_plan = p1.pedir_si_no("¿Mostrar traza de planificación? [s/n] (por defecto s): ", por_defecto=True)

    usar_colores = p1.pedir_si_no("¿Usar colores en consola? [s/n] (por defecto s): ", por_defecto=True)
    p1.USE_COLOR = bool(usar_colores)

    seed = p1.pedir_semilla()
    if seed is not None:
        p1.random.seed(seed)

    # Umbral de riesgo del enunciado (p)
    p_umbral = 0.20
    entrada = input("Umbral de riesgo p (ENTER=0.20): ").strip()
    if entrada != "":
        try:
            p_umbral = float(entrada)
        except ValueError:
            print("Valor inválido; uso p=0.20.")

    world = crear_mundo_bayes(n=6, inicio=(1, 1))
    kb = crear_kb_bayes(int(world["n"]), world["start"])

    comprobar_muerte_y_eventos(world)

    if modo == "manual":
        ejecutar_manual(world, kb, p_umbral=p_umbral)
    else:
        ejecutar_auto(
            world,
            kb,
            metodo_busqueda=metodo_busqueda,
            p_umbral=p_umbral,
            max_pasos=500,
            verbose=verbose,
            trazar_plan=trazar_plan,
        )

if __name__ == "__main__":
    main()