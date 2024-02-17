from fastapi import Request
import numpy as np

# dependency to make it explicit that routers are accessing hidden state
def get_non_eoa_list(request: Request) -> np.ndarray:
    return request.state.non_eoa_list