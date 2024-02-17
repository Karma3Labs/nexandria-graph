import asyncio
from threading import Lock
import aiohttp
from loguru import logger
from ..config import settings
from dataclasses import dataclass
import time

class ThreadSafeCounter():
  def __init__(self):
    self._counter = 0
    self._lock = Lock()

  # increment and return the counter value
  def next_value(self):
    with self._lock:
      self._counter += 1
      return self._counter

class ThreadSafeDict():
  def __init__(self):
    self._dict = {}
    self._counter = 0
    self._lock = Lock()

  #add to dict if not present and return true/false
  def add_if_not_in(self, key, val) -> tuple[bool, int]:
    with self._lock:
      if not self._dict.get(key):
        self._dict[key] = val
        self._counter += 1
        return True, self._counter
      return False, self._counter

  def get(self):
    with self._lock:
      return self._dict

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
  results: ThreadSafeDict,
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
    key = "-".join((address, neighbor_addr))
    val = {"i":address, "j":neighbor_addr, "v": v}
    added, counter = results.add_if_not_in(key, val)
    if added and counter < context.max_num_results:
      task_group.create_task(fetch_address(http_pool, task_group, results, neighbor_addr, context))
  return 
 
async def fetch_graph(
    http_pool: aiohttp.ClientSession,
    addresses: list[str],
    k: int,
    limit: int,
    chain: str,
    blocklist: set
)->list[dict]:
  results = ThreadSafeDict()
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
  # report all results
  return list(results.get().values())
