from typing import Annotated

from fastapi import APIRouter, Depends, Query
import aiohttp
from loguru import logger

from ..dependencies import graph
from ..dependencies import http_pool
from ..dependencies import blocklist
from fastapi import HTTPException

router = APIRouter(tags=["graphs"])

@router.post("/neighbors/eth_transfers")
@router.get("/neighbors/eth_transfers")
async def get_neighbors_eth_transfers(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  k: Annotated[int, Query(le=5)] = 2,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  http_pool: aiohttp.ClientSession = Depends(http_pool.get_async_client),
  non_eoa_list: set = Depends(blocklist.get_non_eoa_list)
):
  logger.debug(addresses)
  try:
    result = await graph.get_neighbors_scores(
                                        http_pool, 
                                        addresses, 
                                        k, 
                                        limit, 
                                        'eth', 
                                        blocklist=non_eoa_list)
    logger.debug(f"result from get_neighbors_scores: {result}")
    logger.info(f"number of neighbors from get_neighbors_scores: {len(result)}")
    resp = {"result": result}
    return resp
  except Exception as exc:
    logger.error(f"Unknown error: {exc}")
    raise HTTPException(status_code=500, detail="Unknown error")


