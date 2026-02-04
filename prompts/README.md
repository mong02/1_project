# Prompts Guide - 프롬프트 파일 가이드

이 문서는 prompts 폴더 내의 모든 프롬프트 파일과 사용처, 변수를 정리합니다.

---

## 프롬프트 파일 목록

| 파일명 | 용도 | 사용처 |
|--------|------|--------|
| blog_style_analysis.md | 블로그 스타일 분석 | Step1 - 블로그 URL 분석 |
| blog_writing.md | 최종 블로그 글 작성 | Step5 - 글 생성 |
| design_brief.md | 설계안 생성 | Step3 - 설계안 |
| final_options.md | 최종 옵션 설명 | Step4 - 옵션 가이드 |
| final_title.md | 최종 제목 생성 | Step5 - 제목 결정 |
| image_aggregate.md | 이미지 종합 분석 | Step2 - 이미지 분석 |
| image_analysis.md | 개별 이미지 분석 | Step2 - 이미지 분석 |
| image_plan.md | 이미지 배치 계획 | Step5 - 이미지 배치 |
| title_generation.md | 제목 후보 생성 | Step2 - 제목 추천 |
| topic_suggestion.md | 주제 추천 | Step2 - 주제 추천 |

---

## 파일별 상세 정보

### 1. blog_style_analysis.md
**용도**: 사용자의 기존 블로그 스타일을 분석
**사용처**: `agents/topic_agent.py` - `analyze_blog_style()`
**변수**:
- `{content}`: 블로그 HTML 내용 (최대 6000자)

---

### 2. blog_writing.md
**용도**: 최종 블로그 글 작성
**사용처**: `agents/write_agent.py` - `generate_post()`
**변수**:
- `{persona_line}`: 페르소나 설명
- `{avoid}`: 금지 키워드 목록
- `{blog_style}`: 블로그 스타일 분석 결과
- `{tone_example}`: 말투 예시
- `{region}`: 지역 범위
- `{target}`: 타겟 독자
- `{extra}`: 추가 요청사항
- `{title}`: 글 제목
- `{post_type}`: 글 성격
- `{main}`: 메인 키워드
- `{sub_csv}`: 서브 키워드 CSV
- `{target_context}`: 타겟 상황
- `{tone_summary}`: 톤앤매너 요약
- `{outline_summary}`: 글 구성 요약
- `{length_note}`: 글 길이 안내
- `{intro_idx}`: 인트로 이미지 인덱스
- `{body_idxs}`: 본문 이미지 인덱스 목록
- `{excluded_idxs}`: 제외된 이미지 인덱스
- `{image_list}`: 이미지 목록
- `{final_options_block}`: 최종 옵션 블록

---

### 3. design_brief.md
**용도**: 블로그 설계안 생성
**사용처**: `agents/topic_agent.py` - `generate_design_brief()`
**변수**:
- `{topic}`: 주제
- `{category}`: 카테고리
- `{subtopic}`: 세부주제
- `{title}`: 제목
- `{job}`: 역할/직업
- `{mbti}`: MBTI 유형
- `{post_type}`: 글 성격
- `{headline_style}`: 헤드라인 스타일
- `{region_scope}`: 지역 범위
- `{target_reader}`: 타겟 독자
- `{target_situation}`: 타겟 상황
- `{extra_request}`: 추가 요청

---

### 4. final_options.md
**용도**: Step4 최종 옵션 설명
**사용처**: 참조용 가이드
**변수**:
- `{seo_opt}`: SEO 최적화 여부
- `{evidence_label}`: 근거 라벨 여부
- `{publish_package}`: 발행 패키지 여부
- `{anti_ai_strong}`: AI티 제거 여부
- `{image_hashtag_reco}`: 이미지 해시태그 추천 여부

---

### 5. final_title.md
**용도**: 최종 제목 결정
**사용처**: `agents/write_agent.py` - `generate_post()`
**변수**:
- `{title}`: 기본 제목
- `{main}`: 메인 키워드
- `{sub_csv}`: 서브 키워드 CSV
- `{target}`: 타겟 독자
- `{region}`: 지역 범위
- `{post_type}`: 글 성격
- `{headline_style}`: 헤드라인 스타일

---

### 6. image_aggregate.md
**용도**: 여러 이미지 종합 분석
**사용처**: `agents/image_agent.py` - `aggregate_image_analysis()`
**변수**:
- `{results_json}`: 개별 이미지 분석 결과 JSON

---

### 7. image_analysis.md
**용도**: 단일 이미지 분석
**사용처**: `agents/image_agent.py` - `analyze_single_image()`
**변수**: (이미지 바이너리 직접 전달)

---

### 8. image_plan.md
**용도**: 이미지 배치 계획 수립
**사용처**: `agents/write_agent.py` - `generate_post()`
**변수**:
- `{title}`: 글 제목
- `{main}`: 메인 키워드
- `{target_context}`: 타겟 상황
- `{tone_summary}`: 톤앤매너 요약
- `{outline_summary}`: 글 구성 요약
- `{image_list}`: 이미지 목록

---

### 9. title_generation.md
**용도**: 제목 후보 생성
**사용처**: `agents/write_agent.py` - `suggest_titles_agent()`
**변수**:
- `{topic}`: 주제
- `{category}`: 카테고리
- `{subtopic}`: 세부주제
- `{image_mood}`: 이미지 분위기
- `{image_tags}`: 이미지 태그
- `{post_type}`: 글 성격
- `{headline_style}`: 헤드라인 스타일
- `{target_reader}`: 타겟 독자

---

### 10. topic_suggestion.md
**용도**: 주제 추천
**사용처**: `agents/write_agent.py` - `suggest_titles_agent()`
**변수**:
- `{intent}`: 사용자 의도
- `{main_mood}`: 주요 분위기
- `{main_tags}`: 주요 태그
- `{category}`: 카테고리
- `{subtopic}`: 세부주제
- `{image_count}`: 이미지 개수

---

## 데이터 흐름

```
Step1 (페르소나)
└── blog_style_analysis.md → 블로그 스타일 분석

Step2 (주제 선택)
├── image_analysis.md → 개별 이미지 분석
├── image_aggregate.md → 이미지 종합 분석
├── topic_suggestion.md → 주제 추천
└── title_generation.md → 제목 후보 생성

Step3 (설계안)
└── design_brief.md → 설계안 생성

Step4 (최종 옵션)
└── final_options.md → 옵션 가이드

Step5 (글 생성)
├── image_plan.md → 이미지 배치 계획
├── final_title.md → 최종 제목
└── blog_writing.md → 본문 작성
```

---

## 변수 소스 매핑

| 변수 | 소스 |
|------|------|
| persona_line | Step1 - 페르소나 |
| blog_style | Step1 - 블로그 분석 |
| tone_example | Step1 - 말투 설정 |
| category, subtopic | Step2 - 카테고리 선택 |
| target_reader, extra_request | Step2 - 추가설정 |
| post_type, headline_style | Step2 - 글 성격/스타일 |
| target_context, tone_summary | Step3 - 설계안 |
| outline_summary, sub_csv | Step3 - 설계안 |
| final_options_block | Step4 - 최종 옵션 |

---

*마지막 업데이트: 2026-02-04*
