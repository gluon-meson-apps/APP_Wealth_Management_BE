import urllib

import sqlalchemy
from gluon_meson_sdk.models.config.log import get_config

from tests.e2e.e2e_test_generator import E2eTestGenerator
from tests.e2e.e2e_util import get_log_id_filter
from tests.e2e.logs_generator import LogsGenerator
from tests.e2e.unit_test_generator import UnitTestGenerator

log_db = get_config().log_db
db_url = f"postgresql://{log_db.USER}:{urllib.parse.quote_plus(log_db.PASSWORD)}@{log_db.HOST}:{log_db.PORT}/{log_db.DATABASE}"
connection = sqlalchemy.create_engine(url=db_url)

log_id_filter = get_log_id_filter(['br_extension_multiple_references'])

E2eTestGenerator(connection, log_id_filter).process()
LogsGenerator(connection, log_id_filter).process()
UnitTestGenerator(connection, log_id_filter).process()
