const dims = [
  { key: "picante", label: "picante", value: 5, emoji: "🌶️" },
  { key: "dulce", label: "dulce", value: 5, emoji: "🍯" },
  { key: "salado", label: "salado", value: 5, emoji: "🧂" },
  { key: "vegetariano", label: "vegetariano", value: 5, emoji: "🥬" },
  { key: "carne", label: "carne", value: 5, emoji: "🥩" },
];

const state = {
  members: [],
  method: "mayoria_ponderada",
  topK: 5,
  lastResult: null,
};

const $ = (selector) => document.querySelector(selector);
const sliders = $("#sliders");
const profileForm = $("#profileForm");
const memberList = $("#memberList");
const emptyState = $("#emptyState");
const memberCount = $("#memberCount");
const statusText = $("#statusText");
const loader = $("#loader");
const resultsGrid = $("#resultsGrid");
const profileN = $("#profileN");
const comparePanel = $("#comparePanel");

function initSliders() {
  sliders.innerHTML = dims.map((dim, index) => `
    <div class="slider-row">
      <div class="slider-top">
        <strong>${dim.emoji} ${dim.label}</strong>
        <span id="value-${dim.key}">${dim.value}</span>
      </div>
      <input aria-label="${dim.label}" data-index="${index}" data-key="${dim.key}" type="range" min="1" max="10" value="${dim.value}" />
    </div>
  `).join("");

  sliders.querySelectorAll("input[type='range']").forEach((input) => {
    input.addEventListener("input", () => {
      $(`#value-${input.dataset.key}`).textContent = input.value;
    });
  });
}

function getVectorFromForm() {
  return Array.from(sliders.querySelectorAll("input[type='range']")).map((input) => Number(input.value));
}

function getRestrictionsFromForm() {
  return Array.from(document.querySelectorAll(".restrictions input:checked")).map((input) => input.value);
}

