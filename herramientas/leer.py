"""Convierte los dos reglamentos en una estructura común.

Documento = {"id", "titulo", "bloques": [...]}, donde cada bloque es
  {"tipo": "capitulo", "num", "titulo"}
  {"tipo": "articulo", "id": "5", "num": "5", "titulo", "partes": [...]}
  {"tipo": "disposicion", "id": "df1", "titulo", "partes": [...]}
y cada parte es
  {"id": "5.1", "etiqueta": "1.", "texto", "sub": [partes], "cola": "texto tras la lista"}

Los identificadores son los que se usan en la web: #art-5, #ap-5-1, etc.
"""
import re

LETRAS = "abcdefghijklmnopqrstuvwxyz"


# --------------------------------------------------------------------------
# Reglamento de 2015: texto extraído del PDF original (fuentes/reglamento_2015.txt)
# --------------------------------------------------------------------------
# Párrafos sin número que en el original van sueltos dentro de un artículo.
PARRAFOS_SUELTOS_2015 = (
    "El pleno de la delegación de estudiantes de la Facultad podrá acordar",
    "Se dará la publicidad adecuada a la convocatoria",
)


def _limpia(s):
    return re.sub(r"\s+", " ", s).strip()


def leer_2015(ruta):
    lineas = [l.replace(chr(160), " ").rstrip() for l in open(ruta, encoding="utf-8").read().splitlines()]
    doc = {"id": "antiguo", "titulo": "Reglamento de la Delegación de Alumnos de la Facultad de Ciencias",
           "subtitulo": "De la representación de los estudiantes y su organización", "bloques": []}
    art = None        # artículo o disposición en curso
    actual = None     # parte en curso (a la que se añade el texto que sigue)
    apartado = None   # parte de primer nivel en curso
    en_cola = False
    i = 0
    # Saltar la portada (tres primeras líneas con texto)
    while i < len(lineas) and not lineas[i].strip().startswith("CAPÍTULO"):
        i += 1
    while i < len(lineas):
        l = lineas[i].strip()
        i += 1
        if not l:
            continue
        if l.startswith("CAPÍTULO"):
            while not lineas[i].strip():
                i += 1
            doc["bloques"].append({"tipo": "capitulo", "num": _limpia(l), "titulo": _limpia(lineas[i])})
            i += 1
            art = actual = apartado = None
            en_cola = False
            continue
        m = re.match(r"^Art\. (\d+)\. (.*)$", l)
        if m:
            art = {"tipo": "articulo", "id": m.group(1), "num": m.group(1), "titulo": _limpia(m.group(2)), "partes": []}
            doc["bloques"].append(art)
            actual = apartado = None
            en_cola = False
            en_cola = False
            continue
        if l.startswith("Reforma del Presente Reglamento"):
            art = {"tipo": "disposicion", "id": "ref", "titulo": _limpia(l), "partes": []}
            doc["bloques"].append(art)
            actual = apartado = None
            en_cola = False
            continue
        m = re.match(r"^(\d+)\.\s+(.*)$", l)
        if m and art is not None and art["tipo"] == "articulo":
            apartado = {"id": f'{art["id"]}.{m.group(1)}', "etiqueta": m.group(1) + ".", "texto": m.group(2), "sub": []}
            art["partes"].append(apartado)
            actual = apartado
            en_cola = False
            continue
        m = re.match(r"^([a-n])\)\s*(.*)$", l)
        if m and art is not None:
            if apartado is None:  # artículo sin apartados numerados (art. 10)
                apartado = {"id": art["id"], "etiqueta": "", "texto": "", "sub": []}
                art["partes"].append(apartado)
            texto = m.group(2)
            if not texto:  # «i)» en una línea y el texto en la siguiente
                while not lineas[i].strip():
                    i += 1
                texto = lineas[i].strip()
                i += 1
            letra = {"id": f'{apartado["id"]}.{m.group(1)}', "etiqueta": m.group(1) + ")", "texto": texto, "sub": []}
            apartado["sub"].append(letra)
            actual = letra
            en_cola = False
            continue
        if l.startswith(PARRAFOS_SUELTOS_2015):
            apartado["cola"] = l
            en_cola = True
            continue
        if art is not None and art["id"] == "10" and apartado is None:
            apartado = {"id": "10", "etiqueta": "", "texto": l, "sub": []}
            art["partes"].append(apartado)
            actual = apartado
            continue
        if art is not None and art["tipo"] == "disposicion" and actual is None:
            actual = {"id": "ref", "etiqueta": "", "texto": l, "sub": []}
            art["partes"].append(actual)
            continue
        # continuación de la línea anterior
        if en_cola:
            apartado["cola"] += " " + l
        else:
            actual["texto"] += " " + l
    _normaliza(doc)
    return doc


def _normaliza(doc):
    def rec(p):
        p["texto"] = _limpia(p["texto"])
        if p.get("cola"):
            p["cola"] = _limpia(p["cola"])
        for s in p["sub"]:
            rec(s)
    for b in doc["bloques"]:
        for p in b.get("partes", []):
            rec(p)


