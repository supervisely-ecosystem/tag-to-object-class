import ast
import os
import sys

import supervisely as sly

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from supervisely.app.fastapi import create, Jinja2Templates
from supervisely.app.content import get_data_dir


app_root_directory = os.getcwd()
sly.logger.info(f'App root directory: {app_root_directory!r}')
sys.path.append(app_root_directory)

data_directory = get_data_dir()
temp_data_directory = os.getenv('DEBUG_TEMPORARY_APP_DIR', '/tmp/sly-app')  # to be removed after task execution
sly.logger.info(f'App data directory: {data_directory!r}  Temporary data directory: {temp_data_directory!r}')

app = FastAPI()
sly_app = create()
app.mount('/sly', sly_app)
app.mount("/static", StaticFiles(directory=os.path.join(app_root_directory, 'static')), name="static")

templates_env = Jinja2Templates(directory=os.path.join(app_root_directory, 'templates'))

api = sly.Api.from_env()

task_id = int(os.environ['TASK_ID'])
team_id = int(os.environ['context.teamId'])
workspace_id = int(os.environ['context.workspaceId'])
project_id = int(os.environ['modal.state.slyProjectId'])

"""
selected_tags = os.environ['modal.state.selectedTags.tags']
selected_tags = ast.literal_eval(selected_tags)
if not (isinstance(selected_tags, list) and all(isinstance(item, str) for item in selected_tags)):
    raise ValueError('Unable to parse env modal.state.selectedTags.tags')

res_project_name = os.getenv('modal.state.resultProjectName', None)
"""
anns_in_memory_limit = os.getenv('ANNS_IN_MEMORY_LIMIT', 1000)

sly.logger.info(
    'Script arguments',
    extra={
        'context.teamId': team_id,
        'context.workspaceId': workspace_id,
        'modal.state.slyProjectId': project_id,
    },
)
