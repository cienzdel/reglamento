// Comparador del Reglamento: fichas por tema y, al desplegar, los dos textos con las diferencias resaltadas.
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const plano = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const TIPOS = { nuevo: "Nuevo", cambia: "Cambia", retoque: "Retoque" };

  let datos, temaActivo = "todos";
  const tiposActivos = new Set();

  fetch("../datos/comparativa.json").then((r) => r.json()).then((d) => { datos = d; iniciar(); })
    .catch(() => { $("estado").textContent = "No se han podido cargar los datos. Recarga la página."; });

  function iniciar() {
    $("l-antiguo").href = datos.paginas.antiguo;
    $("l-nuevo").href = datos.paginas.nuevo;
    $("esencial").innerHTML = datos.esencial.map((s) => `<li>${s}</li>`).join("");
    $("nombres").innerHTML = datos.nombres.map(([a, n]) => `<tr><td>${esc(a)}</td><td>${esc(n)}</td></tr>`).join("");

    // Filtros de tema
    const temas = $("temas");
    const chip = (texto, valor, grupo, extra = "") =>
      `<button type="button" class="chip ${extra}" data-${grupo}="${valor}" aria-pressed="false">${texto}</button>`;
    temas.innerHTML = chip("Todos", "todos", "tema") +
      Object.entries(datos.temas).map(([k, v]) => chip(esc(v), k, "tema")).join("");
    temas.querySelector('[data-tema="todos"]').setAttribute("aria-pressed", "true");
    temas.addEventListener("click", (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      temaActivo = b.dataset.tema;
      temas.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      filtrar();
    });
    const tipos = $("tipos");
    tipos.innerHTML = Object.entries(TIPOS).map(([k, v]) => chip(v, k, "tipo", "t-" + k)).join("");
    tipos.addEventListener("click", (ev) => {
      const b = ev.target.closest("button"); if (!b) return;
      const t = b.dataset.tipo;
      if (tiposActivos.has(t)) tiposActivos.delete(t); else tiposActivos.add(t);
      b.setAttribute("aria-pressed", String(tiposActivos.has(t)));
      filtrar();
    });

    pintarFichas();
    let tmp;
    $("q").addEventListener("input", () => { clearTimeout(tmp); tmp = setTimeout(filtrar, 120); });
    $("todo").addEventListener("click", () => {
      const visibles = [...document.querySelectorAll(".ficha:not([hidden]) .ver")];
      const abrir = visibles.some((b) => b.getAttribute("aria-expanded") !== "true");
      visibles.forEach((b) => alternar(b, abrir));
      $("todo").textContent = abrir ? "Plegar todos los textos" : "Desplegar todos los textos";
    });
    filtrar();
    if (location.hash) {
      const f = document.getElementById(location.hash.slice(1));
      if (f) { alternar(f.querySelector(".ver"), true); f.scrollIntoView(); }
    }
  }

  function donde(f) {
    const refs = (lado) => [...new Set(f.filas.map((r) => r[lado] && r[lado].ref).filter(Boolean)
      .map((r) => r.replace(/^Art\. (\d+)\..*$/, "Art. $1")))];
    const a = refs("a"), n = refs("n");
    const txt = (l) => l.length ? l.join(", ") : "—";
    return `2015: ${esc(txt(a))} &nbsp;→&nbsp; Propuesta: ${esc(txt(n))}`;
  }

  function pintarFichas() {
    const cont = $("fichas");
    let html = "";
    for (const [clave, nombre] of Object.entries(datos.temas)) {
      const fichas = datos.fichas.filter((f) => f.tema === clave);
      if (!fichas.length) continue;
      html += `<section class="tema" data-tema="${clave}"><h2>${esc(nombre)}</h2>`;
      for (const f of fichas) {
        html += `<article class="ficha ${f.tipo}" id="${f.id}" data-i="${datos.fichas.indexOf(f)}">` +
          `<h3><span class="etiqueta ${f.tipo}">${TIPOS[f.tipo]}</span>${esc(f.titulo)}</h3>` +
          `<p class="donde">${donde(f)}</p>` +
          `<p class="resumen">${esc(f.resumen)}</p>` +
          (f.puntos ? `<ul class="puntos">${f.puntos.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>` : "") +
          `<button type="button" class="ver" aria-expanded="false" aria-controls="tx-${f.id}">Ver el texto</button>` +
          `<div class="textos" id="tx-${f.id}" hidden></div></article>`;
      }
      html += "</section>";
    }
    cont.innerHTML = html;
    cont.addEventListener("click", (ev) => {
      const b = ev.target.closest(".ver"); if (b) alternar(b);
    });
  }

  function alternar(boton, forzar) {
    const abrir = forzar === undefined ? boton.getAttribute("aria-expanded") !== "true" : forzar;
    const caja = document.getElementById(boton.getAttribute("aria-controls"));
    if (abrir && !caja.dataset.hecho) {
      caja.innerHTML = textos(datos.fichas[+boton.closest(".ficha").dataset.i]);
      caja.dataset.hecho = "1";
    }
    caja.hidden = !abrir;
    boton.setAttribute("aria-expanded", String(abrir));
    boton.textContent = abrir ? "Ocultar el texto" : "Ver el texto";
  }

  function filtrar() {
    const q = plano($("q").value.trim());
    const terms = q ? q.split(/\s+/) : [];
    let n = 0;
    document.querySelectorAll(".ficha").forEach((el) => {
      const f = datos.fichas[+el.dataset.i];
      let ok = (temaActivo === "todos" || f.tema === temaActivo) && (!tiposActivos.size || tiposActivos.has(f.tipo));
      if (ok && terms.length) {
        if (!f._busca) {
          const textos = f.filas.flatMap((r) => [r.a, r.n]).filter(Boolean).flatMap((c) => c.seg.map((s) => s.t));
          f._busca = plano([f.titulo, f.resumen, ...(f.puntos || []), ...textos].join(" "));
        }
        ok = terms.every((t) => f._busca.includes(t));
      }
      el.hidden = !ok;
      if (ok) n++;
    });
    document.querySelectorAll(".tema").forEach((s) => { s.hidden = !s.querySelector(".ficha:not([hidden])"); });
    $("estado").textContent = n === datos.fichas.length ? `${n} cambios` :
      n === 0 ? "Ningún cambio coincide con la búsqueda o los filtros." : `${n} de ${datos.fichas.length} cambios`;
  }

  // ---------------------------------------------------------------- diferencias
  const RE = /[\p{L}\p{N}ºª#]+|[^\s\p{L}\p{N}]/gu;
  function trocear(celda) {
    // Devuelve [{seg, palabra, espacio}] de todos los segmentos de la celda
    const out = [];
    celda.seg.forEach((s, i) => {
      let m, ultimo = 0;
      RE.lastIndex = 0;
      while ((m = RE.exec(s.t))) {
        out.push({ s: i, w: m[0], sp: m.index > ultimo || (m.index === 0 && out.length && out[out.length - 1].s !== i) });
        ultimo = m.index + m[0].length;
      }
    });
    return out;
  }

  function lcs(a, b) {
    const n = a.length, m = b.length;
    const t = new Uint16Array((n + 1) * (m + 1));
    for (let i = n - 1; i >= 0; i--)
      for (let j = m - 1; j >= 0; j--)
        t[i * (m + 1) + j] = a[i].w === b[j].w ? t[(i + 1) * (m + 1) + j + 1] + 1
          : Math.max(t[(i + 1) * (m + 1) + j], t[i * (m + 1) + j + 1]);
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (a[i].w === b[j].w) { a[i].k = b[j].k = true; i++; j++; }
      else if (t[(i + 1) * (m + 1) + j] >= t[i * (m + 1) + j + 1]) i++;
      else j++;
    }
  }

  function pintarCelda(celda, tokens, marca, lado, rotulo) {
    if (!celda) {
      return `<div class="celda"><span class="rot">${rotulo}</span>` +
        `<p class="vacia">${lado === "a" ? "No existía en 2015." : "Desaparece en la propuesta."}</p></div>`;
    }
    const porSeg = celda.seg.map(() => []);
    for (const t of tokens) porSeg[t.s].push(t);
    const cuerpo = celda.seg.map((s, i) => {
      let h = "", abierto = false;
      for (const t of porSeg[i]) {
        const cambia = !t.k;
        if (cambia && !abierto) { h += (t.sp && h ? " " : "") + `<${marca} class="${marca === "del" ? "d" : "i"}">`; abierto = true; }
        else if (!cambia && abierto) { h += `</${marca}>`; abierto = false; if (t.sp) h += " "; }
        else if (t.sp && h) h += " ";
        h += esc(t.w);
      }
      if (abierto) h += `</${marca}>`;
      const et = s.e ? `<strong>${esc(s.e)}</strong> ` : "";
      return `<p class="n${Math.min(s.n, 3)}">${et}${h}</p>`;
    }).join("");
    return `<div class="celda"><span class="rot">${rotulo}</span>` +
      `<a class="ref" href="${celda.url}" target="_top">${esc(celda.ref)}</a>${cuerpo}</div>`;
  }

  function textos(f) {
    let h = `<div class="textos-cab"><div>Reglamento de 2015</div><div>Propuesta</div></div>`;
    for (const fila of f.filas) {
      const ta = fila.a ? trocear(fila.a) : [], tn = fila.n ? trocear(fila.n) : [];
      let nota = "";
      if (fila.a && fila.n) {
        lcs(ta, tn);
        const comunes = ta.filter((t) => t.k).length;
        // Si apenas comparten texto, el resaltado palabra a palabra no ayuda: se muestran limpios.
        if (2 * comunes / (ta.length + tn.length) < 0.45) {
          ta.forEach((t) => (t.k = true)); tn.forEach((t) => (t.k = true));
          nota = `<p class="reescrito">Reescrito por completo: se muestran los dos textos sin marcar.</p>`;
        }
      } else { ta.forEach((t) => (t.k = true)); tn.forEach((t) => (t.k = true)); }
      h += nota + `<div class="par">${pintarCelda(fila.a, ta, "del", "a", "2015")}${pintarCelda(fila.n, tn, "ins", "n", "Propuesta")}</div>`;
    }
    return h;
  }
})();
