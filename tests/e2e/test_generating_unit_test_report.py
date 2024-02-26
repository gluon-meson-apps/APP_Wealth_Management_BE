import asyncio
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from pandas._testing import assert_frame_equal

import tests.e2e.generating_unit_test_report as report

"""
- [x] Make the program as a command line script
    - [x] Use the package `click` for bootstrapping the commands
    - [x] [Option] path - Specify the path of the generated report file, default: $project_root/tests/e2e/testing_report.xlsx
    - [x] [Command] record_tests
        - [x] [Option] count - Number of test cases to be run, this will be helpful if you \
                       only want to verify the process, running all test cases would cost much
        - [x] [Argument] TEST_CASES_ROOT_FOLDER - The folder of the test cases, defaults to $project_root/tests
    - [x] [Command] report
- [ ] Traverse the test case directory and execute all unit tests
    - [x] Traverse the test case directory
        - [x] Filter out all unit tests
        - [x] Get the module name from the test case directory
    - [x] Execute the module
        - [x] Receive the result of the main() function
        - [x] Put the results to a Pandas DataFrame
        - [ ] [TODO] Find out how to judge whether the test passes or fails
        - [ ] **[ATTENTION] The main() function of the tests are async, when being executed, \
              it will raise an exception saying \
              "TypeError: object ChatModelResponse can't be used in 'await' expression"**
    - [x] Write the DataFrame to a specific sheet of an excel file
- [ ] Generate a report from the above testing details
    - [x] Get the dataframe firstly
    - [x] Group the DataFrame by the scenario
        - [x] Count the number of passed and failed tests
        - [x] Add columns `Positive results` and `Negative results`, fill in the counts
        - [x] Calculate the percentage of passed and failed tests
    - [x] Split the items in the `params` column to new columns
        - [ ] [TODO] Decide how to find the model type
    - [x] Write the new DataFrame to another sheet of the same excel file
    - [ ] [TODO] Create a map for use case
    - [x] Group the report by scenario and use case
"""


class TestTraverseTestCaseDirectoryAndExecuteTests:
    def test_given_a_directory_path_should_return_filtered_file_names(self, tmp_path):
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()
        sub_dir1 = test_dir / "subfolder1"
        sub_dir1.mkdir()
        sub_dir2 = test_dir / "subfolder2"
        sub_dir2.mkdir()
        file1 = sub_dir1 / "unit_test_something_unit.py"
        file1.write_text("File 1 content")
        file2 = sub_dir2 / "file2.txt"
        file2.write_text("File 2 content")

        result = report.get_unit_test_files_list(test_dir)

        expected_files = [f"{test_dir}/subfolder1/unit_test_something_unit.py"]
        assert sorted(result) == sorted(expected_files)

    def test_given_a_directory_path_should_return_empty_list_when_file_names_are_not_valid(self, tmp_path):
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()
        sub_dir1 = test_dir / "subfolder1"
        sub_dir1.mkdir()
        file1 = sub_dir1 / "file1.txt"
        file1.write_text("File 1 content")

        result = report.get_unit_test_files_list(test_dir)
        expected_files = []
        assert result == expected_files

    def test_given_a_count_number_should_return_the_number_of_files_in_the_list(self, tmp_path):
        test_dir = tmp_path / "test_directory"
        test_dir.mkdir()
        sub_dir1 = test_dir / "subfolder1"
        sub_dir1.mkdir()
        file1 = sub_dir1 / "unit_test_file1_unit.py"
        file1.write_text("File 1 content")
        file2 = sub_dir1 / "unit_test_file2_unit.py"
        file2.write_text("File 2 content")
        file3 = sub_dir1 / "unit_test_file3_unit.py"
        file3.write_text("File 3 content")
        file4 = sub_dir1 / "unit_test_file4_unit.py"
        file4.write_text("File 4 content")

        result = report.get_unit_test_files_list(test_dir, count=3)
        assert len(result) == 3

    def test_given_a_file_path_should_return_its_module_name(self):
        file_path = "/path/to/package/subfolder1/unit_test_something_unit.py"
        package_name = "package"
        module_name = report.get_module_name(file_path, package_name)

        assert module_name == f"{package_name}.subfolder1.unit_test_something_unit"

    @patch("tests.e2e.generating_unit_test_report.get_module_name",
           return_value="package.subfolder1.unit_test_something_unit")
    @patch("importlib.import_module", return_value=MagicMock())
    def test_given_a_file_path_should_run_its_main_function_if_it_exists_and_is_callable(
            self,
            mock_import_module,
            mock_get_module_name
    ):
        mock_module = mock_import_module.return_value

        mock_module.get_params = MagicMock(return_value="Test Result")

        result = report.execute_test("/path/to/package/subfolder1/unit_test_something_unit.py")

        mock_module.get_params.assert_called_once()
        assert result == "Test Result"

    @patch("tests.e2e.generating_unit_test_report.get_module_name",
           return_value="package.subfolder1.unit_test_something_unit")
    @patch("importlib.import_module", return_value=MagicMock())
    def test_given_a_file_path_should_raise_exception_when_no_main_function_can_be_run(
            self,
            mock_import_module,
            mock_get_module_name
    ):
        mock_module = mock_import_module.return_value
        mock_module.get_params = "Not a callable function"

        with pytest.raises(Exception) as exc:
            report.execute_test("/path/to/package/subfolder1/unit_test_something_unit.py")

        # Assert that the expected exception is raised
        assert str(
            exc.value) == "The module package.subfolder1.unit_test_something_unit does not have a get_params function or it's not callable"

    @patch("tests.e2e.generating_unit_test_report.execute_test")
    def test_given_test_files_list_should_return_results_list_when_tests_are_executed(self, mock_execute_test):
        test_files_list = ["test1.py", "test2.py", "test3.py"]
        expected_results = [
            ["result1", "result2", "result3"],
            ["a", "b", "c", "d"],
            [1, 2, 3, 4, 5]
        ]

        mock_execute_test.side_effect = expected_results

        result = report.traverse_and_execute_test_cases(test_files_list)
        assert result == expected_results


