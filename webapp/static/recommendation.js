"use strict";

// ── 인증 토큰 ────────────────────────────────────────────
function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return token
    ? { "Content-Type": "application/json", "Authorization": "Bearer " + token }
    : { "Content-Type": "application/json" };
}

// ── DOM ──────────────────────────────────────────────────
const loadingEl    = document.getElementById("rec-loading");
const errorEl      = document.getElementById("rec-error");
const errorMsgEl   = document.getElementById("rec-error-msg");
const noSessionEl  = document.getElementById("rec-no-session");
const resultsEl    = document.getElementById("rec-results");
const summaryEl    = document.getElementById("rec-summary-bar");
const cardsEl      = document.getElementById("rec-cards");
const avgSectionEl = document.getElementById("rec-avg-section");
const avgContentEl = document.getElementById("rec-avg-content");
const badgeEl      = document.getElementById("rec-count-badge");
const condSideEl   = document.getElementById("rec-conditions-sidebar");
const condChipsEl  = document.getElementById("rec-cond-chips");

// ── 초기화 ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sessionId = localStorage.getItem("rec_session_id");
  if (!sessionId) {
    showState("no-session");
    return;
  }
  loadResults(sessionId);
});

// ── 결과 로드 ────────────────────────────────────────────
async function loadResults(sessionId) {
  showState("loading");
  try {
    const res  = await fetch("/api/recommend", {
      method:  "POST",
      headers: getAuthHeaders(),
      body:    JSON.stringify({ session_id: sessionId }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "추천 중 오류가 발생했어요.");
      return;
    }

    renderPage(data);
  } catch (err) {
    showError("서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.");
    console.error(err);
  }
}

// ── 전체 페이지 렌더링 ───────────────────────────────────
function renderPage(data) {
  const results  = data.results  || [];
  const seoulAvg = data.seoul_avg;

  if (!results.length) {
    showError("조건에 맞는 추천 결과가 없어요. 조건을 조정해 보세요.");
    return;
  }

  // 배지
  if (badgeEl) { badgeEl.textContent = results.length; badgeEl.style.display = ""; }

  // 검색 조건 요약 바
  renderSummaryBar(results);

  // 결과 카드
  cardsEl.innerHTML = results.map((r, i) => renderCard(r, i)).join("");

  // 서울 평균 비교
  if (seoulAvg) renderAvgSection(seoulAvg, results);

  showState("results");
}

// ── 검색 조건 요약 바 ────────────────────────────────────
function renderSummaryBar(results) {
  // localStorage에 저장된 조건 칩 재사용
  const chips = JSON.parse(localStorage.getItem("rec_cond_chips") || "[]");
  if (!chips.length) {
    summaryEl.style.display = "none";
    return;
  }
  summaryEl.innerHTML = `
    <div class="rec-summary-inner">
      <span class="rec-summary-label">검색 조건</span>
      <div class="rec-summary-chips">
        ${chips.map(c => `<span class="rec-summary-chip">${escHtml(c)}</span>`).join("")}
      </div>
      <a href="/" class="rec-rerun-btn">조건 변경</a>
    </div>
  `;

  // 사이드바 조건 칩
  if (condChipsEl && chips.length) {
    condSideEl.style.display = "block";
    condChipsEl.innerHTML = chips.map(c =>
      `<div class="search-condition">${escHtml(c)}</div>`
    ).join("");
  }
}

// ── 결과 카드 ────────────────────────────────────────────
function renderCard(r, i) {
  const rank      = i + 1;
  const loc       = [r.gu, r.dong].filter(Boolean).join(" ");
  const houseType = r.house_type || "";
  const commute   = r.commute_min != null ? r.commute_min : "–";
  const price     = formatPrice(r.price_manwon);
  const score     = r.score != null ? (parseFloat(r.score) * 100).toFixed(0) : "–";

  const infraScore  = r.infra_score  != null ? parseFloat(r.infra_score)  : null;
  const policyScore = r.policy_score != null ? parseFloat(r.policy_score) : null;

  // 점수 바
  const scorePct   = Math.min(parseFloat(r.score || 0) * 100, 100).toFixed(0);
  const infraPct   = infraScore  != null ? Math.min(infraScore,  100).toFixed(0) : null;
  const policyPct  = policyScore != null ? Math.min(policyScore, 100).toFixed(0) : null;

  // 순위 색상
  const rankColors = { 1: "#3ECF8E", 2: "#60a5fa", 3: "#f59e0b" };
  const rankColor  = rankColors[rank] || "#9CA3AF";

  // 청년정책 매칭 섹션
  const policies   = Array.isArray(r.policy_matched) ? r.policy_matched : [];
  const policyHtml = policies.length > 0 ? renderPolicies(policies) : "";

  return `
    <div class="rec-card" data-rank="${rank}">
      <div class="rec-card-top">
        <div class="rec-rank-badge" style="background:${rankColor}">#${rank}</div>
        <div class="rec-card-loc-wrap">
          <div class="rec-card-loc">${escHtml(loc)}</div>
          ${houseType ? `<span class="rec-type-tag">${escHtml(houseType)}</span>` : ""}
        </div>
        <div class="rec-total-score">
          <span class="rec-score-num">${score}</span>
          <span class="rec-score-unit">점</span>
        </div>
      </div>

      <div class="rec-card-stats">
        <div class="rec-stat">
          <span class="rec-stat-icon">🕐</span>
          <span class="rec-stat-label">통근</span>
          <span class="rec-stat-val">${commute}분</span>
        </div>
        <div class="rec-stat-divider"></div>
        <div class="rec-stat">
          <span class="rec-stat-icon">💰</span>
          <span class="rec-stat-label">${r.price_manwon > 1000 ? "전세" : "보증금"}</span>
          <span class="rec-stat-val">${price}</span>
        </div>
      </div>

      <div class="rec-score-bars">
        <div class="rec-score-row">
          <span class="rec-score-label">종합</span>
          <div class="rec-bar-track">
            <div class="rec-bar-fill" style="width:${scorePct}%;background:var(--green)"></div>
          </div>
          <span class="rec-score-pct">${scorePct}</span>
        </div>
        ${infraPct != null ? `
        <div class="rec-score-row">
          <span class="rec-score-label">인프라</span>
          <div class="rec-bar-track">
            <div class="rec-bar-fill" style="width:${infraPct}%;background:#60a5fa"></div>
          </div>
          <span class="rec-score-pct">${infraPct}</span>
        </div>` : ""}
        ${policyPct != null && policyScore > 0 ? `
        <div class="rec-score-row">
          <span class="rec-score-label">청년정책</span>
          <div class="rec-bar-track">
            <div class="rec-bar-fill" style="width:${policyPct}%;background:#f59e0b"></div>
          </div>
          <span class="rec-score-pct">${policyPct}</span>
        </div>` : ""}
      </div>

      ${policyHtml}
    </div>
  `;
}

// ── 청년정책 목록 렌더링 ─────────────────────────────────
function renderPolicies(policies) {
  const items = policies.map(p => {
    const savingText = p.saving > 0 ? `월 약 ${p.saving}만원 절감` : "";
    const dupBadge   = p.dup ? `<span class="rec-policy-dup">중복제한</span>` : "";
    const linkAttr   = p.url ? `href="${escHtml(p.url)}" target="_blank" rel="noopener"` : "";
    const nameHtml   = p.url
      ? `<a class="rec-policy-name" ${linkAttr}>${escHtml(p.name)} ↗</a>`
      : `<span class="rec-policy-name">${escHtml(p.name)}</span>`;

    return `
      <div class="rec-policy-item">
        <div class="rec-policy-top">
          ${nameHtml}
          ${dupBadge}
        </div>
        ${p.benefit ? `<div class="rec-policy-desc">${escHtml(p.benefit)}</div>` : ""}
        ${savingText ? `<div class="rec-policy-saving">💰 ${escHtml(savingText)}</div>` : ""}
      </div>
    `;
  }).join("");

  return `
    <div class="rec-policy-section">
      <div class="rec-policy-header">
        <span class="rec-policy-icon">📋</span>
        <span>매칭된 청년정책 ${policies.length}건</span>
      </div>
      <div class="rec-policy-list">
        ${items}
      </div>
    </div>
  `;
}

// ── 서울 평균 비교 ────────────────────────────────────────
function renderAvgSection(seoulAvg, results) {
  try {
    const avgPrice   = seoulAvg?.avg_deposit ?? seoulAvg?.median_deposit ?? null;
    const avgCommute = seoulAvg?.avg_commute  ?? null;
    if (!avgPrice && !avgCommute) return;

    const top1 = results[0];
    const items = [];
    if (avgPrice && top1?.price_manwon) {
      const diff = Math.round(top1.price_manwon - avgPrice);
      const sign = diff < 0 ? "▼" : "▲";
      const cls  = diff < 0 ? "rec-avg-good" : "rec-avg-bad";
      items.push(`<div class="rec-avg-row">
        <span class="rec-avg-label">💰 전세 보증금</span>
        <span>서울 평균 <b>${formatPrice(avgPrice)}</b> 대비</span>
        <span class="${cls}">${sign} ${formatPrice(Math.abs(diff))}</span>
      </div>`);
    }
    if (avgCommute && top1?.commute_min) {
      const diff = Math.round(top1.commute_min - avgCommute);
      const sign = diff < 0 ? "▼" : "▲";
      const cls  = diff < 0 ? "rec-avg-good" : "rec-avg-bad";
      items.push(`<div class="rec-avg-row">
        <span class="rec-avg-label">🕐 통근 시간</span>
        <span>서울 평균 <b>${Math.round(avgCommute)}분</b> 대비</span>
        <span class="${cls}">${sign} ${Math.abs(diff)}분</span>
      </div>`);
    }
    if (!items.length) return;

    avgContentEl.innerHTML = items.join("");
    avgSectionEl.style.display = "block";
  } catch (e) { /* 평균 없으면 조용히 숨김 */ }
}

// ── 상태 전환 ────────────────────────────────────────────
function showState(state) {
  loadingEl.style.display   = state === "loading"    ? "flex"  : "none";
  errorEl.style.display     = state === "error"      ? "flex"  : "none";
  noSessionEl.style.display = state === "no-session" ? "flex"  : "none";
  resultsEl.style.display   = state === "results"    ? "block" : "none";
}

function showError(msg) {
  errorMsgEl.textContent = msg;
  showState("error");
}

// ── 유틸 ────────────────────────────────────────────────
function escHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatPrice(manwon) {
  if (!manwon) return "–";
  const n = Math.round(Number(manwon));
  if (n >= 10000) {
    const ok  = Math.floor(n / 10000);
    const rem = n % 10000;
    return rem > 0 ? `${ok}억 ${rem.toLocaleString()}만원` : `${ok}억원`;
  }
  return `${n.toLocaleString()}만원`;
}
