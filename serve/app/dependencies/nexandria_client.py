import asyncio
from threading import Lock
import httpx
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
  contract_addrs: list # TODO change to numpy Series

# coroutine task
async def fetch_address(
  httpxclient: httpx.AsyncClient,
  task_group: asyncio.TaskGroup, 
  results: ThreadSafeDict,
  address: str,
  context: TaskContext
):
  url = f"{context.chain}/v1/address/{address}/neighbors"
  logger.info(f"fetch_address: {url}")
  try:
    start_time = time.perf_counter()
    r = await httpxclient.get(url, params=context.params)
    # TODO replace with a timer context manager
    elapsed_time = time.perf_counter() - start_time
    logger.debug(f"{url} took {elapsed_time} secs")
    r.raise_for_status() # raise exception for any non-200 status
  except httpx.HTTPError as exc:
    logger.error(f"HTTP Exception for {exc.request.url} - {exc}")
    return
  neighbors = r.json()['neighbors']
  for neighbor in neighbors:
    neighbor_addr = neighbor['neighbor_info']['address']
    # skip if this is an eoa to contract transfer
    if neighbor_addr in context.contract_addrs:
      logger.debug(f"skipping fetch for contract address {neighbor_addr}")
      continue
    # Nexandria will return transfers_to_neighbor = 0 if:
    # a) transfer is outgoing (or)
    # b) transfer is very old and happened before from_ts
    if neighbor["transfers_to_neighbor"] == 0:
      logger.debug(f"skipping fetch for 0 transfer to address {neighbor_addr}")
      continue
    v = 0.0001 if neighbor.get("fiat_to_neighbor") is None \
              else float(neighbor.get("fiat_to_neighbor").replace(',',''))
    key = "-".join((address, neighbor_addr))
    val = {"i":address, "j":neighbor_addr, "v": v}
    added, counter = results.add_if_not_in(key, val)
    if added and counter < context.max_num_results:
      task_group.create_task(fetch_address(httpxclient, task_group, results, neighbor_addr, context))
  return 
 
async def fetch_graph(
    httpxclient: httpx.AsyncClient,
    addresses: list[str],
    k,
    limit,
    chain
)->list[dict]:
  results = ThreadSafeDict()
  context = TaskContext(
    max_depth=k,
    max_num_results=limit,
    chain=chain,
    params={ 'details': 'summary', 
            'from_ts': 1672560000, # TODO avoid hardcoding; calculate last 12 months
            'to_ts': 1704096000,  # TODO avoid hardcoding
            'block_cp': 'native' # to specify the Zero address, typically used for fee/burn/mint transactions
            },
    contract_addrs=('0x39aa39c021dfbae8fac545936693ac917d5e7563','0x71660c4005ba85c37ccec55d0c4493e66fe775d3')
  )
  # create task group
  async with asyncio.TaskGroup() as task_group:
    # create and issue tasks
    [task_group.create_task(fetch_address(
                                        httpxclient, 
                                        task_group, 
                                        results, 
                                        addr, 
                                        context
                                        )) for addr in addresses]
  # wait for all tasks to complete...
  # report all results
  return list(results.get().values())
