"use strict";

// ── 상태 ─────────────────────────────────────────────────
let sessionId = null;
let isWaiting = false;

// ── 인증 토큰 ────────────────────────────────────────────
function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return token
    ? { "Content-Type": "application/json", "Authorization": "Bearer " + token }
    : { "Content-Type": "application/json" };
}

// ── DOM ──────────────────────────────────────────────────
const messagesEl     = document.getElementById("messages");
const inputEl        = document.getElementById("user-input");
const sendBtn        = document.getElementById("send-btn");
const quickOptEl     = document.getElementById("quick-options");
const progressListEl = document.getElementById("progress-list");
const condTableEl    = document.getElementById("condition-table");
const condChipsEl    = document.getElementById("condition-chips");
const resultsBtnEl   = document.getElementById("result-btn");
const resultsSectionEl = document.getElementById("results-section");
const resultsListEl  = document.getElementById("results-list");

// 진행도 항목 정의 (순서 = 챗봇 질문 순서)
const PROGRESS_STEPS = [
  { key: "work_address",     label: "직장 위치" },
  { key: "budget",           label: "예산" },
  { key: "allowed_minutes",  label: "통근 허용 시간" },
  { key: "house_type",       label: "주택 유형" },
  { key: "weight_preference",label: "우선순위 선택" },
];

// ── 초기화 ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderProgressList([]);
  renderConditionTable([]);
  appendBotMessage(
    "안녕하세요! 저는 앱이름이에요 🏠\n\n" +
    "서울시 공공데이터를 기반으로 최적의 주거지를 찾아드릴게요.\n" +
    "몇 가지 질문에 답해주시면 바로 추천해드릴게요!\n\n" +
    "어디서 일하실 예정인가요?\n직장 주소나 지하철역을 알려주세요."
  );
  inputEl.focus();
});

// ── 이벤트 ───────────────────────────────────────────────
sendBtn.addEventListener("click", () => sendMessage());
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  setTimeout(() => {
    inputEl.style.height = "auto";
    inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + "px";
  }, 0);
});

// ── 메시지 전송 ──────────────────────────────────────────
async function sendMessage(text) {
  const userText = (text !== undefined ? text : inputEl.value).trim();
  if (!userText || isWaiting) return;

  inputEl.value = "";
  inputEl.style.height = "auto";
  clearQuickOptions();
  appendUserMessage(userText);
  setWaiting(true);

  try {
    const res  = await fetch("/api/chat", {
      method:  "POST",
      headers: getAuthHeaders(),
      body:    JSON.stringify({ user_message: userText, session_id: sessionId }),
    });
    const data = await res.json();

    sessionId = data.session_id;
    appendBotMessage(data.bot_message);
    updatePanels(data.slot_status);
    renderQuickOptions(data.quick_options);

    if (data.is_complete) {
      resultsBtnEl.classList.add("visible");
      startRecommendation();
    }
  } catch (err) {
    appendBotMessage("오류가 발생했습니다. 잠시 후 다시 시도해 주세요.");
    console.error(err);
  } finally {
    setWaiting(false);
  }
}

// ── 추천 실행 ────────────────────────────────────────────
async function startRecommendation() {
  resultsSectionEl.style.display = "block";
  resultsListEl.innerHTML = `
    <div style="text-align:center;padding:20px;color:#a1a1aa">
      <div class="spinner"></div>
      <div style="margin-top:8px;font-size:0.8rem">추천 계산 중…</div>
    </div>
  `;

  try {
    const res  = await fetch("/api/recommend", {
      method:  "POST",
      headers: getAuthHeaders(),
      body:    JSON.stringify({ session_id: sessionId }),
    });
    const data = await res.json();

    if (data.error) {
      resultsListEl.innerHTML = `<div style="color:#ef4444;font-size:0.82rem">${escHtml(data.error)}</div>`;
      appendBotMessage("추천 중 오류가 발생했어요: " + data.error);
      return;
    }

    renderResults(data.results);
    appendBotMessage(
      `추천이 완료됐어요! 오른쪽 패널에서 결과를 확인해 주세요.\n` +
      `총 ${data.results.length}개 매물을 추천드려요 🏠`
    );
  } catch (err) {
    resultsListEl.innerHTML = `<div style="color:#ef4444;font-size:0.82rem">서버 오류</div>`;
    console.error(err);
  }
}

function scrollToResults() {
  resultsSectionEl.scrollIntoView({ behavior: "smooth" });
}

// ── 말풍선 ───────────────────────────────────────────────
function appendBotMessage(text) {
  removeTyping();
  const group = document.createElement("div");
  group.className = "msg-group bot";
  group.innerHTML = `
    <div class="bubble bot">${nl2br(escHtml(text))}</div>
    <div class="msg-time">${nowTime()}</div>
  `;
  messagesEl.appendChild(group);
  scrollBottom();
}

function appendUserMessage(text) {
  const group = document.createElement("div");
  group.className = "msg-group user";
  group.innerHTML = `
    <div class="bubble user">${nl2br(escHtml(text))}</div>
    <div class="msg-time">${nowTime()}</div>
  `;
  messagesEl.appendChild(group);
  scrollBottom();
}

function showTyping() {
  removeTyping();
  const group = document.createElement("div");
  group.id = "typing-row";
  group.className = "msg-group bot";
  group.innerHTML = `<div class="bubble bot typing-dots"><span></span><span></span><span></span></div>`;
  messagesEl.appendChild(group);
  scrollBottom();
}

function removeTyping() {
  const el = document.getElementById("typing-row");
  if (el) el.remove();
}

