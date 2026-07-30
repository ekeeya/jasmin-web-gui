"""This is the jasmin-celery and jasmin-restapi configurations"""
#
#  Copyright (c) 2024
#  File created on 2024/7/17
#  By: Emmanuel Keeya
#  Email: ekeeya@thothcode.tech
#
#  This project is licensed under the GNU General Public License v3.0. You may
#  redistribute it and/or modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This project is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
#  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#  See the GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along with this project.
#  If not, see <http://www.gnu.org/licenses/>.
#
# NOTE: jasmin's api.py / tasks.py do `from .config import *`, so EVERY name jasmin
# reads must exist at module level here. The stock file hardcodes 127.0.0.1 for the
# http-api/broker/redis; we make those env-driven so the REST API and Celery worker
# can reach the other compose services. Keep all sections below in sync with stock.

import logging
import os

# ── RESTAPI ────────────────────────────────────────────────────────────────
# Where the REST API / batch worker pushes messages (Jasmin's legacy HTTP API).
old_api_uri = os.environ.get('JASMIN_OLD_API_URI', 'http://127.0.0.1:1401')
show_jasmin_version = True
auth_cache_seconds = 10
auth_cache_max_keys = 500

log_level = logging.getLevelName(os.environ.get('RESTAPI_LOG_LEVEL', 'DEBUG'))
log_file = '/var/log/jasmin/restapi.log'
log_rotate = 'W6'
log_format = '%(asctime)s %(levelname)-8s %(process)d %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'

# ── CELERY ─────────────────────────────────────────────────────────────────
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@127.0.0.1:5672//')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://:@127.0.0.1:6379/1')
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# ── BATCH THROUGHPUT ─────────────────────────────────────────────────────────
# Max throughput *per worker* when the batch executor pushes to the HTTP API.
# Set to 0 to disable throughput control. Tune via HTTP_THROUGHPUT_PER_WORKER.
http_throughput_per_worker = int(os.environ.get('HTTP_THROUGHPUT_PER_WORKER', '8'))
# When true, batch throughput adapts to Jasmin's response time (slower response
# → slower throughput, and vice-versa).
smart_qos = os.environ.get('SMART_QOS', 'true').lower() in ('1', 'true', 'yes')
