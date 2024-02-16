import asyncio
from threading import Lock

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
  group: asyncio.TaskGroup, 
  counter: ThreadSafeCounter, 
  results: ThreadSafeDict,
  address: str
):
  print(f"address: {address}")
  # sleep to simulate fetching
  await asyncio.sleep(1)
  for i in range(1,5):
    v = counter.next_value()
    if v < 10:
      print(f"creating subtask {v} for address: {address}")
      group.create_task(fetch_address(group, counter, results, address))
    results.add_if_not_in(address, address)
  return 
 
async def fetch_graph(addresses: list[str])->list[dict]:
  results = ThreadSafeDict()
  # create task group
  async with asyncio.TaskGroup() as group:
    counter = ThreadSafeCounter()
    # create and issue tasks
    [group.create_task(fetch_address(group, counter, results, addr)) for addr in addresses]
  # wait for all tasks to complete...
  # report all results
  return results.get()