class TestGenerateReportFromTestingDetails:
    def test_should_get_dataframe_from_testing_details_excel_file(self):
        # report.get_testing_details_dataframe_from_excel("/tmp/test.xlsx")
        assert True

    def test_given_test_details_should_return_a_expended_dataframe_containing_testing_results(self):
        original_columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result"]
        original_data = [
            ("use_case_1", "scenario_1", "prompt_1_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}",
             "llm_result_1_1", "pass"),
            ("use_case_1", "scenario_2", "prompt_1_2", "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}",
             "llm_result_1_2", "fail"),
            ("use_case_2", "scenario_1", "prompt_2_1", "{\"temperature\": 0, \"top_p\": 0.8, \"jsonable\": true}",
             "llm_result_2_1", "pass"),
            ("use_case_2", "scenario_2", "prompt_2_2", "{\"temperature\": 0.8, \"top_p\": 0.9, \"jsonable\": true}",
             "llm_result_2_2", "good"),
        ]
        original_df = pd.DataFrame(data=original_data, columns=original_columns)

        expected_columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result",
                            "fail", "pass", "unknown", "pass percentage", "fail percentage"]
        expected_data = [
            ["use_case_1", "scenario_1", "prompt_1_1",
             "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}", "llm_result_1_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_1", "scenario_2", "prompt_1_2",
             "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}", "llm_result_1_2",
             "fail", 1.0, 0.0, 0.0, 0.0, 100.0],
            ["use_case_2", "scenario_1", "prompt_2_1",
             "{\"temperature\": 0, \"top_p\": 0.8, \"jsonable\": true}", "llm_result_2_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_2", "scenario_2", "prompt_2_2",
             "{\"temperature\": 0.8, \"top_p\": 0.9, \"jsonable\": true}", "llm_result_2_2",
             "unknown", 0.0, 0.0, 1.0, 0.0, 0.0]
        ]
        expected_df = pd.DataFrame(data=expected_data, columns=expected_columns)

        actual_result_df = report.statistic_testing_result(original_df)

        assert actual_result_df.equals(expected_df)

    def test_given_test_details_should_return_a_summary_df(self):
        original_columns = ["use_case", "scenario", "prompt_template", "params", "llm_result", "test_result"]
        original_data = [
            ("use_case_1", "scenario_1", "prompt_template_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}",
             "llm_result_1_1", "pass"),
            ("use_case_2", "scenario_1", "prompt_template_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}",
             "llm_result_2_1", "fail"),
            ("use_case_2", "scenario_2", "prompt_template_2", "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}",
             "llm_result_2_2", "pass"),
            ("use_case_3", "scenario_1", "prompt_template_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}",
             "llm_result_2_2", "fail"),
        ]
        original_df = pd.DataFrame(data=original_data, columns=original_columns)

        expected_columns = ["scenario", "prompt_template", "params", "total", "pass", "fail", "pass percentage", "fail percentage"]
        expected_data = [
            ["scenario_1", "prompt_template_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}", 3.0, 1.0, 2.0, 33.333, 66.666],
            ["scenario_2", "prompt_template_2", "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}", 1.0, 1.0, 0.0, 100.0, 0.0],
        ]
        expected_df = pd.DataFrame(data=expected_data, columns=expected_columns)

        actual_result_df = report.statistic_testing_result(original_df)

        assert_frame_equal(actual_result_df, expected_df)

    def test_given_dataframe_should_extract_keys_to_new_columns_if_it_is_json_string(self):
        original_columns = ["column1", "column2"]
        original_data = [
            ("row1", "{\"key1\": \"value11\", \"key2\": \"value21\"}"),
            ("row2", "{\"key1\": \"value12\", \"key2\": \"value22\"}"),
        ]
        original_df = pd.DataFrame(data=original_data, columns=original_columns)

        expected_columns = ["column1", "key1", "key2"]
        expected_data = [
            ("row1", "value11", "value21"),
            ("row2", "value12", "value22")
        ]
        expected_df = pd.DataFrame(data=expected_data, columns=expected_columns)

        actual_result_df = report.unnest_json_values(original_df, "column2")

        assert actual_result_df.equals(expected_df)

    def test_group_dataframe(self):
        expected_columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result",
                            "fail", "pass", "unknown", "pass percentage", "fail percentage"]
        expected_data = [
            ["use_case_1", "scenario_1", "prompt_1_1",
             "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}", "llm_result_1_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_1", "scenario_2", "prompt_1_2",
             "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}", "llm_result_1_2",
             "fail", 1.0, 0.0, 0.0, 0.0, 100.0],
            ["use_case_2", "scenario_1", "prompt_2_1",
             "{\"temperature\": 0, \"top_p\": 0.8, \"jsonable\": true}", "llm_result_2_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_2", "scenario_2", "prompt_2_2",
             "{\"temperature\": 0.8, \"top_p\": 0.9, \"jsonable\": true}", "llm_result_2_2",
             "unknown", 0.0, 0.0, 1.0, 0.0, 0.0]
        ]
        expected_df = pd.DataFrame(data=expected_data, columns=expected_columns)

        grouped_df = expected_df.groupby(["scenario", "use_case"]).sum()

        # Write the grouped DataFrame to an Excel file
        output_file = "output.xlsx"
        with pd.ExcelWriter(output_file) as writer:
            grouped_df.to_excel(writer, sheet_name="Grouped Data", index=True)

        print(f"DataFrame has been written to {output_file}.")

    def test_grouping(self):
        columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result",
                            "fail", "pass", "unknown", "pass percentage", "fail percentage"]
        data = [
            ["use_case_1", "scenario_1", "prompt_1_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}",
             "llm_result_1_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_1", "scenario_2", "prompt_1_2", "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}",
             "llm_result_1_2",
             "fail", 1.0, 0.0, 0.0, 0.0, 100.0],
            ["use_case_2", "scenario_1", "prompt_2_1", "{\"temperature\": 0, \"top_p\": 0.8, \"jsonable\": true}",
             "llm_result_2_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_2", "scenario_2", "prompt_2_2", "{\"temperature\": 0.8, \"top_p\": 0.9, \"jsonable\": true}",
             "llm_result_2_2",
             "unknown", 0.0, 0.0, 1.0, 0.0, 0.0]
        ]
        df = pd.DataFrame(data=data, columns=columns)

        # Group the DataFrame by "scenario" and "use_case"
        grouped_df = df.groupby(["scenario", "use_case"]).sum().sort_index()

        expected_grouped_columns = ["prompt", "params", "llm_result", "test_result",
                                    "fail", "pass", "unknown", "pass percentage", "fail percentage"]
        expected_grouped_data = [
            ["prompt_1_1", "{\"temperature\": 0, \"top_p\": 0.7, \"jsonable\": true}", "llm_result_1_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["prompt_2_1", "{\"temperature\": 0, \"top_p\": 0.8, \"jsonable\": true}", "llm_result_2_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["prompt_1_2", "{\"temperature\": 0.9, \"top_p\": 0.8, \"jsonable\": true}", "llm_result_1_2",
             "fail", 1.0, 0.0, 0.0, 0.0, 100.0],
            ["prompt_2_2", "{\"temperature\": 0.8, \"top_p\": 0.9, \"jsonable\": true}", "llm_result_2_2",
             "unknown", 0.0, 0.0, 1.0, 0.0, 0.0]
        ]
        index_tuples = [
            ('scenario_1', 'use_case_1'),
            ('scenario_1', 'use_case_2'),
            ('scenario_2', 'use_case_1'),
            ('scenario_2', 'use_case_2')
        ]
        names = ["scenario", "use_case"]
        index = pd.MultiIndex.from_tuples(index_tuples, names=names)
        expected_grouped_df = pd.DataFrame(data=expected_grouped_data, columns=expected_grouped_columns,
                                           index=index).sort_index()

        pd.testing.assert_frame_equal(grouped_df, expected_grouped_df)
