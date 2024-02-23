from fastapi import Request

def get_semaphore(request: Request):
    return request.state.sema