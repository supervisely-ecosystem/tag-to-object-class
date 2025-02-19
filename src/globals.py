import ast
import os
import sys

import supervisely as sly

from fastapi import FastAPI
from supervisely.app.fastapi import create
from supervisely.app.content import get_data_dir
from distutils.util import strtobool

app_root_directory = os.getcwd()
sly.logger.info(f'App root directory: {app_root_directory!r}')
sys.path.append(app_root_directory)

data_directory = get_data_dir()
temp_data_directory = os.getenv('DEBUG_TEMPORARY_APP_DIR', '/tmp/sly-app')  # to be removed after task execution
sly.logger.info(f'App data directory: {data_directory!r}  Temporary data directory: {temp_data_directory!r}')

app = FastAPI()
sly_app = create()
app.mount('/sly', sly_app)
api = sly.Api.from_env()

task_id = int(os.environ['TASK_ID'])
team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])
project_id = int(os.environ['modal.state.slyProjectId'])

selected_tags = os.environ['modal.state.selectedTags.tags']
selected_tags = ast.literal_eval(selected_tags)
if not (isinstance(selected_tags, list) and all(isinstance(item, str) for item in selected_tags)):
    raise ValueError('Unable to parse env modal.state.selectedTags.tags')

handle_multiple_tags = bool(strtobool(os.environ['modal.state.handleMulti']))
handle_option = os.environ['modal.state.handleOption'] if handle_multiple_tags else None

res_project_name = os.getenv('modal.state.resultProjectName', None)
anns_in_memory_limit = os.getenv('ANNS_IN_MEMORY_LIMIT', 1000)
