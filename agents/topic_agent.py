# 카테고리 - 세부 주제
# 세부 주제 - 제목 후보

import os
import json

class TopicAgent:
    def __init__(self, client):
        # Ollama와 대화할 수 있는 클라이언트를 가져옵니다.
        self.client = client
        # 프롬프트가 저장된 폴더 이름이에요.
        self.folder = "prompts"

    def read_file(self, file_name):
        """폴더에서 마크다운 파일을 읽어오는 간단한 함수입니다."""
        path = f"{self.folder}/{file_name}.md"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def suggest_topics(self, category, job):
        """1. 카테고리를 보고 제목 후보 5개를 제안합니다."""
        # 파일에서 지침서를 읽어옵니다.
        prompt = self.read_file("topic_titles")
        
        # 지침서 안의 빈칸({category}, {job})을 실제 내용으로 채웁니다.
        prompt = prompt.replace("{category}", category)
        prompt = prompt.replace("{job}", job)
        
        # AI에게 물어보고 결과를 받습니다.
        result = self.client.generate_json("주제 기획자", prompt)
        
        # AI가 리스트 형식이 아니라 엉뚱하게 줄 때를 대비한 '정규화'
        if isinstance(result, list):
            return result[:5]
        elif isinstance(result, dict):
            return result.get("topics", ["제목 생성 실패"])
        
        return ["추천 제목 1", "추천 제목 2", "추천 제목 3"]

    def generate_plan(self, topic, job, mbti):
        """2. 선택한 제목으로 블로그 설계도를 만듭니다."""
        # 설계도 작성용 지침서를 읽어옵니다.
        prompt = self.read_file("outline")
        
        # 빈칸 채우기
        prompt = prompt.replace("{topic}", topic)
        prompt = prompt.replace("{job}", job)
        prompt = prompt.replace("{mbti}", mbti)
        
        # AI 호출
        raw_data = self.client.generate_json("콘텐츠 전략가", prompt)
        
        # [정규화] 데이터가 비어있어도 UI가 안 깨지게 기본값을 채워줍니다.
        # .get("키이름", "기본값")을 쓰면 데이터가 없어도 에러가 안 나요!
        plan = {
            "targetSituation": raw_data.get("targetSituation", "정보를 찾는 독자"),
            "format": raw_data.get("format", "정보 전달형"),
            "tone": raw_data.get("tone", "차분한 말투"),
            "keywords": raw_data.get("keywords", {"main": topic, "sub": []})
        }
        
        return plan
