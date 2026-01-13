"""종목코드 검색 Remote MCP 서버

Remote MCP Server Design Skill에 따른 모듈화된 서버 구조
"""

import sys
import os
import asyncio
import logging

# 패키지 경로 추가
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP

from src.tools.master_tools import register_master_tools

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MCP 서버 초기화
mcp = FastMCP(
    name="종목코드 검색",
    instructions="""종목코드 검색 MCP 서버

국내/해외 주식 종목코드를 검색하고 조회합니다.

## 주요 기능
- search_symbols: 종목 검색 (코드/이름)
- get_symbol: 종목 상세 정보 조회
- get_master_status: 마스터파일 상태 확인
- update_master: 마스터파일 갱신
- get_exchanges: 지원 거래소 목록

## 지원 거래소
- 국내: 코스피, 코스닥, 코넥스
- 해외: 나스닥, 뉴욕, 아멕스
""",
    host="0.0.0.0",  # Remote 접속 허용
    port=8000,
)

# 도구 등록
register_master_tools(mcp)

logger.info("종목코드 검색 MCP 서버 초기화 완료")


if __name__ == "__main__":
    logger.info("서버 시작: http://0.0.0.0:8000/mcp")
    mcp.run(transport="streamable-http")
