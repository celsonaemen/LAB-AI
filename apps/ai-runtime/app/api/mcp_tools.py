from fastapi import APIRouter, HTTPException
from app.mcp_tools.client import discover, MCPToolError

router = APIRouter(prefix='/internal/v1', tags=['tools'])


@router.get('/tools')
def tools():
    """Discover schemas and permissions, without granting execution rights."""
    try:
        return discover()
    except MCPToolError:
        raise HTTPException(status_code=503, detail='MCP discovery unavailable') from None
