import importlib
import json
import os
import re

import pandas as pd

package = "generated_golden_test_set"
report_file_name = f"testing_report.xlsx"
unit_test_file_name_pattern = r"^unit_test_\w+_unit.py"


def form_the_dataframe(results: list[tuple]) -> pd.DataFrame:
    columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result"]
    return pd.DataFrame(data=results, columns=columns)


def get_module_name(file_path, package_name):
    module_name_start_index = file_path.find(package_name)
    module_name = file_path[module_name_start_index:-3].replace("/", ".")
    return module_name


def execute_test(file_path):
    try:
        module_name = get_module_name(file_path, package)
        module = importlib.import_module(module_name)
        if hasattr(module, "main") and callable(module.main):
            return module.main()
        else:
            raise Exception(f"The module {module_name} does not have a main function or it's not callable")
    except Exception as e:
        print(str(e))
        raise Exception(str(e))


def traverse_test_cases(test_files_list):
    test_results = []

    for test_file in test_files_list:
        result = execute_test(test_file)
        if result:
            test_results.append(result)

    return test_results


def file_name_is_valid(file_name, pattern):
    return re.match(pattern, file_name) is not None


def get_unit_test_files_list(test_cases_root_folder):
    return [
        os.path.join(root, file)
        for root, _, files in os.walk(test_cases_root_folder)
        for file in files if file_name_is_valid(file, unit_test_file_name_pattern)
    ]


def record_testing_details():
    files_list = get_unit_test_files_list(f"{os.path.dirname(os.path.abspath(__file__))}/{package}")
    files_list = files_list[:2]

    results = traverse_test_cases(files_list)

    df = form_the_dataframe(results)

    with pd.ExcelWriter(f"{os.path.dirname(os.path.abspath(__file__))}/{report_file_name}",
                        engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="details", index=False)
    return df


def statistic_testing_result(dataframe):
    dataframe["test_result"] = dataframe["test_result"].apply(lambda x: x if x in ["pass", "fail"] else "unknown")

    grouped_df = dataframe.groupby(["scenario", "use_case", "test_result"]).size().reset_index(name="count")
    pivoted_df = grouped_df.pivot_table(
        index=["scenario", "use_case"],
        columns="test_result",
        values="count",
        fill_value=0,
    ).reset_index()

    if "pass" not in pivoted_df:
        pivoted_df["pass"] = 0
    if "fail" not in pivoted_df:
        pivoted_df["fail"] = 0
    if "unknown" not in pivoted_df:
        pivoted_df["unknown"] = 0

    total_tests = pivoted_df["pass"] + pivoted_df["fail"] + pivoted_df["unknown"]
    pivoted_df["pass percentage"] = pivoted_df["pass"] / total_tests * 100.0
    pivoted_df["fail percentage"] = pivoted_df["fail"] / total_tests * 100.0
    merged_df = pd.merge(dataframe, pivoted_df, on=["scenario", "use_case"], how="left")
    return merged_df


def extract_keys(json_str):
    json_dict = json.loads(json_str.replace("'", "\""))
    return json_dict


def unnest_json_values(original_df, extract_column):
    new_columns = original_df[extract_column].apply(pd.Series)

    final_df = pd.concat([original_df, new_columns], axis=1)

    final_df.drop(extract_column, axis=1, inplace=True)

    print(final_df.columns)
    return final_df


def generate_report_from_testing_details(dataframe):
    flattened_df = unnest_json_values(dataframe, "params")
    report_df = statistic_testing_result(flattened_df)

    with pd.ExcelWriter(f"{os.path.dirname(os.path.abspath(__file__))}/{report_file_name}",
                        engine="openpyxl",
                        mode="a") as writer:
        report_df.to_excel(writer, sheet_name="summary", index=False)

    return report_df


def main():
    df = record_testing_details()
    generate_report_from_testing_details(df)


if __name__ == "__main__":
    main()
