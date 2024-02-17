from fastapi import Request

# dependency to make it explicit that routers are accessing hidden state
def get_non_eoa_list(request: Request) -> set:
    return request.state.non_eoa_list