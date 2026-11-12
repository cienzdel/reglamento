// Buscador de los reglamentos. ?doc=nuevo | antiguo | ambos
// Los resultados enlazan al apartado en cienzdel.unizar.es y abren en la página principal (target _top).
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  let ambito = ["nuevo", "antiguo", "ambos"].includes(params.get("doc")) ? params.get("doc") : "ambos";
  const fijo = ambito !== "ambos";

  const q = document.getElementById("q");
  const estado = document.getElementById("estado");
  const lista = document.getElementById("resultados");
  const sug = document.getElementById("sugerencias");
  const caja = document.getElementById("ambito");

  const SUGERENCIAS = {
    nuevo: ["delegar el voto", "asentimiento", "moción de censura", "quorum", "vocalías", "tesorería", "telemática"],
    antiguo: ["voto", "moción de censura", "quórum", "vocales", "delegado de Titulación", "Junta Electoral"],
    ambos: ["voto", "moción de censura", "quorum", "vocal", "titulación", "dimisión", "extraordinaria"],
  };
  const NOMBRE = { nuevo: "Propuesta", antiguo: "2015" };

  // Sin tildes y en minúsculas, conservando la longitud (para resaltar sobre el texto original).
  const plano = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const sinTildes = (s) => Array.from(s).map((c) => plano(c) || c).join("");

  let entradas = [];
  fetch("../datos/reglamentos.json")
    .then((r) => r.json())
    .then((d) => {
      entradas = d.entradas.map((e) => ({ ...e, _t: sinTildes(e.texto), _h: sinTildes(e.ref + " " + e.titulo) }));
      if (q.value) buscar();
    })
    .catch(() => { estado.textContent = "No se ha podido cargar el texto. Recarga la página."; });

  function pintarSugerencias() {
    sug.querySelectorAll("button").forEach((b) => b.remove());
    for (const s of SUGERENCIAS[ambito]) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "chip"; b.textContent = s;
      b.addEventListener("click", () => { q.value = s; buscar(); q.focus(); });
      sug.appendChild(b);
    }
  }

  if (!fijo) {
    caja.hidden = false;
    caja.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      ambito = b.dataset.doc;
      caja.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      pintarSugerencias();
      buscar();
    }));
  }
  pintarSugerencias();

  const VACIAS = new Set(["de", "del", "la", "el", "los", "las", "y", "e", "o", "u", "a", "al", "en", "que", "por", "con", "un", "una", "se", "su", "sus", "para"]);
  const letra = (c) => c !== undefined && /[a-z0-9ñºª]/.test(c);
  // Posiciones donde «term» empieza palabra en el texto plano «p»
  function posiciones(p, term) {
    const out = [];
    let i = p.indexOf(term);
    while (i >= 0) { if (!letra(p[i - 1])) out.push(i); i = p.indexOf(term, i + 1); }
    return out;
  }

  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  function fragmento(e, terminos, frase) {
    const t = e.texto, p = e._t;
    let ini = posiciones(p, frase)[0];
    if (ini === undefined) ini = posiciones(p, terminos[0])[0] || 0;
    let desde = Math.max(0, ini - 90), hasta = Math.min(t.length, ini + 200);
    if (desde > 0) { const sp = t.indexOf(" ", desde); if (sp >= 0 && sp < ini) desde = sp + 1; }
    if (hasta < t.length) { const sp = t.lastIndexOf(" ", hasta); if (sp > ini) hasta = sp; }
    let trozo = t.slice(desde, hasta), trozoP = p.slice(desde, hasta);
    // Marcar todas las apariciones de todos los términos en el trozo
    const marcas = [];
    for (const term of terminos) {
      for (const i of posiciones(trozoP, term)) marcas.push([i, i + term.length]);
    }
    marcas.sort((a, b) => a[0] - b[0]);
    let out = "", pos = 0;
    for (const [a, b] of marcas) {
      if (a < pos) continue;
      out += esc(trozo.slice(pos, a)) + "<mark>" + esc(trozo.slice(a, b)) + "</mark>";
      pos = b;
    }
    out += esc(trozo.slice(pos));
    return (desde > 0 ? "… " : "") + out + (hasta < t.length ? " …" : "");
  }

  function buscar() {
    const consulta = sinTildes(q.value.trim());
    lista.innerHTML = "";
    sug.hidden = consulta.length > 0;
    if (consulta.length < 2) { estado.textContent = ""; return; }
    const todas = consulta.split(/\s+/).filter((x) => x.length > 0);
    const utiles = todas.filter((x) => !VACIAS.has(x));
    const terminos = utiles.length ? utiles : todas;
    const res = [];
    for (const e of entradas) {
      if (ambito !== "ambos" && e.doc !== ambito) continue;
      let puntos = 0, todos = true;
      for (const term of terminos) {
        const enTexto = posiciones(e._t, term).length;
        const enTitulo = e._h.includes(term) ? 3 : 0;
        if (enTexto + enTitulo === 0) { todos = false; break; }
        puntos += enTexto + enTitulo;
      }
      if (todos) {
        if (posiciones(e._t, consulta).length) puntos += 5; // la frase exacta
        res.push([puntos, e]);
      }
    }
    res.sort((a, b) => b[0] - a[0]);
    if (!res.length) { estado.textContent = "No hay resultados. Prueba con otra palabra o con menos palabras."; return; }
    estado.textContent = res.length === 1 ? "1 resultado" : `${res.length} resultados`;
    const html = res.slice(0, 40).map(([, e]) =>
      `<li><a href="${e.url}" target="_top"><span class="cab">` +
      (ambito === "ambos" ? `<span class="etiqueta doc-${e.doc}">${NOMBRE[e.doc]}</span>` : "") +
      `<span class="ref">${esc(e.ref)}</span><span class="tit">${esc(e.titulo)}</span></span>` +
      `<p class="frag">${fragmento(e, terminos, consulta)}</p></a></li>`).join("");
    lista.innerHTML = html;
  }

  let temporizador;
  q.addEventListener("input", () => { clearTimeout(temporizador); temporizador = setTimeout(buscar, 120); });
})();
