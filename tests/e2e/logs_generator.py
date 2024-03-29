import pandas as pd
from tests.e2e.e2e_util import standardize_session_name
from tests.e2e.generate_log import generate_one_log


class LogsGenerator:
    def __init__(self, connection, log_table_name='model_log', generate_dir_name='generated', get_log_id_filter="", prefix_for_session_name=""):
        self.connection = connection
        self.get_log_id_filter = get_log_id_filter
        self.log_table_name = log_table_name
        self.generate_dir_name = generate_dir_name
        self.prefix_for_session_name = prefix_for_session_name

    def add_round_group_to_df(self, inner_df):
        inner_df = inner_df.sort_values(by=['created_at'])
        inner_df['round'] = inner_df['scenario'] == 'overall'
        inner_df['round_group'] = inner_df['round'].cumsum()
        inner_df['round_group'] = inner_df['round_group'].shift(1).fillna(0).astype(int)
        return inner_df

    def process_one_round_group(self, inner_df):
        over_all = inner_df.iloc[-1].to_dict()
        round_count = inner_df['round_group'].iloc[0] + 1
        test_prefix = 'unit_test_' if inner_df['test'].iloc[0] else ''
        retry_overall = f'{test_prefix}round{round_count}_retry_overall_response'
        session_name = inner_df['session_name'].iloc[0]
        session_name = standardize_session_name(session_name, self.prefix_for_session_name)

        def merge_scenario(row):
            scenario = row.get('scenario')
            sub_scenario = row.get('sub_scenario')
            if sub_scenario is None:
                return scenario
            return f'{scenario}_{sub_scenario}'

        inner_df['scenario'] = inner_df.apply(merge_scenario, axis=1)

        def process_one_scenario(row):
            scenario = row.get('scenario')
            retry = f'{test_prefix}round{round_count}_retry_{scenario}'
            file_name = f"{test_prefix}round{round_count}_{scenario}"
            import_ = f"from tests.e2e.{self.generate_dir_name}.{session_name}.generated_unit_test import {file_name}_unit as {retry}"
            return (scenario, row.get('output'), retry, import_)

        inner_df['data'] = inner_df.apply(process_one_scenario, axis=1)
        other_scenarios = inner_df[~inner_df['scenario'].isin(['overall'])]. \
            sort_values(by=['created_at'])['data'].tolist()
        other_scenarios_data = {x[0]: x[1:-1] for x in other_scenarios}
        other_scenarios_imports = [x[-1] for x in other_scenarios if x[-1].find("overall_unified_search") == -1]

        round = {
            "user": over_all['params']['question'],
            "response": (over_all['output'], retry_overall),
            "round": round_count,
            'round_name': test_prefix + f"round{round_count}",
            **other_scenarios_data,
            "imports": [
                f"from tests.e2e.{self.generate_dir_name}.{session_name}.generated_e2e_test import {session_name}_e2e as {retry_overall}",
                *other_scenarios_imports
            ],
        }
        return round

    def process_one_group(self, inner_df):
        inner_df = inner_df.sort_values(by=['round_group', 'created_at'])
        return inner_df.groupby(['round_group', 'test']).apply(self.process_one_round_group).to_list()

    def process(self):
        df = pd.read_sql(f"SELECT * FROM {self.log_table_name} where 1=1" + self.get_log_id_filter, self.connection)
        df['session_name'] = df['log_id'].apply(lambda x: x.split('___')[-1])
        df['test'] = df['log_id'].apply(lambda x: x.startswith('test__'))
        df = df.groupby('log_id').apply(self.add_round_group_to_df).reset_index(drop=True)
        result = df.groupby(['session_name']).apply(self.process_one_group).reset_index()

        def log_one_session(row):
            session_name = row.get('session_name')
            data = row.get(0)
            generate_one_log(session_name, data, self.generate_dir_name, self.prefix_for_session_name)

        result.apply(log_one_session, axis=1)
