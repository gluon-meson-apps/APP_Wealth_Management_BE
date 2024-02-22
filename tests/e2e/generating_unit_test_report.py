import asyncio
import importlib
import json
import os
import re

import click
import pandas as pd

package = "generated_golden_test_set"
report_file_path = f"{os.path.dirname(os.path.abspath(__file__))}/testing_report.xlsx"
unit_test_file_name_pattern = r"^unit_test_\w+_unit.py"
MAX_NUMBER_OF_TESTS = 1024


@click.group()
@click.option("-p", "--path", default=report_file_path, show_default=True,
              help="Specify the path of the generated report file", required=False)
@click.pass_context
def cli(ctx, path):
    ctx.ensure_object(dict)
    ctx.obj["PATH"] = path


def form_the_dataframe(results: list[tuple]) -> pd.DataFrame:
    columns = ["use_case", "scenario", "prompt_template", "prompt", "params", "llm_result", "test_result"]
    return pd.DataFrame(data=results, columns=columns)


def get_module_name(file_path, package_name):
    module_name_start_index = file_path.find(package_name)
    module_name = file_path[module_name_start_index:-3].replace("/", ".")
    return module_name


def execute_test(file_path):
    try:
        module_name = get_module_name(file_path, package)
        module = importlib.import_module(module_name)
        if hasattr(module, "get_params") and callable(module.get_params):
            return module.get_params()
        else:
            raise Exception(f"The module {module_name} does not have a get_params function or it's not callable")
    except Exception as e:
        print(str(e))
        raise Exception(str(e))


def traverse_and_execute_test_cases(test_files_list):
    test_results = []

    for test_file in test_files_list:
        result = execute_test(test_file)
        if result:
            test_results.append(result)

    return test_results


def file_name_is_valid(file_name, pattern):
    return re.match(pattern, file_name) is not None


def get_unit_test_files_list(test_cases_root_folder, count=MAX_NUMBER_OF_TESTS):
    result = []
    for root, _, files in os.walk(test_cases_root_folder):
        for file in files:
            if file_name_is_valid(file, unit_test_file_name_pattern) and count:
                result.append(os.path.join(root, file))
                if count:
                    count -= 1
                else:
                    return result
    return result


@cli.command(name="record_tests",
             help="Run all the unit test and record the testing details")
@click.pass_context
@click.option("-c", "--count", type=click.INT, default=MAX_NUMBER_OF_TESTS,
              help="Number of test cases to be run. this will be helpful "
                   "if you only want to verify the process, running all test cases would cost much")
@click.argument("test_cases_root_folder",
                type=click.Path(),
                required=False,
                default=f"{os.path.dirname(os.path.abspath(__file__))}/generated_golden_test_set/")
def record_testing_details(ctx, count, test_cases_root_folder):
    files_list = get_unit_test_files_list(test_cases_root_folder, count=count)

    results = traverse_and_execute_test_cases(files_list)

    df = form_the_dataframe(results)

    with pd.ExcelWriter(ctx.obj["PATH"],
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
    new_columns = original_df[extract_column].apply(lambda x: json.loads(x)).apply(pd.Series)

    final_df = pd.concat([original_df, new_columns], axis=1)

    final_df.drop(extract_column, axis=1, inplace=True)

    return final_df


def get_testing_details_dataframe_from_excel(path):
    df = pd.read_excel(path, sheet_name="details")
    df = df.fillna("unknown")
    return df


@cli.command(name="report",
             help="Generate a report of the testing details")
@click.pass_context
def generate_report_from_testing_details(ctx):
    dataframe = get_testing_details_dataframe_from_excel(ctx.obj["PATH"])
    flattened_df = unnest_json_values(dataframe, "params")
    statistic_df = statistic_testing_result(flattened_df)
    report_df = statistic_df.groupby(["scenario", "use_case"]).sum().sort_index()

    with pd.ExcelWriter(report_file_path,
                        engine="openpyxl",
                        mode="a") as writer:
        report_df.to_excel(writer, sheet_name="summary", index=False)

    return report_df


if __name__ == "__main__":
    cli(obj={})
