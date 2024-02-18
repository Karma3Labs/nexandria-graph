import time
from loguru import logger
import requests
from fastapi import HTTPException

from ..config import settings

async def go_eigentrust(
    pretrust: list[dict],
    max_pt_id: int,
    localtrust: list[dict],
    max_lt_id: int,
):
  start_time = time.perf_counter()
  req = {
  	"pretrust": {
  		"scheme": 'inline',
  		"size": int(max_pt_id)+1, #np.int64 doesn't serialize; cast to int
  		"entries": pretrust,
  	},
    "localTrust": {
  		"scheme": 'inline',
  		"size": int(max_lt_id)+1, #np.int64 doesn't serialize; cast to int
  		"entries": localtrust,
  	},
  	"alpha": settings.EIGENTRUST_ALPHA, 
  	"epsilon": settings.EIGENTRUST_EPSILON,
    "max_iterations": settings.EIGENTRUST_MAX_ITER,
  	"flatTail": settings.EIGENTRUST_FLAT_TAIL
  }

  logger.trace(req)
  # TODO replace requests with aiohttp
  response = requests.post(f"{settings.GO_EIGENTRUST_URL}/basic/v1/compute",
                           json=req,
                           headers = {
                              'Accept': 'application/json',
                              'Content-Type': 'application/json'
                              },
                           timeout=settings.GO_EIGENTRUST_TIMEOUT_MS)

  if response.status_code != 200:
      logger.error(f"Server error: {response.status_code}:{response.reason}")
      raise HTTPException(status_code=response.status_code, detail=response.reason)
  trustscores = response.json()['entries']
  logger.info(f"eigentrust took {time.perf_counter() - start_time} secs for {len(trustscores)} scores")
  return trustscores