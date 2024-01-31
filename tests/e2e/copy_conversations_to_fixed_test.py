import json
import urllib

import re

import click
import sqlalchemy
from gluon_meson_sdk.models.config.log import get_config
import pandas as pd
from sqlalchemy import text


class ConversationCopyBoy:
    def __init__(self):
        log_db = get_config().log_db
        db_url = f"postgresql://{log_db.USER}:{urllib.parse.quote_plus(log_db.PASSWORD)}@{log_db.HOST}:{log_db.PORT}/{log_db.DATABASE}"
        self.connection = sqlalchemy.create_engine(url=db_url)
    def create_table_if_not_exists(self, engine):
        with engine.connect() as connection:
            connection.execute(text(
                """CREATE TABLE IF NOT EXISTS model_log_golden_test_set (
                    id serial primary key,
                    log_id varchar(255) not null,
                    origin_log_id varchar(255) not null,
                    scenario varchar(255),
                    model_name varchar(255),
                    input jsonb,
                    output text,
                    params jsonb,
                    error text,
                    possible_message_templates jsonb,
                    as_test_case boolean default false,
                    sub_scenario varchar(255),
                    created_at timestamp not null default now()
                )"""
            ))
            connection.commit()

    def copy_test_conversations_from_model_log(self):
        sql_query = f"""
select model_log.*, origin_log_id from model_log join (
    select distinct 'test__e2e_test___' || replace(log_id, ' ', '_') as log_id, origin_log_id from model_log_golden_test_set
) golden_test_set
on model_log.log_id = golden_test_set.log_id;
"""
        df = pd.read_sql(sql_query, self.connection)
        df = df.drop(columns=['id'])
        self.save_df_to_db(df)

    def save_df_to_db(self, df):
        df = self.dump_all_json_columns(df)
        df.to_sql('model_log_golden_test_set', self.connection, if_exists='append', index=False)

    def delete_test_cases(self):
        delete_sql = f"""
        delete from model_log where log_id in (
            select distinct 'test__e2e_test___' || replace(log_id, ' ', '_') as log_id from model_log_golden_test_set
        )
        """
        with self.connection.connect() as connection:
            connection.execute(text(delete_sql))
            connection.commit()

    def copy_conversations(self, excel_path):

        self.create_table_if_not_exists(self.connection)
        # use sqlalchemy engine to create table


        df = pd.read_excel(excel_path)
        def process_name(name):
            name = re.sub('[^\w_]', '_', name)
            name = re.sub('_+', '_', name).lower()
            return name
        def concat_use_cases_situation(row):
            return f"sit_{process_name(row.get('Use Cases'))}__{process_name(row.get('situation'))}"

        deduplicated_df = df.drop_duplicates(subset=['conversation_id'])

        readable_ids = deduplicated_df[['conversation_id', 'Use Cases', 'situation']].apply(concat_use_cases_situation, axis=1).to_list()
        # df[['conversation_id', 'Use Cases', 'situation']]
        readable_ids_string = ",".join([f"'{item}'" for item in readable_ids])
        conversation_ids_string = ",".join([f"'{item}'" for item in df['conversation_id'].drop_duplicates().to_list()])
        # exists_conversation_ids_query = f"SELECT * FROM model_log_golden_test_set where log_id in ({ids_string})"

        conversation_select_query = f"""
        SELECT model_log.* FROM model_log
        left join model_log_golden_test_set on model_log.log_id = model_log_golden_test_set.origin_log_id
        where model_log_golden_test_set.log_id is null and model_log.log_id in (
        {conversation_ids_string}
        )
        """
        conversation_to_be_inserted = pd.read_sql(conversation_select_query, self.connection)
        if len(conversation_to_be_inserted) == 0:
            click.echo("No conversation to be inserted")
            return
        conversation_to_be_inserted['origin_log_id'] = conversation_to_be_inserted['log_id']
        conversation_to_be_inserted_join_df = conversation_to_be_inserted.join(deduplicated_df.set_index('conversation_id'), on='log_id', how='left', lsuffix='', rsuffix='_right')
        conversation_to_be_inserted_join_df['log_id'] = conversation_to_be_inserted_join_df.apply(concat_use_cases_situation, axis=1)
        conversation_to_be_inserted_join_df = conversation_to_be_inserted_join_df[conversation_to_be_inserted.columns].drop(columns=['id'])
        self.save_df_to_db(conversation_to_be_inserted_join_df)
        # convert all dict to json
        # conversation_to_be_inserted_join_df = self.dump_all_json_columns(conversation_to_be_inserted_join_df)
        # conversation_to_be_inserted_join_df.to_sql('model_log_golden_test_set', self.connection, if_exists='append', index=False)

    def dump_all_json_columns(self, df):
        df['input'] = self.dump_json_column(df, 'input')
        df['params'] = self.dump_json_column(df, 'params')
        df['possible_message_templates'] = self.dump_json_column(df, 'possible_message_templates')
        return df


    def dump_json_column(self, conversation_to_be_inserted_join_df, column):
        return conversation_to_be_inserted_join_df[column].apply(lambda x: x if isinstance(x, str) else json.dumps(x))


if __name__ == "__main__":
    copy_boy = ConversationCopyBoy()
    copy_boy.copy_conversations("./TB Guru testing cases.xlsx")
    copy_boy.delete_test_cases()
    # copy_boy.copy_test_conversations_from_model_log()
