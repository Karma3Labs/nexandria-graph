import sys
import time
import logging as log

from fastapi import FastAPI, Depends, Request, Response
from contextlib import asynccontextmanager
import httpx
import uvicorn
import pandas as pd

from .dependencies import logging
from .config import settings
from .routers.graph_router import router as graph_router

from loguru import logger

logger.remove()
level_per_module = {
    "": "INFO",
    "app": settings.LOG_LEVEL,
    "silentlib": False
}
logger.add(sys.stdout, 
           colorize=True, 
           format="<green>{time:HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>",
           filter=level_per_module,
           level=0)
# logger.add(sys.stdout, 
#            colorize=True, 
#            format="<green>{time:HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>",
#            level=settings.LOG_LEVEL)

log.basicConfig(handlers=[logging.InterceptHandler()], level=0, force=True)
log.getLogger("uvicorn").handlers = [logging.InterceptHandler()]
log.getLogger("uvicorn.access").handlers = [logging.InterceptHandler()]


app_state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Execute when API is started"""
    logger.warning(f"{settings}")
    base_url = settings.NEXANDRIA_URL
    headers = { 'API-Key': settings.NEXANDRIA_API_KEY.get_secret_value() }
    timeout = httpx.Timeout(settings.NEXANDRIA_TIMEOUT_SECS)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=5)
    logger.warning(f"creating connection pool")
    app_state['conn_pool'] = httpx.AsyncClient(
                                                headers=headers,
                                                base_url=base_url,
                                                limits=limits, 
                                                timeout=timeout)
    logger.warning(f"loading blocklist")
    app_state['non_eoa_list'] = pd.read_csv(settings.NON_EOA_LIST, sep=',', header=None).values
    yield
    """Execute when API is shutdown"""
    logger.info(f"closing conn_pool: {app_state['conn_pool']}")
    await app_state['conn_pool'].aclose()

app = FastAPI(lifespan=lifespan, dependencies=[Depends(logging.get_logger)])
app.include_router(graph_router, prefix='/graph')

@app.middleware("http")
async def session_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    logger.info(f"{request.method} {request.url}")
    response = Response("Internal server error", status_code=500)
    request.state.conn_pool = app_state['conn_pool']
    request.state.non_eoa_list = app_state['non_eoa_list']
    response = await call_next(request)
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"{request.url} took {elapsed_time} secs")
    return response

@app.get("/_health", status_code=200)
def get_health():
    logger.info("health check")
    return {'status': 'ok'}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)