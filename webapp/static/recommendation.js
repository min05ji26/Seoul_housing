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
const condBarEl    = document.getElementById("rec-condition-bar");
const topCardWrap  = document.getElementById("rec-top-card-wrap");
const gridEl       = document.getElementById("rec-grid");
const avgSectionEl = document.getElementById("rec-avg-section");
const avgContentEl = document.getElementById("rec-avg-content");
const navBadgeEl   = document.getElementById("rec-count-badge");
const condSideEl   = document.getElementById("rec-conditions-sidebar");
const condChipsEl  = document.getElementById("rec-cond-chips");
const countBtnEl   = document.getElementById("rec-count-btn");
const sortBtnEl    = document.getElementById("rec-sort-btn");
const viewBtns     = document.querySelectorAll(".rec-view-btn");
const mapViewEl    = document.getElementById("rec-map-view");
const cardsContainerSelector = "#rec-top-card-wrap, #rec-grid";

// ── 상태 ─────────────────────────────────────────────────
let _allResults = [];   // 원본 결과 (정렬 전)
let _seoulAvg   = null;
let _currentSort = "score";  // score | commute | price
let _currentView = "card";   // card | map

// ── 초기화 ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const sessionId = localStorage.getItem("rec_session_id");
  if (!sessionId) {
    showState("no-session");
    return;
  }
  attachControlHandlers();
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

    if (res.status === 400) {
      // 세션 만료 — 챗봇 페이지로 안내
      showError("세션이 만료됐어요. 챗봇에서 조건을 다시 입력해 주세요.", true);
      return;
    }
    if (!res.ok || data.error) {
      const rawErr = data.error || "";
      let displayErr = "추천 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.";
      if (rawErr.includes("kakao") || rawErr.includes("ConnectionPool") || rawErr.includes("getaddrinfo"))
        displayErr = "주소 검색 서비스에 연결할 수 없어요.\n네트워크 연결을 확인하고 다시 시도해 주세요.";
      else if (rawErr.includes("슬롯 미완성"))
        displayErr = "조건 입력이 완료되지 않았어요. 챗봇에서 조건을 먼저 입력해 주세요.";
      showError(displayErr);
      return;
    }

    _allResults = data.results  || [];
    _seoulAvg   = data.seoul_avg || null;

    if (!_allResults.length) {
      showError("조건에 맞는 추천 결과가 없어요. 조건을 조정해 보세요.");
      return;
    }

    renderPage();
  } catch (err) {
    showError("서버에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.");
    console.error(err);
  }
}

// ── 컨트롤 이벤트 ─────────────────────────────────────────
function attachControlHandlers() {
  // 정렬 토글
  if (sortBtnEl) {
    sortBtnEl.addEventListener("click", () => {
      const order = ["score", "commute", "price"];
      const idx = order.indexOf(_currentSort);
      _currentSort = order[(idx + 1) % order.length];
      const labelMap = { score: "종합", commute: "통근", price: "가격" };
      sortBtnEl.textContent = `정렬: ${labelMap[_currentSort]} ▼`;
      renderPage();
    });
  }
  // 카드뷰/지도뷰
  viewBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      _currentView = btn.dataset.view;
      viewBtns.forEach(b => b.classList.toggle("active", b.dataset.view === _currentView));
      const isMap = _currentView === "map";
      mapViewEl.style.display = isMap ? "flex" : "none";
      topCardWrap.style.display = isMap ? "none" : "";
      gridEl.style.display = isMap ? "none" : "";
      avgSectionEl.style.display = isMap ? "none" : (avgContentEl.children.length ? "block" : "none");
    });
  });
}

// ── 정렬 ─────────────────────────────────────────────────
function sortedResults() {
  const sorted = [..._allResults];
  if (_currentSort === "score") {
    sorted.sort((a, b) => (b.score || 0) - (a.score || 0));
  } else if (_currentSort === "commute") {
    sorted.sort((a, b) => (a.commute_min || 999) - (b.commute_min || 999));
  } else if (_currentSort === "price") {
    sorted.sort((a, b) => priceForSort(a) - priceForSort(b));
  }
  return sorted;
}
function priceForSort(r) {
  if (r.rent_type === "월세" && r.monthly_rent_manwon) return r.monthly_rent_manwon;
  return r.deposit_manwon || r.price_manwon || 0;
}

