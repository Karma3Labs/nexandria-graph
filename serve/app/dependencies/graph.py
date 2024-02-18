import asyncio
from threading import Lock
import aiohttp
from loguru import logger
from ..config import settings
from . import eigentrust_client
from dataclasses import dataclass
import time

class ThreadSafeEdgeList():
  def __init__(self, init_addr_list:list[str]):
    self._edges = []
    self._addr_set = set(init_addr_list)
    self._lock = Lock()

  def add_edge(self, edge:dict) -> tuple[bool, int]:
    with self._lock:
      self._edges.append(edge)

  def is_first_traversal(self, key:str) -> tuple[bool, int]:
    with self._lock:
      if not key in self._addr_set:
        self._addr_set.add(key)
        return True, len(self._addr_set)
      return False, len(self._addr_set)

  def get_edge_list(self):
    return self._edges
  
  def get_address_set(self):
    return self._addr_set

@dataclass(frozen=True)
class TaskContext:
  max_depth: int
  max_num_results: int
  chain: str
  params: dict
  blocklist: set

# coroutine task
async def fetch_address(
  http_pool: aiohttp.ClientSession,
  task_group: asyncio.TaskGroup, 
  results: ThreadSafeEdgeList,
  address: str,
  context: TaskContext
):
  url = f"{settings.NEXANDRIA_URL}/{context.chain}/v1/address/{address}/neighbors"
  logger.info(f"fetch_address: {url}")
  try:
    start_time = time.perf_counter()
    async with http_pool.get(url, 
                             params=context.params, 
                             raise_for_status=True) as http_resp:
      resp = await http_resp.json()
    # TODO replace with a timer context manager
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{url} took {elapsed_time} secs")
  except asyncio.TimeoutError as exc:
    logger.error(f"Nexandria timed out for {url}")
    return
  except aiohttp.ClientError as exc:
    logger.error(f"HTTP Exception for {url} - {exc}")
    return
  if resp.get('error'):
    # Nexandria always returns HTTP 200 with error in the response body
    logger.error(f"Nexandria Internal error: {address}: {resp.get('error')}")
    return
  neighbors = resp.get('neighbors') or ()

  for neighbor in neighbors:
    neighbor_addr = neighbor['neighbor_info']['address']

    # skip if this is an eoa to contract transfer
    if neighbor_addr in context.blocklist:
      logger.debug(f"skipping fetch for contract address {neighbor_addr}")
      continue

    # Nexandria will return transfers_to_neighbor = 0 if:
    # a) transfer is outgoing (or)
    # b) transfer is very old and happened before from_ts
    if neighbor["transfers_to_neighbor"] == 0:
      logger.debug(f"skipping fetch for 0 transfer to address {neighbor_addr}")
      continue
    v = settings.DEFAULT_TRANSFER_VALUE \
          if neighbor.get("fiat_to_neighbor") is None \
          else float(neighbor.get("fiat_to_neighbor").replace(',',''))
    val = {"i":address, "j":neighbor_addr, "v": v}
    results.add_edge(val)

    is_traverse, counter = results.is_first_traversal(neighbor_addr)
    if is_traverse and counter < context.max_num_results:
      task_group.create_task(fetch_address(http_pool, task_group, results, neighbor_addr, context))
  return 
 
async def get_neighbors_scores(
    http_pool: aiohttp.ClientSession,
    addresses: list[str],
    k: int,
    limit: int,
    chain: str,
    blocklist: set
) -> list[dict]:
  start_time = time.perf_counter()
  results = ThreadSafeEdgeList(addresses)
  context = TaskContext(
    max_depth=k,
    max_num_results=limit,
    chain=chain,
    params={ 'details': 'summary', 
            'from_ts': 1672531200, # since 1/1/2023 00:00:00 UTC  
            'to_ts': round(time.time()) - 600000,  # now minus 10 mins
            'block_cp': 'native' # to specify the Zero address, typically used for fee/burn/mint transactions
            },
    # blocklist = np.array(['0x39aa39c021dfbae8fac545936693ac917d5e7563','0x71660c4005ba85c37ccec55d0c4493e66fe775d3'])
    blocklist=blocklist
  )
  # create task group
  async with asyncio.TaskGroup() as task_group:
    # create and issue tasks
    [task_group.create_task(fetch_address(
                                        http_pool, 
                                        task_group, 
                                        results, 
                                        addr, 
                                        context
                                        )) for addr in addresses]
  # wait for all tasks to complete...
  logger.info(f"nexandria graph took {time.perf_counter() - start_time} secs ")
  
  start_time = time.perf_counter()
  addr_ids = list(results.get_address_set())
  edges = results.get_edge_list()

  pt_len = len(addresses)
  pretrust = [{'i': addr_ids.index(addr), 'v': 1/pt_len} for addr in addresses]

  localtrust = [{'i': addr_ids.index(edge['i']),
                 'j': addr_ids.index(edge['j']), 
                 'v': edge['v']} for edge in edges]
  max_id = len(addr_ids)

  logger.info("calling go_eigentrust")
  i_scores = await eigentrust_client.go_eigentrust(pretrust=pretrust, 
                                  max_pt_id=max_id,
                                  localtrust=localtrust,
                                  max_lt_id=max_id)
  
  addr_scores = [{'i': addr_ids[i_score['i']], 'v': i_score['v']} for i_score in i_scores]
  logger.info(f"eigentrust compute took {time.perf_counter() - start_time} secs ")

  # report all results
  return addr_scores
