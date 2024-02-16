from typing import Annotated
import asyncio

from fastapi import APIRouter, Depends, Query
import httpx
from loguru import logger

from ..dependencies import nexandria_client
from ..dependencies import httpx_pool

router = APIRouter(tags=["graphs"])

@router.post("/neighbors/eth_transfers")
@router.get("/neighbors/eth_transfers")
async def get_neighbors_eth_transfers(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  httpxclient: httpx.AsyncClient = Depends(httpx_pool.get_async_client)
):
  logger.debug(addresses)
  loop = asyncio.get_event_loop()
  result = await nexandria_client.fetch_graph(httpxclient, addresses)
  return {"result": result}