// ── 전체 페이지 렌더링 ───────────────────────────────────
function renderPage() {
  const results = sortedResults();

  // 사이드바 매물 수 배지
  if (navBadgeEl) {
    navBadgeEl.textContent = results.length;
    navBadgeEl.style.display = "";
  }
  localStorage.setItem("rec_result_count", String(results.length));

  // 컨트롤 카운트 버튼 라벨
  if (countBtnEl) countBtnEl.textContent = `추천 개수: ${results.length}개 ▼`;

  // 검색 조건 바
  renderConditionBar();

  // 1위 hero 카드
  topCardWrap.innerHTML = renderTopCard(results[0], 0);

  // 2~N위 그리드
  const rest = results.slice(1);
  gridEl.innerHTML = rest.map((r, i) => renderRestCard(r, i)).join("")
                     + renderMoreCard(results.length);

  // 서울 평균 비교
  if (_seoulAvg) renderAvgSection(_seoulAvg, results);

  showState("results");
}

// ── 조건 바 렌더링 (localStorage 기반) ──────────────────
function renderConditionBar() {
  const chips = JSON.parse(localStorage.getItem("rec_cond_chips") || "[]");
  if (!chips.length) {
    condBarEl.style.display = "none";
    // 사이드바도 숨김
    if (condSideEl) condSideEl.style.display = "none";
    return;
  }
  condBarEl.style.display = "flex";
  condBarEl.innerHTML = chips
    .map((c, i) => `<span>${escHtml(c)}</span>${i < chips.length - 1 ? '<span class="rec-cond-sep">•</span>' : ''}`)
    .join("");

  // 사이드바 조건 칩
  if (condChipsEl && chips.length) {
    condSideEl.style.display = "block";
    condChipsEl.innerHTML = chips.map(c =>
      `<div class="search-condition">${escHtml(c)}</div>`
    ).join("");
  }
}

// ── 1위 hero 카드 ───────────────────────────────────────
function renderTopCard(r, idx) {
  if (!r) return "";
  const score    = (r.score != null ? r.score : 0);
  const commute  = r.commute_min != null ? r.commute_min : "–";
  const cost     = r.cost_score != null ? r.cost_score : 0;
  const infra    = r.infra_score != null ? r.infra_score : 0;
  const safety   = r.safety_score != null ? r.safety_score : null;
  const detailParts = [];
  if (r.house_type) detailParts.push(escHtml(r.house_type));
  if (r.area_m2)    detailParts.push(`${r.area_m2}㎡`);
  if (r.rent_type)  detailParts.push(escHtml(r.rent_type));

  const priceLine = formatPriceLine(r);
  const policyHtml = r.policy_matched && r.policy_matched.length
    ? `<div class="rec-policy">💚 청년정책 ${r.policy_matched.length}건 적용 가능 — ${escHtml(r.policy_matched[0].name)}</div>`
    : "";

  // 점수바 (4축, safety는 데이터 있으면만)
  const scoreRows = [
    scoreRow("통근", commute, 60, true),
    scoreRow("주거비", cost, 100, false),
    scoreRow("인프라", infra, 100, false),
  ];
  if (safety != null) scoreRows.push(scoreRow("안전", safety, 100, false));

  // 태그칩
  const tags = [];
  if (r.policy_score) tags.push(`📋 청년정책 ${r.policy_score}점`);
  if (r.infra_score)  tags.push(`🏪 편의시설 ${r.infra_score}점`);
  if (commute !== "–") tags.push(`🚇 통근 ${commute}분`);

  const fullPolicies = renderFullPolicies(r.policy_matched);

  return `
    <div class="rec-top-card">
      <div class="rec-top-image">
        <div class="rec-rank-badge">🏆 1위 추천</div>
        <div class="rec-score-badge">⭐ ${score}</div>
        <span style="font-size:64px">🏢</span>
        <button class="rec-heart-btn" data-id="${idx}" onclick="toggleFav(this)" aria-label="찜">🤍</button>
      </div>
      <div class="rec-top-content">
        <div class="rec-address">📍 ${escHtml(r.address || (r.gu + " " + r.dong))}</div>
        <div class="rec-detail">${detailParts.join(" · ") || "주택 유형 정보 없음"}</div>
        <div class="rec-price">${priceLine}</div>
        <div class="rec-mgmt">시세 통계 기반 추정 (실제 매물은 직방·다방·네이버부동산에서 확인)</div>

        <div class="rec-scores">
          ${scoreRows.join("")}
        </div>

        ${policyHtml}

        <div class="rec-tags">
          ${tags.map(t => `<span class="rec-tag">${t}</span>`).join("")}
        </div>

        ${fullPolicies}
      </div>
    </div>
  `;
}

