const $ = (selector) => document.querySelector(selector);

const decisionCopy = {
  approve: { label: "Aprobación simulada", badge: "Aprobar", color: "#62c3a3" },
  review: { label: "Revisión manual", badge: "Revisar", color: "#e0a553" },
  reject: { label: "Rechazo simulado", badge: "Rechazar", color: "#d17279" },
};

function percent(value, digits = 1) {
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function shortHash(value) {
  return value ? `${value.slice(0, 12)}…${value.slice(-6)}` : "No disponible";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.message || body.detail?.[0]?.msg || "No fue posible completar la solicitud.");
  }
  return body;
}

function renderMetrics(metrics) {
  const cards = [
    ["ROC AUC", metrics.roc_auc.toFixed(3), "Capacidad de ordenamiento en prueba"],
    ["Exactitud", percent(metrics.accuracy), `${metrics.test_records} registros de prueba`],
    ["Recall favorable", percent(metrics.recall), "Clase positiva sintética"],
    ["Brier score", metrics.brier_score.toFixed(3), "Menor es mejor para probabilidad"],
  ];
  $("#metric-grid").innerHTML = cards
    .map(
      ([label, value, note]) => `
        <article class="metric-card">
          <span class="metric-label">${label}</span>
          <strong class="metric-value">${value}</strong>
          <small class="metric-note">${note}</small>
        </article>
      `,
    )
    .join("");
}

function renderTrace(metadata, operations) {
  $("#trace-model").textContent = `${metadata.algorithm} · ${metadata.model_version}`;
  $("#trace-dataset").textContent = shortHash(metadata.dataset_hash);
  $("#trace-requests").textContent = `${operations.scoring_requests} solicitudes`;
  $("#trace-invalid").textContent = `${operations.invalid_requests} entradas inválidas detectadas.`;
}

async function loadModelCard() {
  const status = $("#system-status");
  try {
    const card = await fetchJson("/api/model-card");
    renderMetrics(card.metrics);
    renderTrace(card.metadata, card.operations);
    status.className = "system-status online";
    status.innerHTML = '<span class="status-dot"></span><span>Modelo disponible</span>';
  } catch (error) {
    status.className = "system-status offline";
    status.innerHTML = '<span class="status-dot"></span><span>Modelo no disponible</span>';
    $("#metric-grid").innerHTML = `
      <article class="metric-card">
        <span class="metric-label">Error de carga</span>
        <strong class="metric-value">—</strong>
        <small class="metric-note">${error.message}</small>
      </article>`;
  }
}

async function refreshOperations() {
  try {
    const metrics = await fetchJson("/api/metrics");
    const card = await fetchJson("/api/model-card");
    renderTrace(card.metadata, metrics.operations);
  } catch {
    // The scoring result remains usable even if the secondary refresh fails.
  }
}

function serializeForm(form) {
  const data = new FormData(form);
  const numberFields = [
    "monthly_income",
    "employment_months",
    "requested_amount",
    "current_obligations",
    "savings_balance",
  ];
  const applicant = {};
  for (const field of numberFields) applicant[field] = Number(data.get(field));
  applicant.employment_type = data.get("employment_type");
  applicant.housing_type = data.get("housing_type");
  return {
    applicant,
    trusted_profile_id: data.get("trusted_profile_id"),
  };
}

function renderResult(result, thresholds) {
  const copy = decisionCopy[result.decision];
  $("#result-empty").hidden = true;
  $("#result-content").hidden = false;
  $("#decision-label").textContent = copy.label;
  $("#decision-badge").textContent = copy.badge;
  $("#decision-badge").style.color = copy.color;
  $("#decision-badge").style.backgroundColor = `${copy.color}18`;
  $("#score-number").textContent = result.score;
  $("#score-fill").style.width = `${result.score}%`;
  $("#score-fill").style.backgroundColor = copy.color;
  $(".review-cut").style.left = `${thresholds.review_min}%`;
  $(".approve-cut").style.left = `${thresholds.approval_min}%`;
  $("#model-version").textContent = `modelo ${result.model_version} · probabilidad ${percent(result.probability_good)}`;
  $("#reason-list").innerHTML = result.reason_codes.map((reason) => `<li>${reason}</li>`).join("");
  $("#sensitivity-list").innerHTML = result.sensitivity
    .map(
      (item) => `
        <div class="sensitivity-item">
          <span>${item.feature}</span>
          <strong>${item.effect_points >= 0 ? "+" : ""}${item.effect_points.toFixed(2)} pts</strong>
        </div>`,
    )
    .join("");
  $("#result-disclaimer").textContent = result.disclaimer;
}

function bindForm() {
  const form = $("#score-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const error = $("#form-error");
    const button = form.querySelector("button[type='submit']");
    error.hidden = true;
    button.disabled = true;
    button.querySelector("span:first-child").textContent = "Calculando…";
    const payload = serializeForm(form);
    try {
      const result = await fetchJson("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      renderResult(result, { review_min: 40, approval_min: 70 });
      refreshOperations();
    } catch (requestError) {
      error.textContent = requestError.message;
      error.hidden = false;
      refreshOperations();
    } finally {
      button.disabled = false;
      button.querySelector("span:first-child").textContent = "Calcular score académico";
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindForm();
  loadModelCard();
});
