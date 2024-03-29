import os
from pathlib import Path

import pandas as pd

from tests.e2e.e2e_util import standardize_session_name
from utils.common import format_jinja_template


class E2eTestGenerator:
    def __init__(self, connection, log_table_name='model_log', generate_dir_name='generated', get_log_id_filter="",
                 thought_agent_host="localhost", prefix_for_session_name=""):
        self.connection = connection
        self.get_log_id_filter = get_log_id_filter
        self.log_table_name = log_table_name
        self.generate_dir_name = generate_dir_name
        self.thought_agent_host = thought_agent_host
        self.prefix_for_session_name = prefix_for_session_name

    def process_one_params_with_session_name(self, session_name):
        def process_one_params(params):
            print(params)
            if params is None:
                return {}
            params["conversation_id"] = f'test__e2e_test___{session_name.replace(self.prefix_for_session_name, "")}'
            return params
        return process_one_params

    def process_one_group(self, inner_df):
        session_name = standardize_session_name(inner_df.name, prefix=self.prefix_for_session_name)
        params_list = inner_df['params'].apply(self.process_one_params_with_session_name(session_name)).tolist()
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f"{cur_dir}/e2e_test_template.jinja2", "r") as rf:
            template = rf.read()
            Path(f"{cur_dir}/{self.generate_dir_name}/{session_name}/generated_e2e_test").mkdir(parents=True, exist_ok=True)
            with open(f"{cur_dir}/{self.generate_dir_name}/{session_name}/generated_e2e_test/{session_name}_e2e.py", "w") as wf:
                wf.write(format_jinja_template(template, params_list=params_list, thought_agent_host=self.thought_agent_host))
    def process(self, ignore_test_case_flag=True):
        if ignore_test_case_flag:
            query = f"SELECT * FROM {self.log_table_name} where scenario = 'overall' and not(log_id like 'test__e2e_test__%%')"
        else:
            query = f"SELECT * FROM {self.log_table_name} where as_test_case = true and scenario = 'overall' and not(log_id like 'test__e2e_test__%%')"
        df = pd.read_sql(query + self.get_log_id_filter, self.connection)
        df.sort_values(["created_at"]).groupby(['log_id']).apply(self.process_one_group)
