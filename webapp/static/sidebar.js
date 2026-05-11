(function () {
  // 현재 페이지 경로로 active 판단
  const path = location.pathname;

  const html = `
    <nav id="sidebar">
      <div class="sidebar-brand">
        <div class="brand-icon">🏠</div>
        <div class="brand-text">
          <div class="brand-name">집찾봇</div>
          <div class="brand-sub">청년 주거 추천</div>
        </div>
      </div>

      <div class="sidebar-section">
        <div class="sidebar-label">메인</div>
        <a class="nav-item ${path === '/' ? 'active' : ''}" href="/">
          <span class="nav-left"><span class="nav-icon">💬</span> 챗봇으로 찾기</span>
        </a>
        <a class="nav-item ${path === '/recommendation' ? 'active' : ''}" id="nav-rec" href="/recommendation">
          <span class="nav-left"><span class="nav-icon">🏠</span> 주거 추천</span>
          <span class="nav-badge" id="nav-rec-badge" style="display:none"></span>
        </a>
        <a class="nav-item ${path === '/recommendation' ? '' : 'disabled'}" id="nav-map" href="#">
          <span class="nav-left"><span class="nav-icon">🗺️</span> 지도뷰</span>
        </a>
      </div>

      <div id="current-conditions" style="display:none">
        <div class="sidebar-label">현재 검색 조건</div>
        <div id="condition-chips"></div>
      </div>

      <div class="sidebar-bottom">
        <div class="sidebar-label">계정</div>
        <a class="nav-item ${path === '/mypage' ? 'active' : ''}" href="/mypage">
          <span class="nav-left"><span class="nav-icon">👤</span> 내 정보</span>
        </a>
        <a class="nav-item ${path === '/favorites' ? 'active' : ''}" href="/favorites">
          <span class="nav-left"><span class="nav-icon">❤️</span> 찜 목록</span>
          <span class="nav-badge" id="nav-fav-badge" style="display:none"></span>
        </a>
        <a class="nav-item" href="#" id="sidebar-logout-btn">
          <span class="nav-left"><span class="nav-icon">🚪</span> 로그아웃</span>
        </a>
        <div class="user-chip">
          <div class="user-avatar">🐻</div>
          <div>
            <div class="user-name" id="sidebar-username">사용자님</div>
            <div class="user-sub" id="sidebar-usersub">청년 주거 탐색 중</div>
          </div>
        </div>
      </div>
    </nav>
  `;

  // #app 첫 번째 자식으로 사이드바 삽입
  function inject() {
    // 변경
    const app = document.getElementById('app') || document.getElementById('app-rec');
    if (!app) return;
    const existing = document.getElementById('sidebar');
    if (existing) existing.remove();
    app.insertAdjacentHTML('afterbegin', html);

    // app-rec이면 rec-main이 두 번째 칼럼에 오도록 순서 보정
    const recMain = document.getElementById('rec-main');
    if (recMain) app.appendChild(recMain);
        // 기존 사이드바 있으면 교체
    const existing = document.getElementById('sidebar');
    if (existing) existing.remove();
    app.insertAdjacentHTML('afterbegin', html);
    bindEvents();
    renderUserInfo();
    renderBadges();
    renderSearchCondition();
  }

  function bindEvents() {
    const logoutBtn = document.getElementById('sidebar-logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', e => {
        e.preventDefault();
        ['token','user_id','nickname','workplace','last_search',
         'rec_result_count','rec_session_id','rec_favs'].forEach(k => localStorage.removeItem(k));
        location.href = '/login';
      });
    }
  }

  function renderUserInfo() {
    const nick = localStorage.getItem('nickname') || '사용자';
    const el = document.getElementById('sidebar-username');
    if (el) el.textContent = nick + '님';

    const workplace = localStorage.getItem('workplace') || '';
    const sub = document.getElementById('sidebar-usersub');
    if (sub && workplace) sub.textContent = workplace + ' 직장인';
  }

  async function renderBadges() {
    const userId = parseInt(localStorage.getItem('user_id') || '0');
    if (!userId) return;
    const token = localStorage.getItem('token') || '';

    // 찜 배지
    try {
      const res  = await fetch(`/favorites/keys?user_id=${userId}`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      const count = (data.keys || []).length;
      const badge = document.getElementById('nav-fav-badge');
      if (badge && count > 0) {
        badge.textContent = count;
        badge.style.display = '';
      }
    } catch(e) {}

    // 추천 배지
    const recCount = localStorage.getItem('rec_result_count');
    if (recCount) {
      const badge = document.getElementById('nav-rec-badge');
      if (badge) {
        badge.textContent = recCount;
        badge.style.display = '';
      }
    }
  }

  function renderSearchCondition() {
    const raw = localStorage.getItem('last_search');
    if (!raw) return;
    try {
      const s = JSON.parse(raw);
      if (!s.workplace) return;
      const box = document.getElementById('current-conditions');
      const chips = document.getElementById('condition-chips');
      if (!box || !chips) return;
      chips.innerHTML = [
        s.workplace ? `<div class="search-condition">📍 ${s.workplace}</div>` : '',
        s.budget    ? `<div class="search-condition">💰 ${s.budget}</div>` : '',
        s.commute_time ? `<div class="search-condition">🚇 통근 ${s.commute_time}분 이내</div>` : '',
      ].join('');
      box.style.display = 'block';
    } catch(e) {}
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inject);
  } else {
    inject();
  }
})();