// ── 2~N위 카드 ──────────────────────────────────────────
function renderRestCard(r, i) {
  const colorMap = ["blue", "green", "gray"];
  const color    = colorMap[i % colorMap.length];
  const rank     = i + 2;
  const score    = r.score != null ? r.score : 0;
  const priceLine = formatPriceLineCompact(r);
  const commute  = r.commute_min != null ? r.commute_min : "–";

  const policyBadge = r.policy_matched && r.policy_matched.length
    ? `<div class="rec-card-policy">💚 청년정책 ${r.policy_matched.length}건 적용 가능</div>`
    : "";

  return `
    <div class="rec-card">
      <div class="rec-card-image ${color}">
        <div class="rec-rank-badge">${rank}위</div>
        <div class="rec-score-badge">⭐ ${score}</div>
        <span>🏠</span>
        <button class="rec-heart-btn" data-id="${i+1}" onclick="toggleFav(this)" aria-label="찜">🤍</button>
      </div>
      <div class="rec-card-body">
        <div class="rec-card-rank">${rank}위 추천</div>
        <div class="rec-card-addr">${escHtml(r.address || (r.gu + " " + r.dong))}</div>
        <div class="rec-card-price">${priceLine}</div>
        <div class="rec-card-info">🚇 통근 ${commute}분 · 🏪 인프라 ${r.infra_score || 0}점 · ⭐ ${score}점</div>
        ${policyBadge}
      </div>
    </div>
  `;
}

// ── 더보기 카드 ─────────────────────────────────────────
function renderMoreCard(currentCount) {
  if (currentCount >= 10) return "";
  return `
    <div class="rec-more-card" onclick="onMoreCardClick()">
      <span style="font-size:40px">🏙️</span>
      <div class="rec-more-title">추천 개수 늘리기</div>
      <div class="rec-more-sub">더 많은 매물 보기</div>
      <button class="rec-more-btn">추천 ${currentCount < 5 ? 5 : 10}개로 늘리기 ▼</button>
    </div>
  `;
}
function onMoreCardClick() {
  // TODO: 실제 서버에 final_recommend_count 늘려서 재요청
  alert("더 많은 매물 보기 기능은 준비 중이에요.\n현재 추천 결과는 상위 5개입니다.");
}

