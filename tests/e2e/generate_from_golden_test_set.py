import urllib

import sqlalchemy
from gluon_meson_sdk.models.config.log import get_config

from tests.e2e.e2e_test_generator import E2eTestGenerator
from tests.e2e.e2e_util import get_log_id_filter
from tests.e2e.logs_generator import LogsGenerator
from tests.e2e.unit_test_generator import UnitTestGenerator

def generate():
    log_db = get_config().log_db
    db_url = f"postgresql://{log_db.USER}:{urllib.parse.quote_plus(log_db.PASSWORD)}@{log_db.HOST}:{log_db.PORT}/{log_db.DATABASE}"
    connection = sqlalchemy.create_engine(url=db_url)


    E2eTestGenerator(connection, log_table_name='model_log_golden_test_set', generate_dir_name='generated_golden_test_set', thought_agent_host="bj-3090.private.gluon-meson.tech").process()
    LogsGenerator(connection, log_table_name='model_log_golden_test_set', generate_dir_name='generated_golden_test_set').process()
    UnitTestGenerator(connection, log_table_name='model_log_golden_test_set', generate_dir_name='generated_golden_test_set').process()


if __name__ == "__main__":
    generate()
