# 기억장치 부분
# 사용자가 고른 모든 값 저장 구간 / 단계 이동 시 데이터 유지
# 초기화 / 리셋 처리
# 중요! 변수 이름은 여기서만 정의 (다른 파일은 직접 값 생성 금지)
# 생성할 경우 변수 꼬여서 나중에 디버깅 과정 도중 꼬여버리게 됩니다 ㅠ
# 담당자 1 명만 건드는 것으로 설정

# state.py


PERSONA_PATH = "data/persona.json"  # ← 너희 state.py에서 실제 쓰는 경로로 맞추기

def delete_persona_from_disk():
    if os.path.exists(PERSONA_PATH):
        os.remove(PERSONA_PATH)


import copy
import json
import os
import streamlit as st
from config import PROFILE_PATH, STEP2_PATH, STEP3_PATH, STEP4_PATH, TARGET_CHARS, FINAL_OPTION_DEFAULTS


# 단일 스키마 사용 ! DEFAULT_STATE
DEFAULT_STATE = {
    "step": 1,

    # Step1: 페르소나
    "persona": {
        "role_job": "",
        "tone": {"mode": "preset", "preset": None, "custom_text": ""},
        "mbti": {"type": None, "style_desc": None},
        "avoid_keywords": [],
        "blog": {"use_analysis": False, "url": None, "analyzed_style": None},
    },

    # Step2: 주제/제목/이미지
    "topic_flow": {
        "images": {
            "files": [],       # UploadedFile / bytes / path 등 프로젝트 룰에 맞춰 저장
            "captions": [],
            "intent": {"mode": "none", "preset": None, "custom_text": ""},
        "analysis": {"mood": None, "tags": [], "raw": None, "source": None},
        },

        "category": {
            "selected": None,
            "subtopic_candidates": [],
            "selected_subtopic": None,
            "custom_subtopic": "", #추가 사항 02.02 : 기타 사용자 추가
        },

        "ai_subtopic_recos": {
            "items": [],        # [{"text": "...", "reason": "...", "keywords": [...] }]
            "selected": None,
        },

        "title": {
            "input_keyword": "",
            "candidates": [],   # [{"title":"...", "one_liner":"..."}]
            "selected": None,
            "selected_source": None,  # manual | ai_reco | image_analysis | unknown
        },
    },

    # Step2/3: 옵션(유저가 고르는 값)
    "options": {
        "post_type": "정보 전달형(설명/팁)",
        "headline_style": "호기심 유발형(적당함)",
        "detail": {
            "series": {"use_series": False, "prev_url": None},
            "region_scope": {"text": ""},
            "target_situation": {"text": ""},
            "target_reader": {"text": ""},
            "extra_request": {"text": ""},
        },
    },

    # Step3: 설계안(에이전트 결과 요약)
    "design_brief": {
        "status": "idle",   # idle | generating | ready | error
        "error": None,

        "applied_persona_text": "",

        "keywords": {"main": "", "sub": []},
        "target_context": {"text": ""},

        "tone_manner": {"summary": "", "rules": []},

        "outline": {"summary": "", "sections": []},

        "length": {"target_chars": TARGET_CHARS, "note": ""},

        "strategy": {
            "text": "",
            "seo": {"enabled": False, "notes": ""},
            "hashtags": [],
        },

        "inputs": {
            "mood": {"value": "", "source": None},
            "image_tags": {"values": [], "source": None},
            "title": {"value": "", "source": None},
            "keywords": {"main": "", "main_source": None, "sub": []},
            "options": {
                "post_type": "",
                "headline_style": "",
                "region_scope": "",
                "target_situation": "",
                "target_reader": "",
                "extra_request": "",
            },
            "constraints": {"target_chars": TARGET_CHARS, "seo_opt": False},
        },
        "sources": {"from_step1": {}, "from_step2": {}, "keyword_sources": {}, "agent_raw": None},
        "updated_at": None,
    },

    # Step4: 최종 토글
    "final_options": {
        "base_locked": {
            "anti_ai_basic": True,
            "empathy_structure": True,
        },
        "toggles": {
            "seo_opt": FINAL_OPTION_DEFAULTS["seo_opt"],
            "evidence_label": FINAL_OPTION_DEFAULTS["evidence_label"],
            "publish_package": FINAL_OPTION_DEFAULTS["publish_package"],
            "anti_ai_strong": FINAL_OPTION_DEFAULTS["anti_ai_strong"],
            "image_hashtag_reco": FINAL_OPTION_DEFAULTS["image_hashtag_reco"],
        },
        "params": {
            "seo": {"keyword_density_level": "medium", "use_h2_h3": True, "meta_description": True},
            "anti_ai": {"level": "strong", "remove_repetition": True, "prefer_human_phrasing": True},
        },
    },

    # Step4 결과물(최종 출력)
    "outputs": {
        "status": "idle",   # idle | generating | ready | error
        "error": None,
        "result": None,     # 최종 글/패키지 dict
        "raw": None,        # 디버그 원문
        "updated_at": None,
    },

    # 팀 협업용 메타
    "dirty": {
        "persona_changed": False,
        "topic_changed": False,
        "options_changed": False,
        "design_brief_stale": False,
        "outputs_stale": False,
    },
}