function resetForm() {
  profileForm.reset();
  sliders.querySelectorAll("input[type='range']").forEach((input) => {
    input.value = 5;
    $(`#value-${input.dataset.key}`).textContent = "5";
  });
  $("#presupuesto").value = 30000;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function renderMembers() {
  memberCount.textContent = `${state.members.length} ${state.members.length === 1 ? "persona" : "personas"}`;
  emptyState.classList.toggle("hidden", state.members.length > 0);

  memberList.innerHTML = state.members.map((member, index) => `
    <article class="member">
      <div>
        <strong>${member.nombre}</strong>
        <small>${formatCurrency(member.presupuesto_max)} · ${member.restricciones.length ? member.restricciones.join(", ") : "sin restricciones"}</small>
      </div>
      <button class="remove-member" type="button" aria-label="Eliminar ${member.nombre}" data-index="${index}">×</button>
    </article>
  `).join("");

  memberList.querySelectorAll(".remove-member").forEach((button) => {
    button.addEventListener("click", () => {
      state.members.splice(Number(button.dataset.index), 1);
      renderMembers();
    });
  });
}

function setStatus(message, loading = false) {
  statusText.textContent = message;
  loader.classList.toggle("hidden", !loading);
}

function methodLabel(method) {
  const labels = {
    mayoria_ponderada: "mayoría ponderada",
    promedio: "promedio naive",
    minima_miseria: "mínima miseria",
    maximo_placer: "máximo placer",
    media_satisfaccion: "media satisfacción",
  };
  return labels[method] || method;
}

function restaurantEmoji(restaurante) {
  const tipos = (restaurante.tipo_cocina || []).join(" ").toLowerCase();
  if (tipos.includes("pizza") || tipos.includes("italiana")) return "🍕";
  if (tipos.includes("mex")) return "🌮";
  if (tipos.includes("jap") || tipos.includes("sushi")) return "🍣";
  if (tipos.includes("veg")) return "🥗";
  if (tipos.includes("hamb")) return "🍔";
  if (tipos.includes("postre") || tipos.includes("cafe")) return "☕";
  return "🍽️";
}

function renderProfileN(perfil) {
  if (!perfil) {
    profileN.classList.add("hidden");
    return;
  }

  profileN.classList.remove("hidden");
  profileN.innerHTML = Object.entries(perfil).map(([key, value]) => `
    <div class="n-pill">
      <strong>${key}</strong>
      <span>${Number(value).toFixed(1)}</span>
    </div>
  `).join("");
}

function renderResults(data) {
  state.lastResult = data;
  renderProfileN(data.perfil_n);
  comparePanel.classList.add("hidden");
  comparePanel.innerHTML = "";

  if (!data.restaurantes || !data.restaurantes.length) {
    resultsGrid.innerHTML = "";
    setStatus("No encontramos restaurantes que cumplan las restricciones. Prueba ampliar presupuesto o relajar alguna restricción.");
    return;
  }

  setStatus(`Método usado: ${methodLabel(data.metodo_usado)} · ${data.restaurantes.length} opciones compatibles`);

  resultsGrid.innerHTML = data.restaurantes.map((restaurante, index) => {
    const score = Math.round((restaurante.score_grupo || 0) * 100);
    const scoreMin = Math.round((restaurante.score_min || 0) * 100);
    const tags = [
      ...(restaurante.tipo_cocina || []).slice(0, 3),
      restaurante.tiene_vegetariano ? "veg friendly" : null,
      restaurante.hace_delivery ? "delivery" : null,
    ].filter(Boolean);

    const personas = restaurante.satisfaccion_por_persona || {};
    return `
      <article class="restaurant-card">
        <div class="rest-visual">
          <span class="emoji">${restaurantEmoji(restaurante)}</span>
          <span class="score-badge">${score}%</span>
        </div>
        <div class="rest-body">
          <h3>${index + 1}. ${restaurante.nombre}</h3>
          <div class="tags">
            <span class="tag">${formatCurrency(restaurante.precio_promedio_cop)}</span>
            <span class="tag">★ ${Number(restaurante.rating || 4).toFixed(1)}</span>
            ${tags.map((tag) => `<span class="tag">${tag}</span>`).join("")}
          </div>
          <p class="justification">${restaurante.justificacion || restaurante.descripcion || "Opción compatible con el perfil del grupo."}</p>
          <div class="meter">
            <div class="meter-top"><span>satisfacción mínima</span><strong>${scoreMin}%</strong></div>
            <div class="meter-track"><div class="meter-fill" style="width:${scoreMin}%"></div></div>
          </div>
          <div class="person-scores">
            ${Object.entries(personas).map(([name, value]) => `<span>${name}: ${Math.round(value * 100)}%</span>`).join("")}
          </div>
          <form class="feedback-box" data-recomendacion-id="${restaurante.recomendacion_id || ""}">
            <strong>Feedback rápido</strong>
            <label>
              ¿Quién evalúa?
              <select name="usuario_nombre" required>
                <option value="">Selecciona</option>
                ${state.members.map((m) => `<option value="${m.nombre}">${m.nombre}</option>`).join("")}
              </select>
            </label>
            <div class="feedback-row">
              <label class="check-pill"><input type="checkbox" name="fue_al_restaurante" checked> Sí fuimos</label>
              <label>
                Calificación
                <select name="calificacion">
                  <option value="5">5 · excelente</option>
                  <option value="4">4 · buena</option>
                  <option value="3">3 · normal</option>
                  <option value="2">2 · floja</option>
                  <option value="1">1 · mala</option>
                </select>
              </label>
            </div>
            <textarea name="comentario" rows="2" placeholder="Comentario opcional"></textarea>
            <button class="feedback-btn" type="submit" ${restaurante.recomendacion_id ? "" : "disabled"}>Guardar feedback</button>
            ${restaurante.recomendacion_id ? "" : `<small class="feedback-warning">No hay recomendacion_id. Revisa conexión con Supabase.</small>`}
          </form>
        </div>
      </article>
    `;
  }).join("");

  attachFeedbackHandlers();
}


function attachFeedbackHandlers() {
  document.querySelectorAll(".feedback-box").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const recomendacionId = form.dataset.recomendacionId;
      if (!recomendacionId) {
        setStatus("No pude guardar feedback porque esta tarjeta no tiene recomendacion_id.");
        return;
      }

      const formData = new FormData(form);
      const payload = {
        recomendacion_id: recomendacionId,
        usuario_nombre: formData.get("usuario_nombre"),
        fue_al_restaurante: formData.get("fue_al_restaurante") === "on",
        calificacion: Number(formData.get("calificacion") || 3),
        comentario: formData.get("comentario") || "",
      };

      const button = form.querySelector("button");
      button.disabled = true;
      button.textContent = "Guardando...";

      try {
        const data = await postJSON("/feedback", payload);
        form.classList.add("feedback-saved");
        button.textContent = data.guardado ? "Feedback guardado ✓" : "No se pudo guardar";
        setStatus(data.mensaje || "Feedback guardado en Supabase.");
      } catch (error) {
        button.disabled = false;
        button.textContent = "Guardar feedback";
        setStatus(error.message);
      }
    });
  });
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "No se pudo completar la solicitud.");
  }
  return data;
}

