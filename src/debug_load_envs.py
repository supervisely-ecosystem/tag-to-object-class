import os

from dotenv import load_dotenv


app_dir = os.getcwd()
debug_env_path = os.path.join(app_dir, 'debug.env')
secret_debug_env_path = os.path.join(app_dir, 'secret_debug.env')

load_dotenv(debug_env_path)
load_dotenv(secret_debug_env_path, override=True)