// ── 청년정책 풀 카드 (1위 카드 안) ──────────────────────
function renderFullPolicies(policies) {
  if (!policies || !policies.length) return "";
  const items = policies.map(p => {
    const savingText = p.saving > 0 ? `월 약 ${p.saving}만원 절감` : "";
    const dupBadge   = p.dup ? `<span class="rec-policy-dup">중복제한</span>` : "";
    const linkAttr   = p.url ? `href="${escHtml(p.url)}" target="_blank" rel="noopener"` : "";
    const nameHtml   = p.url
      ? `<a class="rec-policy-name" ${linkAttr}>${escHtml(p.name)} ↗</a>`
      : `<span class="rec-policy-name">${escHtml(p.name)}</span>`;
    return `
      <div class="rec-policy-item">
        <div class="rec-policy-top">${nameHtml}${dupBadge}</div>
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
      <div class="rec-policy-list">${items}</div>
    </div>
  `;
}

// ── 점수바 한 줄 ────────────────────────────────────────
function scoreRow(label, value, max, asMinutes) {
  if (value == null) return "";
  let pct, displayVal;
  if (asMinutes) {
    pct = Math.max(0, 100 - (value / max) * 100);  // 통근시간은 적을수록 점수 높음
    displayVal = `${value}분`;
  } else {
    pct = Math.min(100, Math.max(0, value));
    displayVal = `${value}점`;
  }
  return `
    <div class="rec-score-row">
      <span>${label}</span>
      <div class="rec-score-bar"><div class="rec-score-fill" style="width:${pct}%"></div></div>
      <span class="rec-score-num">${displayVal}</span>
    </div>
  `;
}

// ── 가격 표시 ───────────────────────────────────────────
function formatPriceLine(r) {
  if (r.rent_type === "월세" && r.monthly_rent_manwon) {
    return `보증금 ${formatManwon(r.deposit_manwon)} / 월세 ${r.monthly_rent_manwon}만원`;
  }
  if (r.rent_type === "전세") {
    return `전세 ${formatManwon(r.deposit_manwon)}`;
  }
  return formatManwon(r.deposit_manwon || r.price_manwon);
}
function formatPriceLineCompact(r) {
  if (r.rent_type === "월세" && r.monthly_rent_manwon) {
    return `월 ${r.monthly_rent_manwon}만 / 보증 ${formatManwon(r.deposit_manwon, true)}`;
  }
  return formatManwon(r.deposit_manwon || r.price_manwon);
}
function formatManwon(manwon, compact) {
  if (!manwon) return "–";
  const n = Math.round(Number(manwon));
  if (n >= 10000) {
    const ok  = Math.floor(n / 10000);
    const rem = n % 10000;
    if (compact) return rem > 0 ? `${ok}억 ${rem.toLocaleString()}만` : `${ok}억`;
    return rem > 0 ? `${ok}억 ${rem.toLocaleString()}만원` : `${ok}억원`;
  }
  return compact ? `${n.toLocaleString()}만` : `${n.toLocaleString()}만원`;
}

// ── 즐겨찾기 토글 ────────────────────────────────────────
function toggleFav(btn) {
  if (!btn) return;
  const filled = btn.textContent.trim() === "❤️";
  btn.textContent = filled ? "🤍" : "❤️";
  // localStorage 저장 (id 기반)
  const id = btn.dataset.id || "";
  const favs = JSON.parse(localStorage.getItem("rec_favs") || "[]");
  if (filled) {
    const idx = favs.indexOf(id);
    if (idx >= 0) favs.splice(idx, 1);
  } else {
    if (!favs.includes(id)) favs.push(id);
  }
  localStorage.setItem("rec_favs", JSON.stringify(favs));
}
window.toggleFav = toggleFav;
window.onMoreCardClick = onMoreCardClick;

// ── 서울 평균 비교 ──────────────────────────────────────
function renderAvgSection(seoulAvg, results) {
  try {
    const avgPrice   = seoulAvg?.avg_deposit ?? seoulAvg?.median_deposit ?? null;
    const avgCommute = seoulAvg?.avg_commute  ?? null;
    if (!avgPrice && !avgCommute) return;

    const top1 = results[0];
    const items = [];
    const top1Price = top1?.deposit_manwon || top1?.price_manwon;
    if (avgPrice && top1Price) {
      const diff = Math.round(top1Price - avgPrice);
      const sign = diff < 0 ? "▼" : "▲";
      const cls  = diff < 0 ? "rec-avg-good" : "rec-avg-bad";
      items.push(`<div class="rec-avg-row">
        <span class="rec-avg-label">💰 보증금</span>
        <span>서울 평균 <b>${formatManwon(avgPrice)}</b> 대비</span>
        <span class="${cls}">${sign} ${formatManwon(Math.abs(diff))}</span>
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

function showError(msg, gotoChat) {
  errorMsgEl.textContent = msg;
  if (gotoChat) {
    const retryBtn = errorEl.querySelector(".rec-retry-btn");
    if (retryBtn) retryBtn.textContent = "챗봇으로 가기";
  }
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
