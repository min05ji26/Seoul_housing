"""
nlp_input_module.py
───────────────────
챗봇 슬롯 추출 + 상태 머신

흐름:
  사용자 자연어 → llm_module.extract_slots_from_text() (Gemini)
              → 정규식 폴백 (API 실패 시 자동)
  슬롯 완성 → get_v5_params() → run_recommendation() kwargs

필수 슬롯:
  work_address, transport_mode, rent_type, deposit_manwon, allowed_minutes
  (월세면 monthly_manwon 추가)

선택 슬롯:
  vibe (list), use_youth_policy (bool), region_filter,
  house_type, weight_preference
"""

import re
from typing import Dict, List, Optional, Any

from vibe_module import extract_vibe_from_text, get_vibe_weights, INFRA_KEYS
from llm_module import extract_slots_from_text


def _parse_commute_minutes(txt: str) -> Optional[int]:
    """다양한 통근 시간 표현 → 편도 분 단위 정수. 파싱 불가·비현실적 값은 None."""
    # 시간+분 결합 (예: 1시간 30분)
    m = re.search(r"(\d+)\s*시간\s*(\d+)\s*분", txt)
    if m:
        minutes = int(m.group(1)) * 60 + int(m.group(2))
    # N시간 반 (예: 1시간 반)
    elif re.search(r"(\d+)\s*시간\s*반", txt):
        m2 = re.search(r"(\d+)\s*시간", txt)
        minutes = int(m2.group(1)) * 60 + 30 if m2 else None
    # 한시간 반
    elif re.search(r"한\s*시간\s*반", txt):
        minutes = 90
    # N시간 (예: 1시간, 1.5시간)
    elif re.search(r"(\d+(?:\.\d+)?)\s*시간", txt):
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*시간", txt)
        minutes = int(float(m2.group(1)) * 60) if m2 else None
    # 한시간
    elif re.search(r"한\s*시간", txt):
        minutes = 60
    # N분 (예: 40분, 편도 60분)
    elif re.search(r"(\d+)\s*분", txt):
        m2 = re.search(r"(\d+)\s*분", txt)
        minutes = int(m2.group(1)) if m2 else None
    # 숫자만 입력 (예: "80" → 80분으로 처리)
    else:
        m2 = re.search(r"^\s*(\d+)\s*$", txt)
        minutes = int(m2.group(1)) if m2 else None

    if minutes is None:
        return None
    # 왕복 → 편도 환산
    if re.search(r"왕복", txt):
        minutes = minutes // 2
    # 비현실적 값 필터
    if minutes < 5 or minutes > 300:
        return None
    return minutes


def _parse_manwon(txt: str) -> Optional[int]:
    """다양한 금액 표현 → 만원 단위 정수. 파싱 불가 시 None."""
    # 억+천만 (예: 1억5천만원, 1억5천)
    m = re.search(r"(\d+)\s*억\s*(\d+)\s*천", txt)
    if m:
        return int(m.group(1)) * 10000 + int(m.group(2)) * 1000
    # 억 단독 (예: 2억, 2억원)
    m = re.search(r"(\d+)\s*억", txt)
    if m:
        return int(m.group(1)) * 10000
    # 천만원 (예: 5천만원, 5천만)
    m = re.search(r"(\d+)\s*천\s*만", txt)
    if m:
        return int(m.group(1)) * 1000
    # 천 단독 (예: 5천, 5천원) — 만원 단위 아닐 수 있으나 보증금 문맥에선 천만원
    m = re.search(r"(\d+)\s*천(?!\s*만)", txt)
    if m:
        return int(m.group(1)) * 1000
    # 만원 직접 (예: 5000만원, 5000만, 5000)
    m = re.search(r"(\d+)\s*만", txt)
    if m:
        return int(m.group(1))
    # 숫자만 (예: 5000)
    m = re.search(r"(\d{3,})", txt)
    if m:
        return int(m.group(1))
    return None

# ──────────────────────────────────────────────────────────
# 슬롯 정의
# ──────────────────────────────────────────────────────────

REQUIRED_SLOTS = [
    "work_address", "transport_mode", "rent_type",
    "deposit_manwon", "allowed_minutes",
    "house_type", "weight_preference",
]

SLOT_QUESTIONS = {
    "work_address":      "직장 도로명 주소를 알려주세요.\n(예: 강남구 테헤란로 521)\n역명·건물명은 주소로 인식되지 않아요.",
    "transport_mode":    "출퇴근 수단은 자가용인가요, 대중교통인가요?",
    "rent_type":         "전세로 보실 건가요, 월세로 보실 건가요?",
    "deposit_manwon":    "보증금(전세금)은 얼마 정도 생각하세요? (예: 1억5천만원)",
    "monthly_manwon":    "월세는 얼마까지 괜찮으세요? (예: 50만원)",
    "allowed_minutes":   "최대 통근 시간은 몇 분이에요? (예: 40분)",
    "house_type":        "주택 유형 선호가 있으신가요?\n① 오피스텔  ② 연립·다세대  ③ 상관없음",
    "weight_preference": "추천 우선순위를 선택해 주세요.\n① 통근 우선  ② 주거비 우선  ③ 균형  ④ 직접 설정",
}

