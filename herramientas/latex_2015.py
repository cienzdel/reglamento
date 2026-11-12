"""Genera la transcripción literal del Reglamento de 2015 con la plantilla del Consejo.

Uso: python herramientas/latex_2015.py RUTA/reglamento_2015.tex
La carpeta de destino debe contener estilo-reglamento.tex, fonts/, logo_consejo.pdf y
sello_ciencias_agua.pdf (los mismos que el Reglamento de 2026).
"""
import sys
from leer import leer_2015

ESC = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_"}


def esc(s):
    return "".join(ESC.get(c, c) for c in s)


def partes(ps, nivel, out):
    sangria = "  " * nivel
    entorno = "enumerate"
    out.append(f"{sangria}\\begin{{{entorno}}}")
    for p in ps:
        out.append(f"{sangria}\\item[{esc(p['etiqueta'])}] {esc(p['texto'])}")
        if p["sub"]:
            partes(p["sub"], nivel + 1, out)
        if p.get("cola"):
            out.append("")
            out.append(f"{sangria}{esc(p['cola'])}")
    out.append(f"{sangria}\\end{{{entorno}}}")


def main(destino):
    doc = leer_2015(sys.path[0] + "/../fuentes/reglamento_2015.txt")
    out = [
        "% !TEX program = lualatex",
        "% Transcripción literal del Reglamento de la Delegación de Alumnos de la Facultad de Ciencias",
        "% (modificación de junio de 2015) con la plantilla del Consejo de Estudiantes.",
        "% Generado por herramientas/latex_2015.py (repo cienzdel/reglamento): no editar a mano.",
        "\\documentclass[11pt,a4paper]{article}",
        "\\input{estilo-reglamento}",
        "\\borradorfalse",
        "\\renewcommand{\\piedepagina}{Reglamento de la Delegación de Alumnos de la Facultad de Ciencias (2015) · Transcripción}",
        "\\hypersetup{pdftitle={Reglamento de la Delegación de Alumnos de la Facultad de Ciencias (2015). Transcripción}}",
        "",
        "\\begin{document}",
        "",
        "\\thispagestyle{portada}",
        "\\vspace*{50mm}",
        "\\begin{center}",
        "{\\fontsize{26}{32}\\selectfont\\bfseries REGLAMENTO DE LA DELEGACIÓN\\\\[2pt] DE ALUMNOS\\\\[2pt] FACULTAD DE CIENCIAS\\par}",
        "\\vspace{6pt}",
        "{\\fontsize{11}{14}\\selectfont DE LA REPRESENTACIÓN DE LOS ESTUDIANTES Y SU ORGANIZACIÓN\\par}",
        "\\end{center}",
        "\\vfill",
        "\\begin{center}",
        "\\parbox{120mm}{\\centering\\small\\color{grisPie}Transcripción literal del Reglamento vigente, en su modificación de junio de 2015,",
        "con la plantilla actual del Consejo de Estudiantes. Se respeta el texto original, erratas incluidas.",
        "El texto con validez es el del documento original.}",
        "\\end{center}",
        "\\vspace*{10mm}",
        "\\clearpage",
        "",
        "\\tableofcontents",
        "\\clearpage",
        "",
    ]
    for b in doc["bloques"]:
        if b["tipo"] == "capitulo":
            out += ["", f"\\capitulo{{{esc(b['num'])}}}{{{esc(b['titulo'])}}}", ""]
        elif b["tipo"] == "articulo":
            titulo = b["titulo"]
            out.append(f"\\articulo{{{b['num']}}}{{{esc(titulo)}}}")
            ps = b["partes"]
            if len(ps) == 1 and not ps[0]["etiqueta"]:  # art. 10: sin apartados
                out.append(esc(ps[0]["texto"]))
                partes(ps[0]["sub"], 0, out)
            else:
                partes(ps, 0, out)
            out.append("")
        else:
            out += ["", f"\\disposicion{{{esc(b['titulo'])}}}"]
            for p in b["partes"]:
                out.append(esc(p["texto"]))
            out.append("")
    out.append("\\end{document}")
    open(destino, "w", encoding="utf-8").write("\n".join(out) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
