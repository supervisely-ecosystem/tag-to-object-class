from fastapi import Depends

import supervisely as sly

from supervisely.app import StateJson, DataJson
from supervisely.app.widgets import ElementButton
from supervisely.app.fastapi import run_sync

import src.select_tags.card_widgets as card_widgets
import src.select_tags.card_functions as card_functions

import src.globals as g


@card_widgets.testr_button.add_route(app=g.app, route=ElementButton.Routes.BUTTON_CLICKED)
def test_my_btn(state: StateJson = Depends(StateJson.from_request)):
    sly.logger.info(f"{state.get('testInputText')=}")
    sly.logger.info('Post TEST BTN ')
    state["testInputText"] = 'not so fast'
    run_sync(DataJson().synchronize_changes())
    run_sync(state.synchronize_changes())


def my_old_route(state: StateJson = Depends(StateJson.from_request)):
    sly.logger.info(f"CHANGE {state=}")


g.app.add_api_route('/dummy_old_route/', my_old_route, methods=["POST"])