function setWaiting(v) {
  isWaiting = v;
  sendBtn.disabled = v;
  inputEl.disabled = v;
  if (v) showTyping();
}

function scrollBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ── 빠른 옵션 ────────────────────────────────────────────
function renderQuickOptions(options) {
  clearQuickOptions();
  if (!options || !options.length) return;
  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.className = "quick-btn";
    btn.textContent = opt.label;
    btn.onclick = () => sendMessage(opt.value);
    quickOptEl.appendChild(btn);
  });
}

function clearQuickOptions() {
  quickOptEl.innerHTML = "";
}

// ── 패널 업데이트 ────────────────────────────────────────
function updatePanels(slots) {
  if (!slots) return;
  renderProgressList(slots);
  renderConditionTable(slots);
  updateSidebarConditions(slots);
}

// 진행도 리스트
function renderProgressList(slots) {
  const filled = {};
  (slots || []).forEach(s => { if (s.filled) filled[s.key] = s.value; });

  // budget 특수 처리: deposit + monthly
  const hasBudget = filled["deposit_manwon"] || filled["rent_type"];
  if (hasBudget) filled["budget"] = budgetLabel(filled);

  let html = "";
  let foundCurrent = false;
  PROGRESS_STEPS.forEach((step, i) => {
    const isDone = !!filled[step.key];
    let cls, icon;
    if (isDone) {
      cls = "done"; icon = "✓";
    } else if (!foundCurrent) {
      foundCurrent = true;
      cls = "current"; icon = String(i + 1);
    } else {
      cls = "pending"; icon = String(i + 1);
    }
    const valueHtml = isDone && filled[step.key] !== true
      ? `<span class="prog-value">${escHtml(String(filled[step.key]))}</span>` : "";
    html += `
      <div class="progress-item">
        <div class="prog-badge ${cls}">${icon}</div>
        <span class="prog-label ${cls}">${escHtml(step.label)}</span>
        ${valueHtml}
      </div>
    `;
  });
  progressListEl.innerHTML = html;
}

// 입력된 조건 테이블
function renderConditionTable(slots) {
  const map = {};
  (slots || []).forEach(s => { map[s.key] = s; });

  const rows = [
    { key: "work_address",  label: "직장" },
    { key: "budget",        label: "예산",   virtual: true },
    { key: "allowed_minutes", label: "통근" },
    { key: "house_type",    label: "유형" },
  ];

  let html = "";
  rows.forEach(r => {
    let val = null;
    if (r.virtual && r.key === "budget") {
      val = budgetLabel(Object.fromEntries((slots||[]).filter(s=>s.filled).map(s=>[s.key, s.value])));
    } else {
      const s = map[r.key];
      val = s && s.filled ? s.value : null;
    }
    const valHtml = val
      ? `<span class="cond-val">${escHtml(String(val))}</span>`
      : `<span class="cond-empty">미입력</span>`;
    html += `<div class="condition-row"><span class="cond-label">${r.label}</span>${valHtml}</div>`;
  });
  condTableEl.innerHTML = html;
}

// 사이드바 현재 검색 조건
function updateSidebarConditions(slots) {
  const map = {};
  (slots || []).forEach(s => { if (s.filled) map[s.key] = s.value; });

  const chips = [];
  if (map.work_address)  chips.push("📍 " + map.work_address);
  if (map.deposit_manwon || map.rent_type) chips.push("💰 " + budgetLabel(map));
  if (map.allowed_minutes) chips.push("🕐 통근 " + map.allowed_minutes + "분 이내");

  if (chips.length) {
    document.getElementById("current-conditions").style.display = "block";
    condChipsEl.innerHTML = chips.map(c =>
      `<div class="search-condition"><span class="dot">•</span>${escHtml(c)}</div>`
    ).join("");
  }
}

function budgetLabel(map) {
  const rt  = map.rent_type;
  const dep = map.deposit_manwon;
  const mon = map.monthly_manwon;
  if (!rt && !dep) return null;
  if (rt === "월세" && mon) return `월세 ${mon}만원↓`;
  if (rt === "월세") return "월세";
  if (dep) return `전세 ${Number(dep).toLocaleString()}만원`;
  return rt || null;
}

// ── 추천 결과 렌더링 ─────────────────────────────────────
function renderResults(results) {
  if (!results || !results.length) {
    resultsListEl.innerHTML = `<p style="font-size:0.82rem;color:#999">결과 없음</p>`;
    return;
  }
  resultsListEl.innerHTML = results.map((r, i) => {
    const tags = [
      r.house_type,
      `통근 ${r.commute_min}분`,
      `${Math.round(r.price_manwon / 100)}백만원`,
      r.infra_score != null ? `인프라 ${parseFloat(r.infra_score).toFixed(0)}점` : null,
      r.policy_score && parseFloat(r.policy_score) > 0 ? `정책 ${parseFloat(r.policy_score).toFixed(0)}점` : null,
    ].filter(Boolean);

    return `
      <div class="result-card">
        <div class="result-rank">#${i + 1}</div>
        <div class="result-loc">${escHtml(r.gu)} ${escHtml(r.dong)}</div>
        <div class="result-tags">
          ${tags.map(t => `<span class="result-tag">${escHtml(t)}</span>`).join("")}
        </div>
      </div>
    `;
  }).join("");
}

// ── 유틸 ─────────────────────────────────────────────────
function escHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function nl2br(s) {
  return s.replace(/\n/g, "<br>");
}

function nowTime() {
  const d = new Date();
  const h = d.getHours(), m = String(d.getMinutes()).padStart(2, "0");
  const ampm = h < 12 ? "오전" : "오후";
  return `${ampm} ${h % 12 || 12}:${m}`;
}
