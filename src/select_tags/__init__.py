from supervisely.app import StateJson, DataJson

from src.select_tags.card_routes import *
from src.select_tags.card_functions import *
from src.select_tags.card_widgets import *


StateJson()['exampleField'] = "My Example Value in STATE"
DataJson()['exampleField'] = "My Example Value in DATA"
