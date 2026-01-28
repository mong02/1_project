주제 : SNS 포스팅 자동 생성기 (Social Media Auto Generator Agent)

제품/서비스 정보를 입력하면   캠페인 세트 + 채널별 맞춤 SNS 게시글을 자동으로 생성해 주는  
로컬 AI 기반 콘텐츠 생성 에이전트입니다

주제를 선택한 이유 :

AI 기술이 단순 질의응답을 넘어 실제 업무를 대체·보조하는 방향으로 확장되고 있는 상황에서, 본 프로젝트는 AI를 콘텐츠 제작 에이전트로 활용하는 사례를 구현하고자 선택하였습니다. 특히 SNS 마케팅이라는 현실적인 문제를 해결 대상으로 삼아, AI가 전략 수립과 콘텐츠 생성을 단계적으로 수행하도록 설계한 점이 본 주제의 핵심입니다.


📁 주요 기능
- 캠페인용 게시글 자동 생성
- 인스타그램 / 블로그 / 스레드 / 링크드인 채널별 맞춤 문장
- 후킹 문장 A/B 후보 자동 생성
- 전략형 해시태그 생성
- 과장·금지어 등 리스크 표현 자동 검수
- Ollama 기반 로컬 AI 사용 (외부 API 비용 없음)

📁 동작 구조
1. 사용자가 UI에서 제품 정보, 목표, 톤, 채널을 입력
2. FastAPI 서버가 요청을 수신
3. AI 에이전트가 순차적으로
   - 전략 수립
   - 후킹 문장 생성
   - 채널별 게시글 생성
   - 리스크 표현 검수
4. 결과를 UI 화면에 출력

📁 프로젝트 구조
social-agent/
├─ app/
│ ├─ main.py # FastAPI 서버 진입점
│ ├─ schemas.py # 요청/응답 데이터 모델
│ ├─ llm/ # Ollama 연동
│ ├─ agents/ # AI 에이전트 로직
│ └─ utils/
├─ ui_app.py # Streamlit UI
├─ requirements.txt
└─ README.txt


📁 실행 방법
가상환경 생성 및 활성화

python -m venv .venv
.\.venv\Scripts\activate

필수 패키지 설치

pip install -r requirements.txt

터미널 2개 실행 
터미널 1 : API 서버 실행 

.\.venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000

터미널 2 : UI 실행 

.\.venv\Scripts\activate
streamlit run ui_app.py

ollama 준비 (저희가 강의 때 설치한 거 그대로라 딱히 만질필요 없습니다!)

* 실행 도중 오류가 난다면?
No module named uvicorn
→ 가상환경(.venv) 활성화 안 된 상태에서 실행한 경우

UI에서 API 연결 실패
→ FastAPI 서버(8000 포트)를 먼저 실행하지 않은 경우

결과가 생성되지 않음
→ Ollama 미실행 또는 모델 미다운로드





