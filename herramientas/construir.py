"""Genera los datos de la web y los fragmentos HTML para Drupal.

Uso: python herramientas/construir.py
Salida:
  datos/reglamentos.json   textos estructurados + índice de búsqueda (lo usan buscar/ y comparador/)
  datos/comparativa.json   fichas del comparador con el texto de cada celda ya resuelto
  drupal/*.html            cuerpos de las páginas /reglamento, /reglamento/nuevo, /reglamento/antiguo
                           y /reglamento/comparador (se pegan en el editor de Drupal)
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from leer import leer_2015, leer_2026  # noqa: E402
import comparativa as C  # noqa: E402

RAIZ = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
WEB = "https://cienzdel.unizar.es"
PAGES = "https://cienzdel.github.io/reglamento"
ARCHIVOS = "/sites/cienzdel/files/archivos"
PAGINA = {"nuevo": f"{WEB}/reglamento/nuevo", "antiguo": f"{WEB}/reglamento/antiguo"}
PDF = {
    "nuevo": f"{ARCHIVOS}/borrador_reglamento_consejo_estudiantes_2026_v2.pdf",
    "antiguo": f"{ARCHIVOS}/reglamento_delegacion_alumnos_2015.pdf",
    "antiguo_transcripcion": f"{ARCHIVOS}/reglamento_delegacion_alumnos_2015_transcripcion.pdf",
}


def ancla(id_):
    """Identificador de apartado -> id HTML. «5.6» -> ap-5-6; «df1.1» -> ap-df1-1."""
    return "ap-" + id_.replace(".", "-")


def ancla_bloque(b):
    return f"art-{b['id']}" if b["tipo"] == "articulo" else f"disp-{b['id']}"


def recorrer(partes, nivel=1):
    for p in partes:
        yield p, nivel
        yield from recorrer(p["sub"], nivel + 1)


def indexar(doc):
    """Mapa id -> (parte, bloque) y bloque por id de artículo."""
    partes, bloques = {}, {}
    for b in doc["bloques"]:
        if b["tipo"] == "capitulo":
            continue
        bloques[b["id"]] = b
        for p, _ in recorrer(b["partes"]):
            partes[p["id"]] = (p, b)
    return partes, bloques


def ref_legible(b, p=None):
    if b["tipo"] == "articulo":
        if p is None or p["id"] == b["id"]:
            return f"Art. {b['num']}"
        return "Art. " + p["id"].replace(".", ".", 1).rstrip()
    return b["titulo"].split(".")[0]


# ---------------------------------------------------------------------------
# Búsqueda
# ---------------------------------------------------------------------------
def texto_completo(p):
    trozos = [f"{p['etiqueta']} {p['texto']}".strip()]
    for s, _ in recorrer(p["sub"]):
        trozos.append(f"{s['etiqueta']} {s['texto']}")
    if p.get("cola"):
        trozos.append(p["cola"])
    return " ".join(trozos)


def entradas_busqueda(doc):
    out = []
    capitulo = ""
    for b in doc["bloques"]:
        if b["tipo"] == "capitulo":
            capitulo = f"{b['num'].title()}: {b['titulo']}"
            continue
        titulo = f"Art. {b['num']}. {b['titulo']}" if b["tipo"] == "articulo" else b["titulo"]
        for p in b["partes"]:
            ref = ref_legible(b, p) if p["etiqueta"] else titulo.split(".")[0] if b["tipo"] == "articulo" else b["titulo"].split(".")[0]
            if b["tipo"] == "articulo" and not p["etiqueta"]:
                ref = f"Art. {b['num']}"
            out.append({
                "doc": doc["id"], "ref": ref, "titulo": titulo, "capitulo": capitulo,
                "url": f"{PAGINA[doc['id']]}#{ancla(p['id'])}", "texto": texto_completo(p),
            })
    return out


# ---------------------------------------------------------------------------
# Comparador
# ---------------------------------------------------------------------------
def celda(doc_id, ids, idx):
    if ids is None:
        return None
    if isinstance(ids, str):
        ids = [ids]
    partes, bloques = idx
    segmentos, enlace, refs = [], None, []
    for i in ids:
        if i.startswith("art:"):
            b = bloques[i[4:]]
            lista = [(p, n) for p, n in recorrer(b["partes"])]
            enlace = enlace or f"{PAGINA[doc_id]}#{ancla_bloque(b)}"
            refs.append(f"Art. {b['num']}")
        else:
            solo_cabeza = i.endswith(":")
            pid = i.rstrip(":")
            p, b = partes[pid]
            nivel = pid.count(".") if b["tipo"] == "articulo" else 1
            nivel = max(nivel, 1)
            lista = [(p, nivel)] if solo_cabeza else [(q, nivel + n - 1) for q, n in recorrer([p])]
            enlace = enlace or f"{PAGINA[doc_id]}#{ancla(pid)}"
            refs.append(ref_legible(b, p) if b["tipo"] == "articulo" else b["titulo"].split(".")[0])
        for q, n in lista:
            segmentos.append({"e": q["etiqueta"], "t": q["texto"], "n": n})
            if q.get("cola") and not (i.endswith(":")):
                segmentos.append({"e": "", "t": q["cola"], "n": n})
    unicas = []
    for r in refs:  # «Art. 6.5» y «Art. 6.5.a» -> «Art. 6.5»
        if not any(r == u or r.startswith(u + ".") for u in unicas):
            unicas.append(r)
    return {"ref": " y ".join(unicas), "url": enlace, "seg": segmentos}


def comprobar_cobertura(antiguo_idx):
    """Todo apartado del texto de 2015 debe aparecer en alguna ficha."""
    usados = set()
    for f in C.FICHAS:
        for a, _ in f["filas"]:
            for i in ([a] if isinstance(a, str) else a or []):
                if i.startswith("art:"):
                    continue
                pid = i.rstrip(":")
                usados.add(pid)
                if not i.endswith(":"):
                    p, _ = antiguo_idx[0][pid]
                    usados.update(q["id"] for q, _ in recorrer([p]))
    faltan = [k for k in antiguo_idx[0] if k not in usados]
    if faltan:
        print("AVISO: apartados de 2015 sin ficha:", faltan)


# ---------------------------------------------------------------------------
# HTML para Drupal (estilos en línea: el tema apenas estiliza el contenido)
# ---------------------------------------------------------------------------
AZUL = "#1b2a5c"
E = html.escape


def html_texto(doc):
    out = []
    for b in doc["bloques"]:
        if b["tipo"] == "capitulo":
            out.append(f'<h2 style="margin-top:2em">{E(b["num"].capitalize())}. {E(b["titulo"])}</h2>')
            continue
        titulo = f"Art. {b['num']}. {b['titulo']}" if b["tipo"] == "articulo" else b["titulo"]
        out.append(f'<h3 id="{ancla_bloque(b)}" style="margin-top:1.4em">{E(titulo)}</h3>')
        for p, n in recorrer(b["partes"]):
            margen = f' style="margin-left:{1.6 * (n - 1):.1f}em"' if n > 1 else ""
            etiqueta = f"<strong>{E(p['etiqueta'])}</strong> " if p["etiqueta"] else ""
            out.append(f'<p id="{ancla(p["id"])}"{margen}>{etiqueta}{E(p["texto"])}</p>')
            if p.get("imagen"):
                ancho = 420 if "mini" not in p["imagen"] else 200
                out.append(f'<p><img src="{ARCHIVOS}/reglamento_{p["imagen"]}" alt="Logotipo del Consejo de Estudiantes, '
                           f'{"versión reducida" if "mini" in p["imagen"] else "versión completa"}" width="{ancho}"></p>')
            if p.get("cola"):
                out.append(f"<p>{E(p['cola'])}</p>")
    return "\n".join(out)


def html_indice(doc):
    filas = []
    abierto = False
    for b in doc["bloques"]:
        if b["tipo"] == "capitulo":
            if abierto:
                filas.append("</ul></li>")
            filas.append(f'<li>{E(b["num"].capitalize())}. {E(b["titulo"])}<ul>')
            abierto = True
        else:
            titulo = f"Art. {b['num']}. {b['titulo']}" if b["tipo"] == "articulo" else b["titulo"]
            if b["tipo"] == "disposicion" and abierto:
                filas.append("</ul></li>")
                abierto = False
            filas.append(f'<li><a href="#{ancla_bloque(b)}">{E(titulo)}</a></li>')
    if abierto:
        filas.append("</ul></li>")
    return '<details><summary><strong>Índice</strong></summary><ul>' + "".join(filas) + "</ul></details>"


def caja(contenido, color="#e9edf7", borde=AZUL):
    return (f'<div style="background:{color};border-left:4px solid {borde};padding:12px 16px;margin:0 0 1.2em">'
            f"{contenido}</div>")


def buscador(doc, alto=340):
    return (f'<iframe src="{PAGES}/buscar/?doc={doc}" title="Buscador del Reglamento" '
            f'style="border:1px solid #cfd5e2;border-radius:8px;width:100%;height:{alto}px" loading="lazy"></iframe>')


def pagina_nuevo(doc):
    aviso = caja(
        "<p><strong>Propuesta, todavía no está en vigor.</strong> Es el borrador del Reglamento del Consejo de Estudiantes, "
        "presentado en el pleno constitutivo del 22 de octubre de 2026. Incluye dos cambios propuestos después del pleno "
        "y sometidos a aprobación por asentimiento hasta el 19 de noviembre de 2026: el plazo para delegar el voto "
        f'(<a href="#{ancla("5.6")}">art. 5.6</a>) y el logotipo (<a href="#art-17">art. 17</a> y Anexo). '
        "Entrará en vigor cuando lo ratifique el Consejo de Facultad; hasta entonces sigue vigente el "
        '<a href="/reglamento/antiguo">Reglamento de 2015</a>.</p>'
        f'<p style="margin-bottom:0"><a href="{PDF["nuevo"]}">Descargar el borrador en PDF</a> · '
        '<a href="/reglamento/comparador">Ver qué cambia respecto al de 2015</a> · '
        '<a href="mailto:cienzdel@unizar.es">Enviar comentarios</a></p>', "#fff6dc", "#e6c35c")
    return "\n".join([
        aviso,
        "<h2>Buscar en el texto</h2>",
        buscador("nuevo"),
        "<h2>Texto del borrador</h2>",
        html_indice(doc),
        html_texto(doc),
    ])


def pagina_antiguo(doc):
    aviso = caja(
        "<p><strong>Reglamento en vigor.</strong> Reglamento de la Delegación de Alumnos de la Facultad de Ciencias, "
        "en su modificación de junio de 2015. Se aplica hasta que el Consejo de Facultad ratifique el "
        '<a href="/reglamento/nuevo">nuevo Reglamento</a>, que de momento es una propuesta.</p>'
        f'<p style="margin-bottom:0"><a href="{PDF["antiguo"]}">PDF original</a> · '
        f'<a href="{PDF["antiguo_transcripcion"]}">Transcripción con la plantilla del Consejo (PDF)</a> · '
        '<a href="/reglamento/comparador">Ver qué cambia en la propuesta</a></p>')
    nota = ('<p><em>El texto se reproduce literalmente, con las erratas del original. '
            "En caso de duda, vale el PDF original.</em></p>")
    return "\n".join([
        aviso,
        "<h2>Buscar en el texto</h2>",
        buscador("antiguo"),
        "<h2>Texto del Reglamento</h2>",
        nota,
        html_indice(doc),
        html_texto(doc),
    ])


def pagina_portada():
    tarjeta = ('<div style="border:1px solid #cfd5e2;border-radius:8px;padding:14px 16px;margin:0 0 12px">'
               '<h3 style="margin-top:0"><a href="{url}">{titulo}</a></h3><p style="margin-bottom:0">{texto}</p></div>')
    return "\n".join([
        "<p>El Consejo de Estudiantes se rige por su Reglamento. El de 2015 sigue en vigor, y el Pleno ha preparado "
        "uno nuevo, adaptado a los Estatutos de la Universidad, que está pendiente de ratificación por el "
        "Consejo de Facultad. Aquí puedes leer los dos, buscar en ellos y ver en qué se diferencian.</p>",
        tarjeta.format(url="/reglamento/nuevo", titulo="Reglamento nuevo (propuesta)",
                       texto="Borrador del Reglamento del Consejo de Estudiantes de la Facultad de Ciencias. "
                             f'Texto completo y <a href="{PDF["nuevo"]}">PDF</a>.'),
        tarjeta.format(url="/reglamento/antiguo", titulo="Reglamento antiguo (en vigor)",
                       texto="Reglamento de la Delegación de Alumnos, modificación de junio de 2015. Texto completo, "
                             f'<a href="{PDF["antiguo"]}">PDF original</a> y '
                             f'<a href="{PDF["antiguo_transcripcion"]}">transcripción con la plantilla del Consejo</a>.'),
        tarjeta.format(url="/reglamento/comparador", titulo="Comparador",
                       texto="Qué cambia, tema a tema y explicado en pocas palabras, con los dos textos lado a lado."),
        "<h2>Buscar en los dos reglamentos</h2>",
        buscador("ambos", 400),
    ])


def pagina_comparador():
    return "\n".join([
        "<p>Los cambios entre el Reglamento de 2015 y la propuesta, tema a tema. Pulsa «Ver el texto» en cualquier "
        "cambio para ver los dos textos lado a lado, con lo añadido y lo eliminado resaltado.</p>",
        f'<p><a href="{PAGES}/comparador/">Abrir el comparador a pantalla completa</a></p>',
        f'<iframe src="{PAGES}/comparador/" title="Comparador del Reglamento" '
        'style="border:0;width:100%;height:85vh;min-height:640px" loading="lazy"></iframe>',
    ])


def main():
    antiguo = leer_2015(os.path.join(RAIZ, "fuentes", "reglamento_2015.txt"))
    nuevo = leer_2026(os.path.join(RAIZ, "fuentes", "reglamento_2026.tex"))
    idx = {"antiguo": indexar(antiguo), "nuevo": indexar(nuevo)}
    comprobar_cobertura(idx["antiguo"])

    fichas = []
    for f in C.FICHAS:
        filas = [{"a": celda("antiguo", a, idx["antiguo"]), "n": celda("nuevo", n, idx["nuevo"])} for a, n in f["filas"]]
        fichas.append({k: v for k, v in f.items() if k != "filas"} | {"filas": filas})

    os.makedirs(os.path.join(RAIZ, "datos"), exist_ok=True)
    os.makedirs(os.path.join(RAIZ, "drupal"), exist_ok=True)
    with open(os.path.join(RAIZ, "datos", "reglamentos.json"), "w", encoding="utf-8") as fh:
        json.dump({"paginas": PAGINA, "entradas": entradas_busqueda(nuevo) + entradas_busqueda(antiguo)},
                  fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(RAIZ, "datos", "comparativa.json"), "w", encoding="utf-8") as fh:
        json.dump({"temas": C.TEMAS, "esencial": C.ESENCIAL, "nombres": C.NOMBRES, "fichas": fichas,
                   "paginas": PAGINA, "pdf": {k: WEB + v for k, v in PDF.items()}},
                  fh, ensure_ascii=False, separators=(",", ":"))
    for nombre, contenido in [("reglamento.html", pagina_portada()), ("reglamento-nuevo.html", pagina_nuevo(nuevo)),
                              ("reglamento-antiguo.html", pagina_antiguo(antiguo)),
                              ("reglamento-comparador.html", pagina_comparador())]:
        with open(os.path.join(RAIZ, "drupal", nombre), "w", encoding="utf-8") as fh:
            fh.write(contenido + "\n")
    print("Fichas:", len(fichas), "· entradas de búsqueda:", len(entradas_busqueda(nuevo)) + len(entradas_busqueda(antiguo)))


if __name__ == "__main__":
    main()
