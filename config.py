"""This is the jasmin-celery and jasmin-restapi configurations"""

import logging
import os

# RESTAPI
old_api_uri = os.environ.get('JASMIN_OLD_API_URI', 'http://127.0.0.1:1401')
show_jasmin_version = True
auth_cache_seconds = 10
auth_cache_max_keys = 500

log_level = logging.getLevelName('INFO')
log_file = '/var/log/jasmin/restapi.log'
log_rotate = 'W6'
log_format = '%(asctime)s %(levelname)-8s %(process)d %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'