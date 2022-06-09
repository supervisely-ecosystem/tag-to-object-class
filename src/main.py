from fastapi import Request, Depends

import src.debug_load_envs  # before import sly
import supervisely as sly
from supervisely.app import StateJson

import src.globals as g
import src.select_tags


@g.app.get("/")
def read_index(request: Request):
    sly.logger.info('GET ROOOOOOT')
    return g.templates_env.TemplateResponse('index.html', {'request': request})


# @g.app.post("/apply_changes/")
# async def apply_changes(state: StateJson = Depends(StateJson.from_request)):
#     await state.synchronize_changes()