async function recommend() {
  if (!state.members.length) {
    setStatus("Agrega al menos una persona para recomendar.");
    location.hash = "#grupo";
    return;
  }

  setStatus("Calculando compatibilidad del grupo...", true);
  resultsGrid.innerHTML = "";
  comparePanel.classList.add("hidden");
  location.hash = "#resultados";

  try {
    const data = await postJSON("/recomendar", {
      grupo: state.members,
      metodo: state.method,
      top_k: state.topK,
    });
    renderResults(data);
  } catch (error) {
    setStatus(`${error.message} Puedes revisar que Flask esté corriendo en http://localhost:5000.`);
  } finally {
    loader.classList.add("hidden");
  }
}

function renderComparison(data) {
  const comparativa = data.comparativa || {};
  const entries = Object.entries(comparativa).map(([method, info]) => ({
    method,
    score: info.score_top_1 || 0,
    minScore: info.score_min_top_1 || 0,
    name: info.top_1 || "Sin resultado",
  })).sort((a, b) => b.score - a.score);

  comparePanel.classList.remove("hidden");
  comparePanel.innerHTML = `
    <h3>Comparación crítica de métodos</h3>
    <p>Cada método puede cambiar el restaurante ganador porque representa una forma distinta de tomar decisiones grupales.</p>
    ${entries.map((entry) => `
      <div class="compare-row" title="Ganador: ${entry.name}">
        <strong>${methodLabel(entry.method)}</strong>
        <div class="compare-bar"><span style="width:${Math.round(entry.score * 100)}%"></span></div>
        <small>${Math.round(entry.score * 100)}%</small>
      </div>
    `).join("")}
  `;
}

async function compareMethods() {
  if (!state.members.length) {
    setStatus("Agrega integrantes antes de comparar métodos.");
    location.hash = "#grupo";
    return;
  }

  setStatus("Comparando métodos de agregación...", true);
  location.hash = "#resultados";

  try {
    const data = await postJSON("/comparar-metodos", { grupo: state.members });
    renderComparison(data);
    setStatus("Comparación lista. Úsala para explicar el componente socio-tecnológico del proyecto.");
  } catch (error) {
    setStatus(error.message);
  } finally {
    loader.classList.add("hidden");
  }
}

function loadDemo() {
  state.members = [
    {
      nombre: "Camila",
      vector: [3, 7, 6, 9, 2],
      presupuesto_max: 28000,
      distancia_max: 2000,
      restricciones: ["vegetariano"],
      peso_voto: 1,
    },
    {
      nombre: "Juan",
      vector: [8, 3, 8, 2, 9],
      presupuesto_max: 35000,
      distancia_max: 2000,
      restricciones: [],
      peso_voto: 1,
    },
    {
      nombre: "Sofi",
      vector: [4, 8, 5, 7, 4],
      presupuesto_max: 30000,
      distancia_max: 2000,
      restricciones: ["sin_mariscos"],
      peso_voto: 1.2,
    },
  ];
  renderMembers();
  setStatus("Demo cargada. Puedes recomendar o editar el grupo.");
  location.hash = "#grupo";
}

profileForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const nombre = $("#nombre").value.trim();

  state.members.push({
    nombre,
    vector: getVectorFromForm(),
    presupuesto_max: Number($("#presupuesto").value),
    distancia_max: 2000,
    restricciones: getRestrictionsFromForm(),
    peso_voto: 1,
  });

  renderMembers();
  resetForm();
});

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segment").forEach((segment) => segment.classList.remove("active"));
    button.classList.add("active");
    state.method = button.dataset.method;
  });
});

$("#recommendBtn").addEventListener("click", recommend);
$("#compareBtn").addEventListener("click", compareMethods);
$("#demoBtn").addEventListener("click", loadDemo);
$("#clearBtn").addEventListener("click", () => {
  state.members = [];
  state.lastResult = null;
  renderMembers();
  resultsGrid.innerHTML = "";
  renderProfileN(null);
  comparePanel.classList.add("hidden");
  setStatus("Grupo limpio. Agrega nuevas personas para recomendar.");
});

initSliders();
renderMembers();
