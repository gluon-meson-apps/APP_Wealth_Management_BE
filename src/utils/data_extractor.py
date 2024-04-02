import json

import pandas as pd


def extract_data_set(file_path, columns):
    df = pd.read_excel(file_path)

    selected_columns = columns
    column_data_types = {}

    for column_index in selected_columns:
        abbreviation = df.columns[column_index].strip()

        description = df.iloc[0][column_index]
        data_types = set(df.iloc[1:, column_index].dropna().astype(str))

        column_data_types[abbreviation] = {'description': description, 'types': list(data_types)}
    json_string = json.dumps(column_data_types, ensure_ascii=False, indent=2)

    return json_string


def add_line_to_column(file_path, column_name):
    df = pd.read_excel(file_path)

    df[column_name] = df[column_name].astype(str) + "线"

    df.to_excel(file_path, index=False)


if __name__ == '__main__':
    file_path = '../resources/repository/files/TAG_BASIC_INFO.xlsx'
    add_line_to_column(file_path, 'LINE_DESC')
