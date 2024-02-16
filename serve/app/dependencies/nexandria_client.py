import asyncio
from threading import Lock
import httpx
from loguru import logger
from ..config import settings

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
    self._lock = Lock()

  #add to dict if not present and return true/false
  def add_if_not_in(self, key, val) -> bool:
    with self._lock:
      if not self._dict.get(key):
        self._dict[key] = val
        return True
      return False

  def get(self):
    with self._lock:
      return self._dict
        
# coroutine task
async def fetch_address(
  httpxclient: httpx.AsyncClient,
  group: asyncio.TaskGroup, 
  counter: ThreadSafeCounter, 
  results: ThreadSafeDict,
  address: str
):
  url = f"eth/v1/address/{address}/neighbors"
  logger.info(f"fetch_address: {url}")
  params = { 'from_ts': 1672560000, 'to_ts': 1704096000, 'block_cp': 'native' }
  r = await httpxclient.get(url, params=params)
  # for i in range(1,5):
  #   await asyncio.sleep(1)
  #   v = counter.next_value()
  #   if v < 5:
  #     logger.debug(f"creating subtask {v} for address: {address}")
  #     group.create_task(fetch_address(httpxclient, group, counter, results, address))
  results.add_if_not_in(address, r.json())
  return 
 
async def fetch_graph(httpxclient: httpx.AsyncClient, addresses: list[str])->list[dict]:
  results = ThreadSafeDict()
  # create task group
  async with asyncio.TaskGroup() as group:
    counter = ThreadSafeCounter()
    # create and issue tasks
    [group.create_task(fetch_address(httpxclient, group, counter, results, addr)) for addr in addresses]
  # wait for all tasks to complete...
  # report all results
  return results.get()
