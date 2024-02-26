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
    self._counter = 0
    self._lock = Lock()

  def add_edge(self, edge:dict) -> tuple[bool, int]:
    with self._lock:
      self._edges.append(edge)

  def try_add_and_traverse(self, key:str, limit:int) -> tuple[bool, bool]:
    with self._lock:
      # print(f"{key},{limit} - {self._counter},{self._addr_set}")
      if self._counter < limit and not key in self._addr_set:
        self._addr_set.add(key)
        self._counter += 1
        return True, True
      else:
        return key in self._addr_set, False

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
  sema: asyncio.Semaphore,
  http_pool: aiohttp.ClientSession,
  task_group: asyncio.TaskGroup, 
  results: ThreadSafeEdgeList,
  address: str,
  context: TaskContext,
  current_depth: int,
):
  try:
    url = f"{settings.NEXANDRIA_URL}/{context.chain}/v1/address/{address}/neighbors"
    logger.info(f"fetch_address: {url}")
    try:
      async with sema:
        start_time = time.perf_counter()
        async with http_pool.get(url, 
                                params=context.params, 
                                raise_for_status=True) as http_resp:
          resp = await http_resp.json()
        # TODO replace with a timer context manager
        elapsed_time = time.perf_counter() - start_time
        logger.info(f"Summary {url} took {elapsed_time} secs")
        if resp.get('error') and \
          resp.get('error').get('details').startswith('large accounts') \
        :
          logger.info(f"Nexandria error 422: large account: retry {url}")
          start_time = time.perf_counter()
          async with http_pool.get(url, 
                        params={'details': 'partial', 'block_cp': 'native'},
                        raise_for_status=True) as http_resp:
            resp = await http_resp.json()
          elapsed_time = time.perf_counter() - start_time
          logger.info(f"Partial {url} took {elapsed_time} secs")
    except asyncio.TimeoutError as exc:
      logger.error(f"Nexandria timed out for {url}?{context.params}")
      return
    except aiohttp.ClientError as exc:
      logger.error(f"HTTP Exception for {url}?{context.params} - {exc}")
      return
    except Exception as exc:
      logger.error(f"Unknown error: {exc}")
      return
    if resp.get('error'):
      # Nexandria always returns HTTP 200 with error in the response body
      logger.error(f"Nexandria Internal error: {url}?{context.params} {resp.get('error')}")
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

      is_neighbor, is_traverse = results.try_add_and_traverse(neighbor_addr, context.max_num_results)
      logger.debug(f"{neighbor_addr}" 
                  f" is_neighbor:{is_neighbor}" 
                  f" is_traverse:{is_traverse}"
                  f" current_depth:{current_depth}")
      if is_neighbor:
        v = settings.DEFAULT_TRANSFER_VALUE \
              if neighbor.get("fiat_to_neighbor") is None \
              else float(neighbor.get("fiat_to_neighbor").replace(',',''))
        val = {"i":address, "j":neighbor_addr, "v": v}
        results.add_edge(val)
        if is_traverse and current_depth < context.max_depth:
          task_group.create_task(
            fetch_address(
              sema, http_pool, task_group, results, neighbor_addr, context, current_depth+1))
  except Exception as exc:
    logger.error(f"Unknown error: {exc}")
  return 
 
async def get_neighbors_scores(
    sema: asyncio.Semaphore,
    http_pool: aiohttp.ClientSession,
    addresses: list[str],
    k: int,
    limit: int,
    chain: str,
    blocklist: set,
) -> list[dict]:
  start_time = time.perf_counter()
  match chain:
    case 'ethereum' | 'eth':
      chain = 'eth' # nexandria only recognizes eth as chain name
      from_ts = 1672531200 # since 1/1/2023 00:00:00 UTC
    case 'base': 
      from_ts = 1686790800 # since 6/15/2023 00:00:00 UTC

  results = ThreadSafeEdgeList(addresses)
  context = TaskContext(
    max_depth=k,
    max_num_results=limit,
    chain=chain,
    params={ 'details': 'summary', 
            'from_ts': from_ts, 
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
                                        sema,
                                        http_pool, 
                                        task_group, 
                                        results, 
                                        addr, 
                                        context,
                                        current_depth=1
                                        )) for addr in addresses]
  # wait for all tasks to complete...
  logger.info(f"nexandria graph took {time.perf_counter() - start_time} secs ")
  
  start_time = time.perf_counter()
  addr_ids = list(results.get_address_set())
  edges = results.get_edge_list()

  if len(edges) <= 0:
    logger.error(f"No edges found for {addresses}")
    return []
  
  pt_len = len(addresses)
  logger.info(f"generating pretrust with {addresses}")
  pretrust = [{'i': addr_ids.index(addr), 'v': 1/pt_len} for addr in addresses]

  logger.info(f"generating localtrust with {len(addr_ids)} addresses and  {len(edges)} edges")
  localtrust = [{'i': addr_ids.index(edge['i']),
                 'j': addr_ids.index(edge['j']), 
                 'v': edge['v']} for edge in edges]
  max_id = len(addr_ids)

  logger.info("calling go_eigentrust")
  i_scores = await eigentrust_client \
                    .go_eigentrust(pretrust=pretrust, 
                                  max_pt_id=max_id,
                                  localtrust=localtrust,
                                  max_lt_id=max_id)
  
  addr_scores = [{'address': addr_ids[i_score['i']], 'score': i_score['v']} for i_score in i_scores]
  logger.info(f"eigentrust compute took {time.perf_counter() - start_time} secs ")

  # report all results
  return addr_scores