SLOT_DISPLAY = {
    "work_address":      "직장 주소",
    "transport_mode":    "이동수단",
    "rent_type":         "임대 유형",
    "deposit_manwon":    "보증금",
    "monthly_manwon":    "월세",
    "allowed_minutes":   "최대 통근",
    "house_type":        "주택유형",
    "weight_preference": "우선순위",
    "vibe":              "동네 분위기",
    "use_youth_policy":  "청년정책 반영",
    "region_filter":     "선호 지역",
    # 청년정책 세부 슬롯
    "policy_employment": "취업상태",
    "policy_income":     "월 소득",
    "policy_marriage":   "혼인상태",
    "policy_education":  "학력",
    "policy_no_house":   "무주택여부",
}

# 청년정책 세부 질문 (use_youth_policy=True 후 순서대로 수집)
POLICY_SLOTS = [
    "policy_employment",
    "policy_income",
    "policy_marriage",
    "policy_education",
    "policy_no_house",
]

POLICY_QUESTIONS = {
    "policy_employment": (
        "취업 상태를 선택해 주세요.\n"
        "① 취업자 (회사 근무, 프리랜서 등)\n"
        "② 미취업자 (구직 중, 일 경험 없음 등)\n"
        "③ 자영업자 (사업자 등록자)"
    ),
    "policy_income": (
        "월 소득이 얼마인지 알려주세요.\n"
        "(예: 200만원 / 250 / 소득 없음)\n"
        "청년정책 자격 확인에만 사용됩니다."
    ),
    "policy_marriage": "혼인 상태를 선택해 주세요.\n① 미혼  ② 기혼",
    "policy_education": (
        "최종 학력을 선택해 주세요.\n"
        "① 고졸이하  ② 대학재학  ③ 대졸  ④ 석박사"
    ),
    "policy_no_house": (
        "현재 주택을 소유하고 있나요?\n"
        "① 무주택 (소유 없음)  ② 주택 소유"
    ),
}

# ──────────────────────────────────────────────────────────
# ChatBot 클래스
# ──────────────────────────────────────────────────────────

