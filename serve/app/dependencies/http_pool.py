from fastapi import Request

# dependency to make it explicit that routers are accessing hidden state
def get_async_client(request: Request):
    return request.state.conn_pool