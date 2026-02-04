"""
프롬프트 파일 로더 유틸리티

프롬프트 .md 파일을 읽어와서 변수 치환을 수행합니다.
"""

import os
import re
from typing import Dict, Any
import json


def load_prompt(filename: str, prompts_dir: str = "prompts") -> str:
    """
    프롬프트 파일을 로드합니다.
    
    Args:
        filename: 프롬프트 파일 이름 (.md 확장자 제외)
        prompts_dir: 프롬프트 파일이 저장된 디렉토리 (기본값: "prompts")
    
    Returns:
        프롬프트 문자열
    
    Raises:
        FileNotFoundError: 파일이 존재하지 않을 경우
    """
    path = os.path.join(prompts_dir, f"{filename}.md")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def render_prompt(template: str, variables: Dict[str, Any]) -> str:
    """
    프롬프트 템플릿에 변수를 치환합니다.
    
    {variable_name} 형식의 플레이스홀더를 실제 값으로 대체합니다.
    
    Args:
        template: 프롬프트 템플릿 문자열
        variables: 치환할 변수 딕셔너리
    
    Returns:
        변수가 치환된 프롬프트 문자열
    """
    if not template:
        return ""
    
    def _get_value(key: str) -> str:
        """변수 딕셔너리에서 값을 가져와 문자열로 변환합니다."""
        value = variables.get(key)
        
        if value is None:
            return ""
        
        # dict나 list는 JSON 형식으로 변환
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        
        # 나머지는 문자열로 변환
        return str(value).strip() if value is not None else ""
    
    # {variable_name} 패턴을 찾아서 치환
    placeholder_pattern = re.compile(r"\{([a-zA-Z0-9_]+)\}")
    return placeholder_pattern.sub(lambda m: _get_value(m.group(1)), template)


def load_and_render_prompt(filename: str, variables: Dict[str, Any], prompts_dir: str = "prompts") -> str:
    """
    프롬프트 파일을 로드하고 변수를 치환합니다.
    
    load_prompt()와 render_prompt()를 결합한 편의 함수입니다.
    
    Args:
        filename: 프롬프트 파일 이름 (.md 확장자 제외)
        variables: 치환할 변수 딕셔너리
        prompts_dir: 프롬프트 파일이 저장된 디렉토리
    
    Returns:
        변수가 치환된 프롬프트 문자열
    """
    template = load_prompt(filename, prompts_dir)
    return render_prompt(template, variables)
