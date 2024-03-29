import urllib

import sqlalchemy
from gluon_meson_sdk.models.config.log import get_config

from tests.e2e.e2e_test_generator import E2eTestGenerator
from tests.e2e.e2e_util import get_log_id_filter
from tests.e2e.logs_generator import LogsGenerator
from tests.e2e.unit_test_generator import UnitTestGenerator

def generate_fix_test(log_ids: list[str]):
    log_db = get_config().log_db
    db_url = f"postgresql://{log_db.USER}:{urllib.parse.quote_plus(log_db.PASSWORD)}@{log_db.HOST}:{log_db.PORT}/{log_db.DATABASE}"
    connection = sqlalchemy.create_engine(url=db_url)

    log_id_filter = get_log_id_filter(log_ids)

    prefix_for_session_name = "__l__"
    E2eTestGenerator(connection, get_log_id_filter=log_id_filter, prefix_for_session_name=prefix_for_session_name).process()
    LogsGenerator(connection, get_log_id_filter=log_id_filter, prefix_for_session_name=prefix_for_session_name).process()
    UnitTestGenerator(connection, get_log_id_filter=log_id_filter, prefix_for_session_name=prefix_for_session_name).process()


if __name__ == "__main__":
    generate_fix_test(['rma_vietnam'])
