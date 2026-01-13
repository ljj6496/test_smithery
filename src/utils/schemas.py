"""표준 출력 스키마

Remote MCP Server Design Skill에 따른 표준화된 응답 구조
"""

from typing import Any, Literal

# 표준 출력 스키마
STANDARD_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["success", "partial_success", "error", "no_results"],
            "description": "실행 상태",
        },
        "message": {
            "type": "string",
            "description": "상태 메시지",
        },
        "total_count": {
            "type": "integer",
            "description": "총 결과 수",
        },
        "results": {
            "type": "array",
            "items": {"type": "object"},
            "description": "실행 결과 데이터",
        },
        "metadata": {
            "type": "object",
            "description": "추가 메타데이터",
        },
    },
    "required": ["status", "message", "total_count", "results"],
}


def make_response(
    status: Literal["success", "partial_success", "error", "no_results"],
    message: str,
    results: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """표준 응답 생성 헬퍼"""
    return {
        "status": status,
        "message": message,
        "total_count": len(results) if results else 0,
        "results": results or [],
        "metadata": metadata,
    }
