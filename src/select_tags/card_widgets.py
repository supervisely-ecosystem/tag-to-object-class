from supervisely.app.widgets import NotificationBox
from supervisely.app.widgets import ElementButton


simple_notification = NotificationBox(title='Widget Example',
                                      description='i am simplest widget example')


testr_button = ElementButton('Test Route',
                             button_type='success',
                             button_size='large')
