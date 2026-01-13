"""마스터파일 관련 MCP Tools

표준 출력 스키마를 적용한 종목 검색 도구
"""

from dataclasses import asdict
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from src.utils.schemas import STANDARD_OUTPUT_SCHEMA, make_response
from src.master_service import get_master_service, MasterService


def _get_service() -> MasterService:
    """서비스 인스턴스 반환"""
    import os

    base_dir = os.environ.get("HANTOO_DATA_DIR", ".")
    return get_master_service(base_dir)


def register_master_tools(mcp: FastMCP):
    """마스터파일 관련 도구 등록"""

    @mcp.tool(
        name="search_symbols",
        description="종목 검색 - 종목코드나 이름으로 국내/해외 종목을 검색합니다",
    )
    async def search_symbols(
        query: Annotated[str, "검색어 (종목코드 또는 이름)"],
        exchange: Annotated[
            str | None, "거래소 필터 (kospi, kosdaq, konex, nasdaq, nyse, amex)"
        ] = None,
        limit: Annotated[int, "결과 개수 제한"] = 20,
    ) -> dict:
        """종목 검색"""
        if not query or not query.strip():
            return make_response(
                status="error",
                message="검색어가 필요합니다",
            )

        try:
            service = _get_service()
            result = service.search_symbols(query, exchange, limit)

            items = [
                {
                    "code": item.code,
                    "name": item.name,
                    "exchange": item.exchange,
                    "exchange_name": item.exchange_name,
                    "sector": item.sector,
                    "has_data": item.has_data,
                    "data_range": asdict(item.data_range) if item.data_range else None,
                }
                for item in result.items
            ]

            if not items:
                return make_response(
                    status="no_results",
                    message=f"'{query}' 검색 결과 없음",
                    metadata={"query": query, "exchange": exchange},
                )

            return make_response(
                status="success",
                message=f"'{query}' 검색 완료: {len(items)}개 결과",
                results=items,
                metadata={"query": query, "exchange": exchange, "limit": limit},
            )

        except Exception as e:
            return make_response(
                status="error",
                message=f"검색 실행 오류: {str(e)}",
            )

    @mcp.tool(
        name="get_symbol",
        description="종목 상세 정보 조회 - 종목코드로 상세 정보를 조회합니다",
    )
    async def get_symbol(
        code: Annotated[str, "종목코드"],
    ) -> dict:
        """종목 상세 정보 조회"""
        if not code or not code.strip():
            return make_response(
                status="error",
                message="종목코드가 필요합니다",
            )

        try:
            service = _get_service()
            result = service.get_symbol(code)

            if result is None:
                return make_response(
                    status="no_results",
                    message=f"종목 '{code}'을(를) 찾을 수 없습니다",
                    metadata={"code": code},
                )

            item = {
                "code": result.code,
                "name": result.name,
                "english_name": result.english_name,
                "exchange": result.exchange,
                "exchange_name": result.exchange_name,
                "sector": result.sector,
                "listing_date": result.listing_date,
                "market_cap_scale": result.market_cap_scale,
                "has_data": result.has_data,
                "data_range": asdict(result.data_range) if result.data_range else None,
            }

            return make_response(
                status="success",
                message=f"종목 '{result.name}' 조회 완료",
                results=[item],
                metadata={"code": code},
            )

        except Exception as e:
            return make_response(
                status="error",
                message=f"종목 조회 오류: {str(e)}",
            )

    @mcp.tool(
        name="get_master_status",
        description="마스터파일 상태 확인 - 거래소별 종목 수, 업데이트 시간 확인",
    )
    async def get_master_status() -> dict:
        """마스터파일 상태 확인"""
        try:
            service = _get_service()
            status = service.get_status()

            exchanges = [
                {
                    "id": ex_id,
                    "count": ex_status.count,
                    "last_updated": (
                        ex_status.last_updated.isoformat()
                        if ex_status.last_updated
                        else None
                    ),
                    "file_exists": ex_status.file_exists,
                }
                for ex_id, ex_status in status.exchanges.items()
            ]

            return make_response(
                status="success",
                message="마스터파일 상태 조회 완료",
                results=exchanges,
                metadata={
                    "needs_update": status.needs_update,
                    "update_check_date": status.update_check_date,
                },
            )

        except Exception as e:
            return make_response(
                status="error",
                message=f"상태 조회 오류: {str(e)}",
            )

    @mcp.tool(
        name="update_master",
        description="마스터파일 갱신 - 한국투자증권에서 최신 종목 정보 다운로드",
    )
    async def update_master(
        exchanges: Annotated[
            list[str] | None,
            "갱신할 거래소 목록 (미지정시 전체). 예: ['kospi', 'kosdaq']",
        ] = None,
    ) -> dict:
        """마스터파일 갱신"""
        try:
            service = _get_service()
            result = await service.update_master(exchanges)

            if result.success:
                return make_response(
                    status="success",
                    message=f"마스터파일 갱신 완료: {', '.join(result.updated)}",
                    results=[
                        {"exchange": ex, "count": cnt}
                        for ex, cnt in result.counts.items()
                    ],
                    metadata={"updated": result.updated},
                )
            else:
                return make_response(
                    status="partial_success" if result.updated else "error",
                    message=f"일부 갱신 실패: {result.errors}",
                    results=[
                        {"exchange": ex, "count": cnt}
                        for ex, cnt in result.counts.items()
                    ],
                    metadata={"updated": result.updated, "errors": result.errors},
                )

        except Exception as e:
            return make_response(
                status="error",
                message=f"마스터파일 갱신 오류: {str(e)}",
            )

    @mcp.tool(
        name="get_exchanges",
        description="지원 거래소 목록 조회 - 국내/해외 거래소 목록 반환",
    )
    async def get_exchanges() -> dict:
        """지원 거래소 목록 조회"""
        try:
            service = _get_service()
            result = service.get_exchanges()

            exchanges = [
                {"id": ex.id, "name": ex.name, "country": ex.country, "type": "domestic"}
                for ex in result.domestic
            ] + [
                {"id": ex.id, "name": ex.name, "country": ex.country, "type": "overseas"}
                for ex in result.overseas
            ]

            return make_response(
                status="success",
                message=f"지원 거래소: {len(exchanges)}개",
                results=exchanges,
                metadata={
                    "domestic_count": len(result.domestic),
                    "overseas_count": len(result.overseas),
                },
            )

        except Exception as e:
            return make_response(
                status="error",
                message=f"거래소 목록 조회 오류: {str(e)}",
            )
