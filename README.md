# 한투 마스터파일 Remote MCP

한국투자증권 마스터파일을 관리하고 종목 검색 기능을 제공하는 Remote MCP 서버

## 기능

- 마스터파일 자동 다운로드 및 파싱
- 종목 검색 (코드, 한글명, 영문명)
- 지원 거래소: 코스피, 코스닥, 코넥스, 나스닥, 뉴욕, 아멕스
- Remote MCP (Streamable HTTP transport) 지원

## 설치

```bash
uv sync
```

## 서버 실행

### Remote MCP (Streamable HTTP)

```bash
uv run python server.py
```

서버가 `http://0.0.0.0:8000/mcp`에서 실행됩니다.

### Local (Stdio)

```bash
uv run mcp run server.py
```

## 클라이언트 설정

### Cursor/Claude Desktop (Remote)

```json
{
  "mcpServers": {
    "hantoo-mcp": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Cursor/Claude Desktop (Local)

```json
{
  "mcpServers": {
    "hantoo-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/hantoo_mcp", "mcp", "run", "server.py"]
    }
  }
}
```

## MCP Tools

| Tool | 설명 |
|------|------|
| `search_symbols` | 종목 검색 (코드/이름) |
| `get_symbol` | 종목 상세 정보 조회 |
| `get_master_status` | 마스터파일 상태 확인 |
| `update_master` | 마스터파일 수동 갱신 |
| `get_exchanges` | 지원 거래소 목록 |

## 응답 형식

모든 Tool은 표준화된 응답 형식을 사용합니다:

```json
{
  "status": "success",
  "message": "검색 완료: 5개 결과",
  "total_count": 5,
  "results": [...],
  "metadata": {...}
}
```

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `HANTOO_DATA_DIR` | 데이터 디렉토리 경로 | `.` |

## 디렉토리 구조

```
hantoo_mcp/
├── server.py           # 메인 서버
├── src/
│   ├── master_service.py
│   ├── tools/
│   │   └── master_tools.py
│   └── utils/
│       └── schemas.py
├── docs/
└── skills/
```
