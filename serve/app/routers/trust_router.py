from typing import Annotated
import asyncio

from fastapi import APIRouter, Depends, Query,Path, HTTPException
import aiohttp
from loguru import logger

from ..dependencies import graph, http_pool, blocklist, sema

router = APIRouter(tags=["scores"])

@router.post("/neighbors/{blockchain}")
@router.get("/neighbors/{blockchain}")
async def get_neighbors_transfers(
  # Example: -d '["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"]'
  addresses: list[str],
  blockchain: Annotated[str, Path()],
  k: Annotated[int, Query(le=10)] = 5,
  limit: Annotated[int | None, Query(le=1000)] = 100,
  http_pool: aiohttp.ClientSession = Depends(http_pool.get_async_client),
  sema: asyncio.Semaphore = Depends(sema.get_semaphore),
  non_eoa_list: set = Depends(blocklist.get_non_eoa_list),
):
  """
  Given a list of input addresses, return a list of addresses
    trusted by the extended network of the input addresses. \n
  The addresses in the result are ranked by a relative scoring mechanism 
    that is based on the EigenTrust algorithm. \n
  The extended network is derived based on a BFS traversal of the social engagement graph 
    upto **k** degrees and until **limit** is reached. \n
  Example: ["0x4114e33eb831858649ea3702e1c9a2db3f626446", "0x8773442740c17c9d0f0b87022c722f9a136206ed"] \n
  **IMPORTANT**: Please use HTTP POST method and not GET method.
  """
  logger.debug(list(map(str.lower,addresses)))
  try:
    scores = await graph.get_neighbors_scores(
                                        sema,
                                        http_pool, 
                                        addresses, 
                                        k, 
                                        limit, 
                                        blockchain, 
                                        blocklist=non_eoa_list)
    logger.debug(f"result from get_neighbors_scores: {scores}")
    logger.info(f"number of neighbors from get_neighbors_scores: {len(scores)}")
    # filter out the input address
    res = [ score for score in scores if not score['address'] in addresses]
    logger.debug(f"Result has {len(res)} rows")
    return {"result": res}
  except Exception as exc:
    logger.error(f"Unknown error: {exc}")
    raise HTTPException(status_code=500, detail="Unknown error")