# 초기화 / 리셋

def init_state():
    """DEFAULT_STATE 기반으로 session_state를 안전하게 초기화(deepcopy)."""
    for k, v in DEFAULT_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = copy.deepcopy(v)


def reset_all():
    """전체 초기화(프로필 파일은 유지)."""
    for k in list(DEFAULT_STATE.keys()):
        st.session_state[k] = copy.deepcopy(DEFAULT_STATE[k])


def reset_from_step(from_step: int):
    """
    from_step 이후 단계들만 초기화.
    - 1: persona 이후 전부 초기화
    - 2: topic_flow 이후(옵션/설계/출력) 초기화
    - 3: options 이후(설계/출력) 초기화
    - 4: outputs만 초기화
    """
    if from_step <= 1:
        st.session_state["topic_flow"] = copy.deepcopy(DEFAULT_STATE["topic_flow"])
        st.session_state["options"] = copy.deepcopy(DEFAULT_STATE["options"])
        st.session_state["design_brief"] = copy.deepcopy(DEFAULT_STATE["design_brief"])
        st.session_state["final_options"] = copy.deepcopy(DEFAULT_STATE["final_options"])
        st.session_state["outputs"] = copy.deepcopy(DEFAULT_STATE["outputs"])
    elif from_step == 2:
        st.session_state["options"] = copy.deepcopy(DEFAULT_STATE["options"])
        st.session_state["design_brief"] = copy.deepcopy(DEFAULT_STATE["design_brief"])
        st.session_state["final_options"] = copy.deepcopy(DEFAULT_STATE["final_options"])
        st.session_state["outputs"] = copy.deepcopy(DEFAULT_STATE["outputs"])
    elif from_step == 3:
        st.session_state["design_brief"] = copy.deepcopy(DEFAULT_STATE["design_brief"])
        st.session_state["final_options"] = copy.deepcopy(DEFAULT_STATE["final_options"])
        st.session_state["outputs"] = copy.deepcopy(DEFAULT_STATE["outputs"])
    elif from_step >= 4:
        st.session_state["outputs"] = copy.deepcopy(DEFAULT_STATE["outputs"])

    # dirty 플래그도 함께 정리
    dirty = st.session_state.get("dirty", {})
    dirty["design_brief_stale"] = True
    dirty["outputs_stale"] = True
    st.session_state["dirty"] = dirty


def mark_dirty(name: str):
    """dirty는 무조건 True로 찍는 방식이 안전합니다."""
    dirty = st.session_state.get("dirty")
    if not isinstance(dirty, dict):
        dirty = copy.deepcopy(DEFAULT_STATE["dirty"])
    dirty[name] = True
    st.session_state["dirty"] = dirty


# 페르소나 프로필 저장/로드

def save_persona_to_disk():
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(st.session_state["persona"], f, ensure_ascii=False, indent=2)


def save_step2_to_disk():
    os.makedirs(os.path.dirname(STEP2_PATH), exist_ok=True)
    payload = {
        "topic_flow": st.session_state.get("topic_flow"),
        "options": st.session_state.get("options"),
    }
    with open(STEP2_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_step3_to_disk():
    os.makedirs(os.path.dirname(STEP3_PATH), exist_ok=True)
    payload = {"design_brief": st.session_state.get("design_brief")}
    with open(STEP3_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_step4_to_disk():
    os.makedirs(os.path.dirname(STEP4_PATH), exist_ok=True)
    payload = {"final_options": st.session_state.get("final_options")}
    with open(STEP4_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_persona_from_disk():
    if not os.path.exists(PROFILE_PATH):
        return
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            persona = json.load(f)
        if isinstance(persona, dict):
            # 기본값 위에 덮어쓰기(안전)
            merged = copy.deepcopy(DEFAULT_STATE["persona"])
            merged.update(persona)
            st.session_state["persona"] = merged
            dirty = st.session_state.get("dirty")
            if not isinstance(dirty, dict):
                dirty = copy.deepcopy(DEFAULT_STATE["dirty"])
            dirty["persona_changed"] = False
            st.session_state["dirty"] = dirty
    except Exception:
        # 파일 깨짐/권한 이슈 등은 조용히 무시
        return
