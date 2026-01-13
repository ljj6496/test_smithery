"""마스터파일 관리 서비스

한국투자증권 마스터파일을 다운로드하고 파싱하여 종목 검색 기능 제공
"""

import os
import logging
import zipfile
from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass, field

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DataRange:
    """데이터 보유 기간"""

    start: str
    end: str
    days: int


@dataclass
class ExchangeStatus:
    """거래소 상태"""

    count: int
    last_updated: datetime | None
    file_exists: bool


@dataclass
class MasterStatus:
    """마스터파일 상태"""

    exchanges: dict[str, ExchangeStatus]
    needs_update: bool
    update_check_date: str


@dataclass
class ExchangeInfo:
    """거래소 정보"""

    id: str
    name: str
    country: str


@dataclass
class ExchangeListResponse:
    """거래소 목록"""

    domestic: list[ExchangeInfo]
    overseas: list[ExchangeInfo]


@dataclass
class MasterUpdateResponse:
    """마스터파일 업데이트 결과"""

    success: bool
    updated: list[str]
    counts: dict[str, int]
    errors: dict[str, str] | None = None


@dataclass
class SymbolSearchItem:
    """검색 결과 항목"""

    code: str
    name: str
    exchange: str
    exchange_name: str
    sector: str | None = None
    has_data: bool = False
    data_range: DataRange | None = None


@dataclass
class SymbolSearchResult:
    """검색 결과"""

    query: str
    exchange: str | None
    total: int
    items: list[SymbolSearchItem]


@dataclass
class SymbolDetail:
    """종목 상세 정보"""

    code: str
    name: str
    exchange: str
    exchange_name: str
    english_name: str | None = None
    sector: str | None = None
    listing_date: str | None = None
    market_cap_scale: str | None = None
    has_data: bool = False
    data_range: DataRange | None = None


