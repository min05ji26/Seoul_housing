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
    else:
        return None

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

        # 청년정책 확인
        if not self._asked_policy:
            self._asked_policy = True
            if self.slots.get("use_youth_policy") is None:
                return "현재 조건에 맞는 청년정책도 같이 확인하시겠어요? (예 / 아니요)"

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

    # ── 메인 process() ─────────────────────────────────────

    def process(self, user_text: str):
        if self._done:
            return "이미 추천이 완료되었습니다. 새로 시작하려면 페이지를 새로고침해 주세요.", True, None

        self.turn += 1
        if self.turn > self.MAX_TURNS:
            return "대화 한도를 초과했습니다. 새로 시작해 주세요.", False, None

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
            lines.append("- 청년정책: 반영")
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
            user_info = {
                "age": "29", "employment": "재직", "income_manwon": "250",
                "marriage": "미혼", "education": "대졸", "no_house": "무주택",
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
        return rows
