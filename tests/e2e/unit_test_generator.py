
import pandas as pd

from tests.e2e.generate_unit_test import generate_one_unit_test




class UnitTestGenerator:
    def __init__(self, connection):
        self.connection = connection
    def add_round_group_to_df(self, inner_df):
        inner_df = inner_df.sort_values(by=['created_at'])
        inner_df['round'] = inner_df['scenario'] == 'overall' # 10 hours
        inner_df['round_group'] = inner_df['round'].cumsum()
        inner_df['round_group'] = inner_df['round_group'].shift(1).fillna(0).astype(int)
        return inner_df

    def process_one_round_group(self, inner_df):

        round_count = inner_df['round_group'].iloc[0] + 1
        test_prefix = 'test_' if inner_df['test'].iloc[0] else ''
        session_name = inner_df['session_name'].iloc[0]

        def merge_scenario(row):
            scenario = row.get('scenario')
            sub_scenario = row.get('sub_scenario')
            if sub_scenario is None:
                return scenario
            return f'{scenario}_{sub_scenario}'

        inner_df['scenario'] = inner_df.apply(merge_scenario, axis=1)

        def process_one_scenario(row):
            if row.get('scenario') == 'overall':
                return
            params = row.get('params')
            data_list = row.get('possible_message_templates')
            output = row.get('output')
            scenario = row.get('scenario')
            file_name = f'{test_prefix}round{round_count}_{scenario}'
            generate_one_unit_test(session_name, data_list, params, output, scenario, file_name)

        inner_df.apply(process_one_scenario, axis=1)



    def process_one_group(self, inner_df):
        inner_df = inner_df.sort_values(by=['round_group', 'created_at'])
        return inner_df.groupby(['round_group', 'test']).apply(self.process_one_round_group)


    def process(self):
        df = pd.read_sql("SELECT * FROM model_log", self.connection)
        df['session_name'] = df['log_id'].apply(lambda x: x.split('__')[-1])
        df['test'] = df['log_id'].apply(lambda x: x.startswith('test__'))
        df = df.groupby('log_id').apply(self.add_round_group_to_df).reset_index(drop=True)
        result = df.groupby(['session_name']).apply(self.process_one_group).reset_index()
