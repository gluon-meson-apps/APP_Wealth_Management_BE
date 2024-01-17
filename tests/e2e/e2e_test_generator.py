import os
from pathlib import Path

import pandas as pd

from tests.e2e.e2e_util import standardize_session_name
from utils.utils import format_jinja_template


class E2eTestGenerator:
    def __init__(self, connection, get_log_id_filter=None):
        self.connection = connection
        self.get_log_id_filter = get_log_id_filter

    def process_one_params(self, params):
        print(params)
        if params is None:
            return {}
        params["conversation_id"] = f'test__e2e_test__{params["conversation_id"]}'
        return params

    def process_one_group(self, inner_df):
        params_list = inner_df['params'].apply(self.process_one_params).tolist()
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f"{cur_dir}/e2e_test_template.jinja2", "r") as rf:
            template = rf.read()
            session_name = standardize_session_name(inner_df.name)
            Path(f"{cur_dir}/generated/{session_name}/generated_e2e_test").mkdir(parents=True, exist_ok=True)
            with open(f"{cur_dir}/generated/{session_name}/generated_e2e_test/{session_name}_e2e.py", "w") as wf:
                wf.write(format_jinja_template(template, params_list=params_list))
    def process(self, ignore_test_case_flag=True):
        if ignore_test_case_flag:
            query = "SELECT * FROM model_log where scenario = 'overall' and not(log_id like 'test__e2e_test__%%')"
        else:
            query = "SELECT * FROM model_log where as_test_case = true and scenario = 'overall' and not(log_id like 'test__e2e_test__%%')"
        df = pd.read_sql(query + self.get_log_id_filter, self.connection)
        df.sort_values(["created_at"]).groupby(['log_id']).apply(self.process_one_group)