class MasterService:
    """마스터파일 관리 및 종목 검색 서비스"""

    MASTER_DIR = ".master"
    DATA_DIR = ".data/daily"

    # 거래소 정보
    EXCHANGES = {
        "kospi": {"name": "코스피", "country": "KR", "type": "domestic"},
        "kosdaq": {"name": "코스닥", "country": "KR", "type": "domestic"},
        "konex": {"name": "코넥스", "country": "KR", "type": "domestic"},
        "nasdaq": {"name": "나스닥", "country": "US", "type": "overseas"},
        "nyse": {"name": "뉴욕", "country": "US", "type": "overseas"},
        "amex": {"name": "아멕스", "country": "US", "type": "overseas"},
    }

    # 마스터파일 URL 및 파싱 설정
    MASTER_CONFIG = {
        "kospi": {
            "url": "https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
            "parser": "_parse_kospi",
            "name_key": "korean_name",
            "code_key": "short_code",
        },
        "kosdaq": {
            "url": "https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
            "parser": "_parse_kosdaq",
            "name_key": "korean_name",
            "code_key": "short_code",
        },
        "konex": {
            "url": "https://new.real.download.dws.co.kr/common/master/konex_code.mst.zip",
            "parser": "_parse_konex",
            "name_key": "stock_name",
            "code_key": "short_code",
        },
        "nasdaq": {
            "url": "https://new.real.download.dws.co.kr/common/master/nasmst.cod.zip",
            "parser": "_parse_overseas",
            "name_key": "korea_name",
            "code_key": "symbol",
        },
        "nyse": {
            "url": "https://new.real.download.dws.co.kr/common/master/nysmst.cod.zip",
            "parser": "_parse_overseas",
            "name_key": "korea_name",
            "code_key": "symbol",
        },
        "amex": {
            "url": "https://new.real.download.dws.co.kr/common/master/amsmst.cod.zip",
            "parser": "_parse_overseas",
            "name_key": "korea_name",
            "code_key": "symbol",
        },
    }

    def __init__(self, base_dir: str = "."):
        """서비스 초기화"""
        self.base_dir = base_dir
        self.master_dir = os.path.join(base_dir, self.MASTER_DIR)
        self.data_dir = os.path.join(base_dir, self.DATA_DIR)
        self._ensure_dirs()
        self._cache: dict[str, pd.DataFrame] = {}

    def _ensure_dirs(self):
        """필요한 디렉토리 생성"""
        os.makedirs(self.master_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_csv_path(self, exchange: str) -> str:
        """CSV 파일 경로 반환"""
        return os.path.join(self.master_dir, f"{exchange}.csv")

    def _get_file_mtime(self, path: str) -> datetime | None:
        """파일 수정 시간 반환"""
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            return datetime.fromtimestamp(mtime)
        return None

    def _needs_update(self, exchange: str) -> bool:
        """업데이트 필요 여부 확인 (당일 기준)"""
        csv_path = self._get_csv_path(exchange)
        mtime = self._get_file_mtime(csv_path)
        if mtime is None:
            return True
        return mtime.date() < date.today()

    # ============== 상태 조회 ==============

    def get_status(self) -> MasterStatus:
        """마스터파일 상태 조회"""
        exchanges = {}
        needs_update = False

        for ex_id in self.MASTER_CONFIG.keys():
            csv_path = self._get_csv_path(ex_id)
            file_exists = os.path.exists(csv_path)
            mtime = self._get_file_mtime(csv_path)
            count = 0

            if file_exists:
                try:
                    df = self._load_csv(ex_id)
                    count = len(df)
                except Exception:
                    pass

            if self._needs_update(ex_id):
                needs_update = True

            exchanges[ex_id] = ExchangeStatus(
                count=count,
                last_updated=mtime,
                file_exists=file_exists,
            )

        return MasterStatus(
            exchanges=exchanges,
            needs_update=needs_update,
            update_check_date=date.today().isoformat(),
        )

    def get_exchanges(self) -> ExchangeListResponse:
        """지원 거래소 목록 반환"""
        domestic = []
        overseas = []

        for ex_id, info in self.EXCHANGES.items():
            ex_info = ExchangeInfo(
                id=ex_id,
                name=info["name"],
                country=info["country"],
            )
            if info["type"] == "domestic":
                domestic.append(ex_info)
            else:
                overseas.append(ex_info)

        return ExchangeListResponse(domestic=domestic, overseas=overseas)

    # ============== 마스터파일 업데이트 ==============

    async def update_master(
        self, exchanges: list[str] | None = None
    ) -> MasterUpdateResponse:
        """마스터파일 업데이트"""
        if exchanges is None:
            exchanges = list(self.MASTER_CONFIG.keys())

        updated = []
        counts = {}
        errors = {}

        async with httpx.AsyncClient(timeout=60.0) as client:
            for ex_id in exchanges:
                if ex_id not in self.MASTER_CONFIG:
                    errors[ex_id] = f"Unknown exchange: {ex_id}"
                    continue

                try:
                    df = await self._download_and_parse(client, ex_id)
                    csv_path = self._get_csv_path(ex_id)
                    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

                    # 캐시 갱신
                    self._cache[ex_id] = df

                    updated.append(ex_id)
                    counts[ex_id] = len(df)
                    logger.info(f"Updated {ex_id} master: {len(df)} symbols")

                except Exception as e:
                    logger.error(f"Failed to update {ex_id}: {e}")
                    errors[ex_id] = str(e)

        return MasterUpdateResponse(
            success=len(errors) == 0,
            updated=updated,
            counts=counts,
            errors=errors if errors else None,
        )

    async def _download_and_parse(
        self, client: httpx.AsyncClient, exchange: str
    ) -> pd.DataFrame:
        """마스터파일 다운로드 및 파싱"""
        config = self.MASTER_CONFIG[exchange]
        url = config["url"]
        parser_name = config["parser"]

        # 다운로드
        logger.info(f"Downloading {exchange} master from {url}")
        response = await client.get(url)
        response.raise_for_status()

        # ZIP 압축 해제
        temp_zip = os.path.join(self.master_dir, f"{exchange}_temp.zip")
        temp_mst = os.path.join(self.master_dir, f"{exchange}_temp.mst")

        try:
            with open(temp_zip, "wb") as f:
                f.write(response.content)

            with zipfile.ZipFile(temp_zip, "r") as zf:
                # 첫 번째 파일 추출
                extracted = zf.namelist()[0]
                zf.extract(extracted, self.master_dir)
                extracted_path = os.path.join(self.master_dir, extracted)

                # 이름 변경
                if extracted_path != temp_mst:
                    if os.path.exists(temp_mst):
                        os.remove(temp_mst)
                    os.rename(extracted_path, temp_mst)

            # 파싱
            parser = getattr(self, parser_name)
            df = parser(temp_mst, exchange)

            return df

        finally:
            # 임시 파일 정리
            for f in [temp_zip, temp_mst]:
                if os.path.exists(f):
                    os.remove(f)

    # ============== 파싱 메서드 ==============

    def _read_file_content(self, file_path: str) -> str:
        """여러 인코딩으로 파일 읽기 시도"""
        encodings = ["cp949", "euc-kr", "utf-8", "utf-8-sig"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError("Failed to decode file with any encoding")

    def _parse_kospi(self, file_path: str, exchange: str) -> pd.DataFrame:
        """코스피 마스터파일 파싱"""
        content = self._read_file_content(file_path)

        data = []
        for row in content.splitlines():
            if len(row) < 230:
                continue

            # 앞부분: 단축코드, 표준코드, 한글명
            front = row[: len(row) - 228]
            short_code = front[0:9].strip()
            standard_code = front[9:21].strip()
            korean_name = front[21:].strip()

            data.append(
                {
                    "short_code": short_code,
                    "standard_code": standard_code,
                    "korean_name": korean_name.replace(" ", ""),
                    "exchange": exchange,
                    "sector": None,
                }
            )

        return pd.DataFrame(data)

    def _parse_kosdaq(self, file_path: str, exchange: str) -> pd.DataFrame:
        """코스닥 마스터파일 파싱"""
        content = self._read_file_content(file_path)

        data = []
        for row in content.splitlines():
            if len(row) < 224:
                continue

            # 앞부분: 단축코드, 표준코드, 한글명
            front = row[: len(row) - 222]
            short_code = front[0:9].strip()
            standard_code = front[9:21].strip()
            korean_name = front[21:].strip()

            data.append(
                {
                    "short_code": short_code,
                    "standard_code": standard_code,
                    "korean_name": korean_name.replace(" ", ""),
                    "exchange": exchange,
                    "sector": None,
                }
            )

        return pd.DataFrame(data)

    def _parse_konex(self, file_path: str, exchange: str) -> pd.DataFrame:
        """코넥스 마스터파일 파싱"""
        content = self._read_file_content(file_path)

        data = []
        for row in content.splitlines():
            row = row.strip()
            if len(row) < 50:
                continue

            short_code = row[0:9].strip()
            standard_code = row[9:21].strip()
            stock_name = row[21:-184].strip() if len(row) > 205 else row[21:].strip()

            data.append(
                {
                    "short_code": short_code,
                    "standard_code": standard_code,
                    "korean_name": stock_name.replace(" ", ""),
                    "exchange": exchange,
                    "sector": None,
                }
            )

        return pd.DataFrame(data)

    def _parse_overseas(self, file_path: str, exchange: str) -> pd.DataFrame:
        """해외주식 마스터파일 파싱 (탭 구분)"""
        encodings = ["cp949", "euc-kr", "utf-8"]
        df = None

        for enc in encodings:
            try:
                df = pd.read_csv(file_path, sep="\t", encoding=enc, dtype=str)
                break
            except Exception:
                continue

        if df is None:
            raise ValueError("Failed to parse overseas master file")

        # 컬럼명 매핑
        columns = [
            "national_code",
            "exchange_id",
            "exchange_code",
            "exchange_name",
            "symbol",
            "realtime_symbol",
            "korea_name",
            "english_name",
            "security_type",
            "currency",
            "float_position",
            "data_type",
            "base_price",
            "bid_order_size",
            "ask_order_size",
            "market_start_time",
            "market_end_time",
            "dr_yn",
            "dr_country_code",
            "industry_code",
            "index_constituent_yn",
            "tick_size_type",
            "classification_code",
            "tick_size_type_detail",
        ]

        if len(df.columns) >= len(columns):
            df.columns = columns[: len(df.columns)]

        # 필요한 컬럼만 추출
        result = pd.DataFrame(
            {
                "short_code": df["symbol"].str.strip(),
                "standard_code": df["symbol"].str.strip(),
                "korean_name": df["korea_name"].str.strip().str.replace(" ", ""),
                "english_name": df.get(
                    "english_name", pd.Series(dtype=str)
                ).str.strip(),
                "exchange": exchange,
                "sector": None,
            }
        )

        return result

    # ============== 종목 검색 ==============

    def _load_csv(self, exchange: str) -> pd.DataFrame:
        """CSV 파일 로드 (캐시 사용)"""
        if exchange in self._cache:
            return self._cache[exchange]

        csv_path = self._get_csv_path(exchange)
        if not os.path.exists(csv_path):
            return pd.DataFrame()

        df = pd.read_csv(csv_path, dtype=str)
        df = df.fillna("")
        self._cache[exchange] = df
        return df

    def _get_data_range(self, code: str) -> DataRange | None:
        """종목의 데이터 보유 기간 확인"""
        # 국내/해외 데이터 디렉토리 모두 확인
        for data_dir in [self.data_dir, os.path.join(self.base_dir, ".data/overseas")]:
            data_path = os.path.join(data_dir, f"{code}.csv")
            if os.path.exists(data_path):
                try:
                    df = pd.read_csv(data_path)
                    if "date" in df.columns and len(df) > 0:
                        dates = pd.to_datetime(df["date"])
                        return DataRange(
                            start=dates.min().strftime("%Y-%m-%d"),
                            end=dates.max().strftime("%Y-%m-%d"),
                            days=len(df),
                        )
                except Exception:
                    pass
        return None

    def search_symbols(
        self,
        q: str,
        exchange: Optional[str] = None,
        limit: int = 20,
    ) -> SymbolSearchResult:
        """종목 검색"""
        results = []
        q_lower = q.lower().strip()

        # 검색 대상 거래소
        if exchange:
            exchanges = [exchange] if exchange in self.MASTER_CONFIG else []
        else:
            exchanges = list(self.MASTER_CONFIG.keys())

        for ex_id in exchanges:
            df = self._load_csv(ex_id)
            if df.empty:
                continue

            # 코드 또는 이름으로 검색
            mask = df["short_code"].str.lower().str.contains(
                q_lower, na=False
            ) | df["korean_name"].str.lower().str.contains(q_lower, na=False)

            # 영문명이 있으면 추가 검색
            if "english_name" in df.columns:
                mask |= df["english_name"].str.lower().str.contains(q_lower, na=False)

            matched = df[mask]

            for _, row in matched.iterrows():
                code = row["short_code"]
                data_range = self._get_data_range(code)

                results.append(
                    SymbolSearchItem(
                        code=code,
                        name=row["korean_name"],
                        exchange=ex_id,
                        exchange_name=self.EXCHANGES[ex_id]["name"],
                        sector=row.get("sector") if row.get("sector") else None,
                        has_data=data_range is not None,
                        data_range=data_range,
                    )
                )

                if len(results) >= limit:
                    break

            if len(results) >= limit:
                break

        return SymbolSearchResult(
            query=q,
            exchange=exchange,
            total=len(results),
            items=results[:limit],
        )

    def get_symbol(self, code: str) -> SymbolDetail | None:
        """종목 상세 정보 조회"""
        code = code.upper().strip()

        for ex_id in self.MASTER_CONFIG.keys():
            df = self._load_csv(ex_id)
            if df.empty:
                continue

            matched = df[df["short_code"].str.upper() == code]
            if len(matched) > 0:
                row = matched.iloc[0]
                data_range = self._get_data_range(code)

                return SymbolDetail(
                    code=row["short_code"],
                    name=row["korean_name"],
                    english_name=(
                        row.get("english_name") if row.get("english_name") else None
                    ),
                    exchange=ex_id,
                    exchange_name=self.EXCHANGES[ex_id]["name"],
                    sector=row.get("sector") if row.get("sector") else None,
                    listing_date=None,
                    market_cap_scale=None,
                    has_data=data_range is not None,
                    data_range=data_range,
                )

        return None


# 싱글톤 인스턴스
_master_service: MasterService | None = None


def get_master_service(base_dir: str = ".") -> MasterService:
    """MasterService 싱글톤 반환"""
    global _master_service
    if _master_service is None:
        _master_service = MasterService(base_dir)
    return _master_service
