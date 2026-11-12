# Reglamento del Consejo de Estudiantes de Ciencias

Buscador y comparador del Reglamento para [cienzdel.unizar.es/reglamento](https://cienzdel.unizar.es/reglamento),
servidos con GitHub Pages en https://cienzdel.github.io/reglamento/ e incrustados en Drupal con un iframe.

- `buscar/?doc=nuevo|antiguo|ambos`: buscador; los resultados abren el apartado en cienzdel.unizar.es.
- `comparador/`: qué cambia entre el Reglamento de 2015 y la propuesta, tema a tema, con los dos textos a dos columnas.

## Cómo se actualiza

1. Fuentes: `fuentes/reglamento_2015.txt` (texto del PDF original) y `fuentes/reglamento_2026.tex`
   (copia del LaTeX del borrador; si cambia, se vuelve a copiar).
2. Explicaciones del comparador: `herramientas/comparativa.py` (cada ficha empareja apartados de los dos textos).
3. `python herramientas/construir.py` regenera `datos/*.json` y `drupal/*.html`. Avisa si queda algún apartado de 2015 sin ficha.
4. Los `drupal/*.html` se pegan como cuerpo (formato filtered_html) de las páginas /reglamento, /reglamento/nuevo,
   /reglamento/antiguo y /reglamento/comparador.
5. `python herramientas/latex_2015.py DESTINO/reglamento_2015.tex` genera la transcripción de 2015 con la plantilla del Consejo.

Sin dependencias ni paso de compilación: HTML, CSS y JS estáticos.