# --------------------------------------------------------------------------
# Reglamento de 2026: fuente LaTeX (fuentes/reglamento_2026.tex)
# --------------------------------------------------------------------------
def tex_a_texto(s):
    s = s.replace("\\#", "#").replace("~", "\u00a0").replace("\\,", "\u202f")
    s = re.sub(r"\\(?:textbf|emph|textit)\{([^{}]*)\}", r"\1", s)
    s = s.replace("--", "–")
    s = s.replace("\\%", "%")
    assert "\\" not in s, s
    return _limpia(s)


def leer_2026(ruta):
    tex = open(ruta, encoding="utf-8").read()
    cuerpo = tex.split("\\tableofcontents", 1)[1].split("\\end{document}", 1)[0]
    doc = {"id": "nuevo", "titulo": "Reglamento del Consejo de Estudiantes de la Facultad de Ciencias",
           "subtitulo": "De la representación de los estudiantes y su organización", "bloques": []}
    numeros_disp = {"Disposición transitoria única": "dt", "Disposición derogatoria única": "dd",
                    "Disposición final primera": "df1", "Disposición final segunda": "df2",
                    "Disposición final tercera": "df3", "Anexo": "anexo"}
    art = None
    pila = []        # listas abiertas: [{"nivel", "partes"(lista destino), "padre"}]
    contador = {}    # contador del primer nivel por artículo (para [resume])
    ultima = None    # última parte creada
    ultimo_ap = None
    for linea in cuerpo.splitlines():
        l = linea.strip()
        if not l or l.startswith("%") or l in ("\\clearpage",) or l.startswith("\\vspace") or l.startswith("\\thispagestyle"):
            continue
        m = re.match(r"^\\capitulo\{(.*?)\}\{(.*)\}$", l)
        if m:
            doc["bloques"].append({"tipo": "capitulo", "num": m.group(1), "titulo": tex_a_texto(m.group(2))})
            continue
        m = re.match(r"^\\articulo\{(\d+)\}\{(.*)\}$", l)
        if m:
            art = {"tipo": "articulo", "id": m.group(1), "num": m.group(1), "titulo": tex_a_texto(m.group(2)), "partes": []}
            doc["bloques"].append(art)
            contador[art["id"]] = 0
            ultima = ultimo_ap = None
            continue
        m = re.match(r"^\\disposicion\{(.*)\}$", l)
        if m:
            titulo = tex_a_texto(m.group(1))
            clave = next(v for k, v in numeros_disp.items() if titulo.startswith(k))
            art = {"tipo": "disposicion", "id": clave, "titulo": titulo, "partes": []}
            doc["bloques"].append(art)
            ultima = ultimo_ap = None
            continue
        m = re.match(r"^\\begin\{(enumerate|ordinales)\}(\[resume\])?$", l)
        if m:
            nivel = len(pila) + 1
            if nivel == 1:
                destino = art["partes"]
                if not m.group(2):
                    contador[art["id"]] = 0
            else:
                destino = ultima["sub"]
            pila.append({"nivel": nivel, "tipo": m.group(1), "destino": destino, "padre": ultima, "n": 0})
            continue
        if re.match(r"^\\end\{(enumerate|ordinales)\}$", l):
            cerrada = pila.pop()
            ultima = cerrada["padre"] if pila else ultima
            continue
        if l.startswith("\\begin{center}") or l.startswith("\\end{center}"):
            continue
        m = re.match(r"^\\includegraphics\[[^\]]*\]\{(.*)\}$", l)
        if m:
            art["partes"][-1]["imagen"] = m.group(1).replace(".pdf", ".png")
            continue
        m = re.match(r"^\\item (.*)$", l)
        if m:
            nivel = len(pila)
            ctx = pila[-1]
            if nivel == 1:
                contador[art["id"]] += 1
                n = contador[art["id"]]
                parte = {"id": f'{art["id"]}.{n}', "etiqueta": f"{n}.", "texto": tex_a_texto(m.group(1)), "sub": []}
                ultimo_ap = parte
            else:
                ctx["n"] += 1
                padre = ctx["padre"]
                if ctx["tipo"] == "ordinales":
                    et, suf = f'{ctx["n"]}.º', str(ctx["n"])
                else:
                    et, suf = LETRAS[ctx["n"] - 1] + ")", LETRAS[ctx["n"] - 1]
                parte = {"id": f'{padre["id"]}.{suf}', "etiqueta": et, "texto": tex_a_texto(m.group(1)), "sub": []}
            ctx["destino"].append(parte)
            # los hijos de este item se crearán con padre = parte
            ultima = parte
            if nivel >= 2:
                pass
            continue
        # Texto fuera de listas
        texto = tex_a_texto(l)
        if pila:
            ultima["texto"] += " " + texto
        elif art["tipo"] == "disposicion":
            art["partes"].append({"id": f'{art["id"]}.{len(art["partes"]) + 1}', "etiqueta": "", "texto": texto, "sub": []})
        else:  # párrafo suelto tras una lista: cola del último apartado
            ultimo_ap["cola"] = (ultimo_ap.get("cola", "") + " " + texto).strip()
    # El padre de cada nivel debe ser el item del nivel superior: se corrige abajo
    _normaliza(doc)
    return doc