class ChatBot:
    """
    슬롯 수집 상태 머신.
    process(user_text) → (bot_reply: str, is_done: bool, v5_params: dict|None)
    """

    MAX_TURNS = 25

    def __init__(self):
        self.slots: Dict[str, Any] = {}
        self.turn = 0
        self.vibe_unrecognized: Optional[str] = None
        self._asked_vibe    = False
        self._asked_policy  = False
        self._done          = False
        self._last_asked_slot: Optional[str] = None  # 직전에 물어본 슬롯
        self.user_meta: Dict[str, str] = {}  # 로그인 유저 정보 (birth_date, gender, age, nickname)
        # ── 청년정책 카드 플로우 상태 ──
        self._selection_error: Optional[str] = None   # 카드 선택 충돌 오류
        self.policy_cards: Optional[List[Dict]] = None # /api/chat 응답용 카드 데이터
        self.has_more_policy_cards: bool = False       # "더보기" 가능 여부

    # ── 필수 슬롯 확인 ──────────────────────────────────────

    def _missing_required(self) -> List[str]:
        order = ["work_address", "transport_mode", "rent_type", "deposit_manwon"]
        if self.slots.get("rent_type") == "월세":
            order.append("monthly_manwon")
        order += ["allowed_minutes", "house_type", "weight_preference"]
        return [s for s in order if self.slots.get(s) is None]

    def _is_slots_complete(self) -> bool:
        return len(self._missing_required()) == 0

    # ── 슬롯 머지 (None이 아닌 새 값만 채움) ────────────────

    def _merge_slots(self, new_slots: Dict):
        for k, v in new_slots.items():
            if v is not None and self.slots.get(k) is None:
                self.slots[k] = v
        if "vibe_unrecognized" in new_slots and new_slots["vibe_unrecognized"]:
            self.vibe_unrecognized = new_slots["vibe_unrecognized"]

    # ── 다음 질문 결정 ──────────────────────────────────────

    def _next_question(self) -> Optional[str]:
        missing = self._missing_required()
        if missing:
            self._last_asked_slot = missing[0]
            return SLOT_QUESTIONS[missing[0]]

        # 직접설정 선택 후 비율 입력
        if self.slots.get("weight_preference") == "직접설정" and self.slots.get("weight_custom") is None:
            self._last_asked_slot = "weight_custom"
            return "통근과 주거비 비율을 직접 입력해 주세요.\n(예: 통근 70 주거비 30, 또는 7:3)"

        # vibe 확인
        if not self._asked_vibe:
            self._asked_vibe = True
            if self.slots.get("vibe") is not None:
                return None  # 이미 추출됨
            if self.vibe_unrecognized:
                return (
                    f"'{self.vibe_unrecognized}'은 통근시간으로 반영하실 수 있어요.\n"
                    "동네 분위기 선호가 있으신가요?\n"
                    "① 조용함 ② 번화함 ③ 청년활기 ④ 가족친화 ⑤ 자연친화 "
                    "⑥ 편의 우선 ⑦ 운동·건강 ⑧ 카페·문화 ⑨ 상관없음"
                )
            return (
                "동네 분위기 선호가 있으신가요?\n"
                "① 조용함 ② 번화함 ③ 청년활기 ④ 가족친화 ⑤ 자연친화 "
                "⑥ 편의 우선 ⑦ 운동·건강 ⑧ 카페·문화 ⑨ 상관없음"
            )

        # 청년정책 확인 (예/아니요)
        if not self._asked_policy:
            self._asked_policy = True
            if self.slots.get("use_youth_policy") is None:
                return "현재 조건에 맞는 청년정책도 같이 확인하시겠어요? (예 / 아니요)"

        # 청년정책 카드 플로우 (use_youth_policy=True 후)
        if self.slots.get("use_youth_policy"):
            # ── Step 1: employment/education 확보 ──────────────
            # user_meta 우선, 없으면 슬롯에서, 그래도 없으면 챗봇이 묻기
            emp = (self.user_meta.get("employment", "") or "").strip() \
                  or self.slots.get("policy_employment", "")
            edu = (self.user_meta.get("education",  "") or "").strip() \
                  or self.slots.get("policy_education", "")

            # user_meta 값 자동으로 슬롯에 채우기 (1회성)
            if emp and not self.slots.get("policy_employment"):
                self.slots["policy_employment"] = emp
            if edu and not self.slots.get("policy_education"):
                self.slots["policy_education"] = edu

            if not emp:
                self._last_asked_slot = "policy_employment"
                return POLICY_QUESTIONS["policy_employment"]
            if not edu:
                self._last_asked_slot = "policy_education"
                return POLICY_QUESTIONS["policy_education"]

            # ── Step 2: 1차 필터링 ─────────────────────────────
            if self.slots.get("candidate_policies") is None:
                gu = self._extract_work_gu()
                try:
                    from youth_policy_module import fetch_candidates_basic
                    candidates = fetch_candidates_basic(
                        {"age": self.user_meta.get("age", ""),
                         "employment": emp, "education": edu},
                        gu,
                    )
                except Exception as e:
                    print(f"[정책 필터링 오류] {e}")
                    candidates = []
                self.slots["candidate_policies"] = candidates
                self.slots["show_more_offset"] = 0

            # ── Step 3: 카드 표시 + 선택 대기 ─────────────────
            if self.slots.get("selected_policies") is None:
                self._last_asked_slot = "policy_card_selection"
                return "__show_cards__"

            # ── Step 4: 추가 조건 묻기 ─────────────────────────
            for cond in (self.slots.get("required_conditions") or []):
                slot_key = f"policy_{cond}"
                if self.slots.get(slot_key) is None:
                    self._last_asked_slot = slot_key
                    return POLICY_QUESTIONS.get(slot_key, "")

        return None  # 모든 슬롯 완료

    # ── vibe 번호 선택 파싱 ─────────────────────────────────

    _VIBE_MAP = {
        "1": "조용함", "①": "조용함",
        "2": "번화함", "②": "번화함",
        "3": "청년활기", "③": "청년활기",
        "4": "가족친화", "④": "가족친화",
        "5": "자연친화", "⑤": "자연친화",
        "6": "편의 우선", "⑥": "편의 우선",
        "7": "운동·건강", "⑦": "운동·건강",
        "8": "카페·문화", "⑧": "카페·문화",
        "9": "상관없음", "⑨": "상관없음",
    }

    _HOUSE_MAP = {
        "1": "오피스텔", "①": "오피스텔",
        "2": "연립다세대", "②": "연립다세대",
        "3": None, "③": None,
    }

    _WEIGHT_MAP = {
        "1": "통근우선", "①": "통근우선",
        "2": "주거비우선", "②": "주거비우선",
        "3": "균형", "③": "균형",
        "4": "직접설정", "④": "직접설정",
    }

    @classmethod
    def _parse_vibe_choice(cls, text: str) -> Optional[List[str]]:
        chosen = []
        for k, v in cls._VIBE_MAP.items():
            if k in text:
                chosen.append(v)
        if not chosen:
            for n in re.findall(r"\b([1-9])\b", text):
                if n in cls._VIBE_MAP:
                    chosen.append(cls._VIBE_MAP[n])
        # 텍스트로 분위기 이름을 직접 입력한 경우
        if not chosen:
            for v in dict.fromkeys(cls._VIBE_MAP.values()):
                if v in text:
                    chosen.append(v)
        return list(dict.fromkeys(chosen)) or None

    @classmethod
    def _parse_house_choice(cls, text: str) -> Optional[str]:
        for k, v in cls._HOUSE_MAP.items():
            if k in text:
                return v
        return None

    @classmethod
    def _parse_weight_choice(cls, text: str) -> Optional[str]:
        for k, v in cls._WEIGHT_MAP.items():
            if k in text:
                return v
        if re.search(r"통근|출퇴근", text):
            return "통근우선"
        if re.search(r"주거비|비용|저렴", text):
            return "주거비우선"
        if re.search(r"균형|반반", text):
            return "균형"
        if re.search(r"직접\s*설정", text):
            return "직접설정"
        if re.search(r"알아서|위임|맡겨", text):
            return "위임"
        return None

    @staticmethod
    def _validate_work_address(text: str):
        """(valid: bool, error_msg: str). 역명·건물명 입력 거부."""
        stripped = text.strip()
        if re.search(r"[가-힣]+역$", stripped) or re.search(r"[가-힣]+역\s", stripped):
            return False, (
                f"'{stripped}'은 역 이름이에요. 근처 도로명 주소를 입력해 주세요.\n"
                "(예: 강남구 테헤란로 521, 서초구 강남대로 373)"
            )
        if re.search(r"(코엑스|타워|몰|센터|빌딩|광장|마트|쇼핑|터미널)$", stripped.replace(" ", "")):
            return False, (
                f"'{stripped}'은 건물·시설 이름이에요. 실제 도로명 주소를 입력해 주세요.\n"
                "(예: 강남구 영동대로 513)"
            )
        return True, ""

    @staticmethod
    def _parse_weight_custom(text: str) -> Optional[List[int]]:
        """'통근 70 주거비 30' 또는 '7:3' 형식 → [commute, housing]"""
        nums = re.findall(r"\d+", text)
        if len(nums) >= 2:
            a, b = int(nums[0]), int(nums[1])
            if a + b > 0:
                return [a, b]
        return None

    @staticmethod
    def _parse_policy_choice(text: str) -> Optional[bool]:
        if re.search(r"^(예|네|응|ㅇ|y|yes|반영|확인|좋아|알려줘|할게|해줘)", text.strip().lower()):
            return True
        if re.search(r"^(아니|no|n|됐|필요없|괜찮|넘어|skip|별로)", text.strip().lower()):
            return False
        return None

    # ── 청년정책 세부 슬롯 파서 ────────────────────────────

    _EMPLOYMENT_MAP = {
        "1": "재직자",   "①": "재직자",
        "2": "자영업자", "②": "자영업자",
        "3": "미취업자", "③": "미취업자",
        "4": "프리랜서", "④": "프리랜서",
        "5": "일경험없음", "⑤": "일경험없음",
    }

    _MARRIAGE_MAP = {
        "1": "미혼", "①": "미혼",
        "2": "기혼", "②": "기혼",
    }

    _EDUCATION_MAP = {
        "1": "고졸이하", "①": "고졸이하",
        "2": "대학재학", "②": "대학재학",
        "3": "대졸",     "③": "대졸",
        "4": "석박사",   "④": "석박사",
    }

    @classmethod
    def _parse_employment_choice(cls, text: str) -> Optional[str]:
        """취업상태 파싱 → 3분류 정규화 (취업자/미취업자/자영업자)."""
        # 1. 3분류 직접 입력
        if re.search(r"자영업자|자영업|개인사업|사업자|창업", text):
            return "자영업자"
        if re.search(r"미취업자|미취업|구직|취업준비|취준|백수|일경험없|경험없", text):
            return "미취업자"
        if re.search(r"취업자|재직자|근로자|직장인|재직|근무|회사|프리랜서|프리", text):
            return "취업자"
        # 2. 번호 선택 (구 5분류 → 3분류 정규화)
        _old_to_new = {
            "재직자": "취업자", "프리랜서": "취업자", "일경험없음": "미취업자",
            "미취업자": "미취업자", "자영업자": "자영업자",
        }
        for k, v in cls._EMPLOYMENT_MAP.items():
            if k in text:
                return _old_to_new.get(v, v)
        return None

    @classmethod
    def _parse_marriage_choice(cls, text: str) -> Optional[str]:
        for k, v in cls._MARRIAGE_MAP.items():
            if k in text:
                return v
        if re.search(r"미혼|싱글|혼자|비혼|결혼안|결혼 안", text):
            return "미혼"
        if re.search(r"기혼|결혼|배우자|유부", text):
            return "기혼"
        return None

    @classmethod
    def _parse_education_choice(cls, text: str) -> Optional[str]:
        for k, v in cls._EDUCATION_MAP.items():
            if k in text:
                return v
        if re.search(r"석사|박사", text):
            return "석박사"
        if re.search(r"대졸|대학교\s*졸|4년제\s*졸", text):
            return "대졸"
        if re.search(r"재학|대학교\s*재|다니|학생", text):
            return "대학재학"
        if re.search(r"고졸|고등학교|고등\s*졸", text):
            return "고졸이하"
        return None

    @staticmethod
    def _parse_no_house_choice(text: str) -> Optional[str]:
        # ① / 1 / "무주택" → "y"   ② / 2 / "소유" → "n"
        if re.search(r"[①1]|무주택|없어|소유\s*안|안\s*소유", text):
            return "y"
        if re.search(r"[②2]|소유|있어|주택\s*있|집\s*있", text):
            return "n"
        return None

    # ── 잡담/인사 감지 ─────────────────────────────────────

    # 인사말 패턴
    _GREET_RE = re.compile(
        r"^(안녕|하이|hello|hi|헬로|ㅎㅇ|ㅎㅎ|방가|반가|반갑|반겨|좋은\s*(아침|오전|오후|저녁|밤|하루)|잘\s*부탁|처음\s*뵙)",
        re.I,
    )
    # 감사 패턴
    _THANKS_RE = re.compile(r"^(감사|고마워|고맙|수고|ㄳ|땡큐|thanks|thank)", re.I)
    # 도움 요청/모르겠다 패턴
    _HELP_RE = re.compile(
        r"^(뭘|뭐|어떻게|어떡|모르|모르겠|어디서|어떤\s*정보|도움|도와|설명|알려줘|알려주세요|어디\s*적)",
        re.I,
    )
    # 처음부터 / 다시 패턴
    _RESTART_RE = re.compile(r"^(처음|다시|새로\s*시작|리셋|초기화)", re.I)
    # 잘 지내요/요즘 어때 등 안부 패턴
    _CHITCHAT_RE = re.compile(
        r"^(잘\s*지내|잘\s*있|날씨|심심|배고|피곤|힘들|바빠|뭐\s*해|뭐해|어때|요즘)",
        re.I,
    )
    # 집/이사 관련 의지 표현 (슬롯 질문으로 자연 연결)
    _HOUSING_INTENT_RE = re.compile(
        r"(집\s*(구하|찾|보)|이사|방\s*(구하|찾|보)|주거|살\s*곳|거주|전세|월세)",
        re.I,
    )

    def _detect_small_talk(self, text: str) -> Optional[str]:
        """
        인사/잡담 감지 → 자연스러운 응답 문자열 반환.
        잡담이 아니면 None.
        슬롯이 절반 이상 채워진 상태라면 잡담 감지 비활성화 (흐름 방해 방지).
        """
        t = text.strip()
        # 슬롯이 3개 이상 채워진 중간 대화라면 잡담 처리 건너뜀
        filled_count = sum(1 for v in self.slots.values() if v is not None)
        if filled_count >= 3:
            return None
        # 집 찾기 의도가 있으면 잡담 아님
        if self._HOUSING_INTENT_RE.search(t) and len(t) > 3:
            return None

        if self._GREET_RE.search(t):
            greets = [
                "안녕하세요! 😊 반갑습니다.",
                "안녕하세요! 🏠 잘 오셨어요.",
                "반갑습니다! 😊 집 찾는 걸 도와드릴게요.",
            ]
            import random
            return random.choice(greets)

        if self._THANKS_RE.search(t):
            return "천만에요 😊 계속 진행해 볼까요?"

        if self._RESTART_RE.search(t):
            return "처음부터 다시 시작하려면 페이지를 새로고침(F5)해 주세요! 🔄"

        if self._HELP_RE.search(t):
            return (
                "몇 가지 질문에 답해주시면 서울 내 최적 주거지를 추천해드려요 🏠\n"
                "직장 주소, 예산, 통근 시간 등을 순서대로 여쭤볼게요!"
            )

        if self._CHITCHAT_RE.search(t):
            return "저는 항상 열심히 집을 찾고 있어요 🏠😄 주거지 추천을 도와드릴게요!"

        return None

    # ── 청년정책 카드 플로우 헬퍼 ─────────────────────────

    def _extract_work_gu(self) -> str:
        """work_address에서 구 이름 추출."""
        addr = self.slots.get("work_address", "")
        m = re.search(r"([가-힣]+구)", addr)
        return m.group(1) if m else ""

    def _compute_required_conditions(self, policies: list) -> list:
        """선택 정책들이 요구하는 추가 조건 목록 산출 (income/marriage/no_house 순)."""
        from youth_policy_module import _extract_policy_text
        needs = {"income": False, "marriage": False, "no_house": False}
        for p in policies:
            earn_cd  = str(p.get("earnCndSeCd", "")).strip()
            earn_max = str(p.get("earnMaxAmt",  "0")).strip()
            mrg_cd   = str(p.get("mrgSttsCd",   "")).strip()
            text     = _extract_policy_text(p)
            if (earn_cd and earn_cd != "0043001") or (earn_max not in ("0", "", "None")):
                needs["income"]   = True
            if mrg_cd and mrg_cd not in ("", "0055003"):
                needs["marriage"] = True
            if "무주택" in text:
                needs["no_house"] = True
        return [k for k in ["income", "marriage", "no_house"] if needs[k]]

    def _build_card_message(self) -> str:
        """카드 표시 메시지 생성 + self.policy_cards / has_more_policy_cards 세팅."""
        candidates = self.slots.get("candidate_policies", [])
        offset     = self.slots.get("show_more_offset", 0)
        page_size  = 5
        start = offset * page_size
        end   = start + page_size
        page  = candidates[start:end]

        # API 응답용 카드 데이터 세팅
        self.has_more_policy_cards = len(candidates) > end
        if page:
            self.policy_cards = []
            for i, p in enumerate(page, start + 1):
                cl = p.get("_conflict_label", {})
                self.policy_cards.append({
                    "index":            i,
                    "name":             p.get("plcyNm", ""),
                    "description":      p.get("_benefit_desc", ""),
                    "monthly_saving":   p.get("_monthly_saving", 0),
                    "benefit_type":     p.get("_benefit_type", ""),
                    "url":              p.get("refUrlAddr1", "") or p.get("aplyUrlAddr", ""),
                    "auto_match_label": p.get("_auto_match", ""),
                    "conflict_warning": cl.get("warning_text", ""),
                    "conflict_level":   cl.get("level", "none"),
                })
        else:
            self.policy_cards = []

        if not page:
            return (
                "아쉽게도 현재 조건에 맞는 청년정책을 찾지 못했어요. "
                "청년정책 없이 추천을 진행할게요."
            )

        lines = ["📋 내 조건에 맞는 청년정책이에요!\n"]
        for i, p in enumerate(page, start + 1):
            name    = p.get("plcyNm", "")
            desc    = p.get("_benefit_desc", "")
            saving  = p.get("_monthly_saving", 0)
            cl      = p.get("_conflict_label", {})
            warning = cl.get("warning_text", "")
            url     = p.get("refUrlAddr1", "") or p.get("aplyUrlAddr", "")
            auto_m  = p.get("_auto_match", "")
            lines.append(f"[{i}] {name}")
            if auto_m:
                lines.append(f"  {auto_m}")  # auto_m 자체에 이미 ✅ 포함
            lines.append(f"  혜택: {desc}")
            lines.append(f"  💰 월 약 {saving:.0f}만원 절감 추정")
            if warning:
                lines.append(f"  ⚠️ {warning}")
            if url:
                lines.append(f"  🔗 {url}")
            lines.append("")

        if self.has_more_policy_cards:
            lines.append(f"(외 {len(candidates) - end}건 더 있어요. '더보기' 입력 시 추가 표시)")
        lines.append("원하시는 정책 번호를 선택해 주세요. (예: 1 또는 1,3)")
        lines.append("정책이 없으면 '없음'을 입력해 주세요.")
        return "\n".join(lines)

    # ── 메인 process() ─────────────────────────────────────

    def process(self, user_text: str):
        if self._done:
            return "이미 추천이 완료되었습니다. 새로 시작하려면 페이지를 새로고침해 주세요.", True, None

        self.turn += 1
        if self.turn > self.MAX_TURNS:
            return "대화 한도를 초과했습니다. 새로 시작해 주세요.", False, None

        # ── 잡담/인사 감지 ─────────────────────────────────
        small_talk = self._detect_small_talk(user_text)
        if small_talk:
            # 다음에 물어볼 슬롯 질문과 자연스럽게 연결
            missing = self._missing_required()
            if missing:
                next_q = SLOT_QUESTIONS[missing[0]]
                self._last_asked_slot = missing[0]
                return f"{small_talk}\n\n{next_q}", False, None
            return small_talk, False, None

        # LLM 슬롯 추출
        new_slots = extract_slots_from_text(user_text, self.slots)

        # ── 컨텍스트 인식 폴백 ──────────────────────────────
        # 봇이 직전에 특정 슬롯을 물어봤는데 LLM이 그 슬롯을 못 잡은 경우,
        # 사용자 발화를 해당 슬롯 값으로 직접 사용
        _addr_err = None
        if self._last_asked_slot and new_slots.get(self._last_asked_slot) is None:
            asked = self._last_asked_slot
            txt   = user_text.strip()
            if asked == "work_address" and txt:
                valid, err = self._validate_work_address(txt)
                if valid:
                    new_slots["work_address"] = txt
                else:
                    _addr_err = err
            elif asked == "weight_custom":
                parsed = self._parse_weight_custom(txt)
                if parsed:
                    new_slots["weight_custom"] = parsed
            elif asked == "allowed_minutes":
                parsed = _parse_commute_minutes(txt)
                if parsed is not None:
                    new_slots["allowed_minutes"] = parsed
            elif asked == "deposit_manwon":
                new_slots["deposit_manwon"] = _parse_manwon(txt)
            elif asked == "monthly_manwon":
                m = re.search(r"(\d+)", txt)
                if m:
                    new_slots["monthly_manwon"] = int(m.group(1))
            # ── 청년정책 세부 슬롯 ──
            elif asked == "policy_employment":
                parsed = self._parse_employment_choice(txt)
                if parsed:
                    new_slots["policy_employment"] = parsed
            elif asked == "policy_income":
                # "소득 없음" / "없어" → 0
                if re.search(r"없|0|없음", txt):
                    new_slots["policy_income"] = "0"
                else:
                    parsed = _parse_manwon(txt)
                    if parsed is not None:
                        new_slots["policy_income"] = str(parsed)
            elif asked == "policy_marriage":
                parsed = self._parse_marriage_choice(txt)
                if parsed:
                    new_slots["policy_marriage"] = parsed
            elif asked == "policy_education":
                parsed = self._parse_education_choice(txt)
                if parsed:
                    new_slots["policy_education"] = parsed
            elif asked == "policy_no_house":
                parsed = self._parse_no_house_choice(txt)
                if parsed is not None:
                    new_slots["policy_no_house"] = parsed

            elif asked == "policy_card_selection":
                # "더보기" 처리
                if re.search(r"더\s*(보기|봐|줘|봐요)|다음|next", txt.lower()):
                    candidates = self.slots.get("candidate_policies", [])
                    curr_off   = self.slots.get("show_more_offset", 0)
                    next_start = (curr_off + 1) * 5
                    if next_start < len(candidates):
                        self.slots["show_more_offset"] = curr_off + 1
                # "없음" 처리 (정책 없이 진행)
                elif re.search(r"^(없음|없어|없|패스|skip|건너|아니)$", txt.strip().lower()):
                    self.slots["selected_policies"]  = []
                    self.slots["required_conditions"] = []
                    self._selection_error = None
                else:
                    # 번호 파싱 → 선택 검증
                    nums = [int(n) for n in re.findall(r"\d+", txt)]
                    candidates = self.slots.get("candidate_policies", [])
                    selected = []
                    for n in nums:
                        idx = n - 1  # 1-based → 0-based
                        if 0 <= idx < len(candidates):
                            selected.append(candidates[idx])
                    if selected:
                        from youth_policy_module import validate_policy_selection
                        result = validate_policy_selection(selected)
                        if not result["valid"]:
                            self._selection_error = result["error"]
                        else:
                            self.slots["selected_policies"]  = selected
                            self.slots["required_conditions"] = self._compute_required_conditions(selected)
                            self._selection_error = None

        # LLM이 추출한 work_address도 검증 (역명·건물명 거부)
        if new_slots.get("work_address") and self.slots.get("work_address") is None:
            valid, err = self._validate_work_address(new_slots["work_address"])
            if not valid:
                new_slots.pop("work_address")
                if not _addr_err:
                    _addr_err = err
                    self._last_asked_slot = "work_address"

        # 번호 선택 폴백 (LLM이 못 잡은 경우)
        missing = self._missing_required()

        if "house_type" in missing and new_slots.get("house_type") is None:
            parsed = self._parse_house_choice(user_text)
            if parsed is not None:
                new_slots["house_type"] = parsed if parsed else "__none__"

        if "weight_preference" in missing and new_slots.get("weight_preference") is None:
            parsed = self._parse_weight_choice(user_text)
            if parsed:
                new_slots["weight_preference"] = parsed

        # 주소 검증 실패 시 즉시 반환 (슬롯 미병합)
        if _addr_err:
            return _addr_err, False, None

        if self._asked_vibe and self.slots.get("vibe") is None and new_slots.get("vibe") is None:
            parsed = self._parse_vibe_choice(user_text)
            if parsed:
                if "상관없음" in parsed:
                    new_slots["vibe"] = []
                else:
                    new_slots["vibe"] = [v for v in parsed if v != "상관없음"]
            else:
                vibe_result = extract_vibe_from_text(user_text)
                if vibe_result["matched"]:
                    new_slots["vibe"] = vibe_result["matched"]

        if self._asked_policy and self.slots.get("use_youth_policy") is None and new_slots.get("use_youth_policy") is None:
            pol = self._parse_policy_choice(user_text)
            if pol is not None:
                new_slots["use_youth_policy"] = pol

        # house_type="__none__" → None 처리 (둘 다 상관없음)
        if new_slots.get("house_type") == "__none__":
            new_slots["house_type"] = "__skip__"

        self._merge_slots(new_slots)

        # house_type 스킵 처리 — 필수에서 제외
        if self.slots.get("house_type") == "__skip__":
            self.slots["house_type"] = None  # 실제 v5에는 None 전달

        # 다음 질문
        next_q = self._next_question()

        # 카드 표시 처리
        if next_q == "__show_cards__":
            self.policy_cards = None  # 리셋 후 _build_card_message에서 세팅
            card_msg = self._build_card_message()
            candidates = self.slots.get("candidate_policies", [])
            # 후보가 없으면 즉시 selected_policies=[] 로 셋 후 진행
            if not candidates:
                self.slots["selected_policies"]  = []
                self.slots["required_conditions"] = []
                self.policy_cards = []
                # 다음 질문 재결정 (조건 묻기 or 완료)
                next_q2 = self._next_question()
                if next_q2 is None:
                    if not self._is_slots_complete():
                        miss = self._missing_required()
                        return card_msg + "\n\n" + SLOT_QUESTIONS[miss[0]], False, None
                    self._done = True
                    return card_msg + "\n\n" + self._build_summary(), True, self.get_v5_params()
                return card_msg + "\n\n" + next_q2, False, None
            # 선택 오류가 있으면 메시지 앞에 붙이기
            if self._selection_error:
                err = self._selection_error
                self._selection_error = None
                return f"⚠️ {err}\n\n{card_msg}", False, None
            return card_msg, False, None

        if next_q is not None:
            return next_q, False, None

        if not self._is_slots_complete():
            miss = self._missing_required()
            return SLOT_QUESTIONS[miss[0]], False, None

        self._done = True
        params = self.get_v5_params()
        return self._build_summary(), True, params

    # ── 요약 메시지 ─────────────────────────────────────────

    def _build_summary(self) -> str:
        s = self.slots
        rt  = s.get("rent_type", "전세")
        dep = s.get("deposit_manwon", 0)
        lines = ["조건이 모두 입력됐어요. 지금 바로 추천을 시작할게요!\n", "**입력 조건 요약**"]
        lines.append(f"- 직장: {s.get('work_address','')}")
        lines.append(f"- 이동수단: {'자가용' if s.get('transport_mode')=='car' else '대중교통'}")
        if rt == "월세":
            mon = s.get("monthly_manwon", 0)
            lines.append(f"- 예산: 월세 보증금 {dep:,}만원 / 월 {mon}만원")
        else:
            lines.append(f"- 예산: 전세 {dep:,}만원")
        lines.append(f"- 최대 통근: {s.get('allowed_minutes', 60)}분")
        ht = s.get("house_type")
        lines.append(f"- 주택유형: {ht if ht else '상관없음'}")
        wp = s.get("weight_preference", "균형")
        if wp == "직접설정":
            wc = s.get("weight_custom") or [1, 1]
            lines.append(f"- 우선순위: 직접설정 (통근 {wc[0]} : 주거비 {wc[1]})")
        else:
            lines.append(f"- 우선순위: {wp}")
        vibe = s.get("vibe")
        if vibe:
            lines.append(f"- 동네 분위기: {', '.join(vibe)}")
        if s.get("use_youth_policy"):
            emp  = s.get("policy_employment", "")
            inc  = s.get("policy_income", "")
            mrg  = s.get("policy_marriage", "")
            edu  = s.get("policy_education", "")
            nh   = "무주택" if s.get("policy_no_house") == "y" else "주택소유" if s.get("policy_no_house") == "n" else ""
            age  = self.user_meta.get("age", "")
            detail = "  |  ".join(filter(None, [
                f"나이 {age}세" if age else "",
                emp, f"소득 {inc}만원" if inc else "",
                mrg, edu, nh,
            ]))
            lines.append(f"- 청년정책: 반영  ({detail})" if detail else "- 청년정책: 반영")
        return "\n".join(lines)

    # ── v5 파라미터 변환 ────────────────────────────────────

    def get_v5_params(self) -> Dict:
        s = self.slots
        rt  = s.get("rent_type", "전세")
        dep = s.get("deposit_manwon", 0)
        mon = s.get("monthly_manwon", 0)

        budget_manwon      = dep if rt == "전세" else dep + mon * 200
        monthly_rent_manwon = 0.0 if rt == "전세" else float(mon)

        vibe       = [v for v in (s.get("vibe") or []) if v]
        use_policy = bool(s.get("use_youth_policy"))

        weight_infra  = 0.2 if vibe else 0.0
        weight_policy = 0.2 if use_policy else 0.0
        remaining     = 1.0 - weight_infra - weight_policy

        wp_pref = s.get("weight_preference", "균형")
        if wp_pref == "통근우선":
            weight_commute = round(remaining * 0.7, 4)
            weight_housing = round(remaining * 0.3, 4)
        elif wp_pref == "주거비우선":
            weight_commute = round(remaining * 0.3, 4)
            weight_housing = round(remaining * 0.7, 4)
        elif wp_pref == "직접설정":
            wc = s.get("weight_custom") or [1, 1]
            total = wc[0] + wc[1]
            weight_commute = round(remaining * wc[0] / total, 4)
            weight_housing = round(remaining * wc[1] / total, 4)
        else:
            weight_commute = round(remaining / 2, 4)
            weight_housing = round(remaining - weight_commute, 4)

        required_infra = None
        if vibe:
            weights = get_vibe_weights(vibe)
            required_infra = [k for k in INFRA_KEYS if weights.get(k, 1.0) >= 1.3] or None

        ht = s.get("house_type")
        housing_filter = [ht] if ht else None

        user_info = None
        if use_policy:
            # user_meta(회원가입 정보) 우선, 없으면 챗봇 수집 슬롯 사용
            age_val = self.user_meta.get("age", "") or ""
            user_info = {
                "age":           str(age_val),
                "employment":    (self.user_meta.get("employment", "") or "").strip()
                                 or s.get("policy_employment", ""),
                "education":     (self.user_meta.get("education", "") or "").strip()
                                 or s.get("policy_education", ""),
                "income_manwon": s.get("policy_income", ""),
                "marriage":      s.get("policy_marriage", ""),
                "no_house":      s.get("policy_no_house", "y"),
            }

        return dict(
            work_address        = s.get("work_address", ""),
            transport_mode      = s.get("transport_mode", "transit"),
            budget_manwon       = budget_manwon,
            allowed_commute_min = s.get("allowed_minutes", 60),
            final_recommend_count = 5,
            depart_hour=8, depart_min=30,
            arrive_hour=9, arrive_min=0,
            region_filter       = s.get("region_filter"),
            housing_filter      = housing_filter,
            weight_commute      = weight_commute,
            weight_housing      = weight_housing,
            required_infra      = required_infra,
            weight_infra        = weight_infra,
            user_info           = user_info,
            weight_policy       = weight_policy,
            max_policy_display  = 3,
            monthly_rent_manwon = monthly_rent_manwon,
            chatbot_mode        = True,
            vibe_list           = vibe or None,
            selected_policies   = s.get("selected_policies") or None,
        )

    # ── 슬롯 상태 (우측 패널용) ─────────────────────────────

    def slot_status(self) -> List[Dict]:
        rows = []
        keys = list(REQUIRED_SLOTS) + ["monthly_manwon", "vibe", "use_youth_policy"]
        for k in keys:
            if k == "monthly_manwon" and self.slots.get("rent_type") != "월세":
                continue
            v = self.slots.get(k)
            display_val = v
            if isinstance(v, list):
                display_val = ", ".join(v) if v else "상관없음"
            elif isinstance(v, bool):
                display_val = "예" if v else "아니요"
            rows.append({
                "key":    k,
                "label":  SLOT_DISPLAY.get(k, k),
                "value":  display_val,
                "filled": v is not None,
            })

        # 청년정책 세부 슬롯 (반영 선택 시에만 표시)
        if self.slots.get("use_youth_policy"):
            for k in POLICY_SLOTS:
                v = self.slots.get(k)
                display_val = v
                if k == "policy_no_house":
                    display_val = "무주택" if v == "y" else "주택소유" if v == "n" else None
                rows.append({
                    "key":    k,
                    "label":  SLOT_DISPLAY.get(k, k),
                    "value":  display_val,
                    "filled": v is not None,
                })
        return rows
