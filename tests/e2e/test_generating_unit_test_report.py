from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

import tests.e2e.generating_unit_test_report as report

"""
- Make the program as a command line script
    - Use the package `click` for bootstrapping the commands
    - Parameters
        - report_file_path
    - [Command] unit_test
    - [Command] report
- Traverse the test case directory and execute all unit tests
    - [x] Traverse the test case directory
        - [x] Filter out all unit tests
        - [x] Get the module name from the test case directory
    - [x] Execute the module
        - [x] Receive the result of the main() function
        - [x] Put the results to a Pandas DataFrame
        - [ ] [TODO] Find out how to judge whether the test passes or fails
    - [x] Write the DataFrame to a specific sheet of an excel file
- Generate a report from the above testing details
    - [x] Group the DataFrame by the scenario
        - [x] Count the number of passed and failed tests
        - [x] Add columns `Positive results` and `Negative results`, fill in the counts
        - [x] Calculate the percentage of passed and failed tests
    - [x] Split the items in the `params` column to new columns
        - [ ] [TODO] Decide how to find the model type
    - [x] Write the new DataFrame to another sheet of the same excel file
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
        mock_module.main.return_value = "Test Result"

        result = report.execute_test("/path/to/package/subfolder1/unit_test_something_unit.py")

        mock_module.main.assert_called_once()
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
        mock_module.main = "Not a callable function"

        with pytest.raises(Exception) as exc:
            report.execute_test("/path/to/package/subfolder1/unit_test_something_unit.py")

        # Assert that the expected exception is raised
        assert str(
            exc.value) == "The module package.subfolder1.unit_test_something_unit does not have a main function or it's not callable"

    @patch("tests.e2e.generating_unit_test_report.execute_test")
    def test_given_test_files_list_should_return_results_list_when_tests_are_executed(self, mock_execute_test):
        test_files_list = ["test1.py", "test2.py", "test3.py"]
        expected_results = [
            ["result1", "result2", "result3"],
            ["a", "b", "c", "d"],
            [1, 2, 3, 4, 5]
        ]

        mock_execute_test.side_effect = expected_results

        result = report.traverse_test_cases(test_files_list)
        assert result == expected_results


class TestGenerateReportFromTestingDetails:
    def test_given_test_details_should_return_a_expended_dataframe_containing_testing_results(self):
        original_columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result"]
        original_data = [
            ("use_case_1", "scenario_1", "prompt_1_1", {"temperature": 0, "top_p": 0.7, "jsonable": True},
             "llm_result_1_1", "pass"),
            ("use_case_1", "scenario_2", "prompt_1_2", {"temperature": 0.9, "top_p": 0.8, "jsonable": True},
             "llm_result_1_2", "fail"),
            ("use_case_2", "scenario_1", "prompt_2_1", {"temperature": 0, "top_p": 0.8, "jsonable": True},
             "llm_result_2_1", "pass"),
            ("use_case_2", "scenario_2", "prompt_2_2", {"temperature": 0.8, "top_p": 0.9, "jsonable": True},
             "llm_result_2_2", "good"),
        ]
        original_df = pd.DataFrame(data=original_data, columns=original_columns)

        expected_columns = ["use_case", "scenario", "prompt", "params", "llm_result", "test_result",
                            "fail", "pass", "unknown", "pass percentage", "fail percentage"]
        expected_data = [
            ["use_case_1", "scenario_1", "prompt_1_1",
             {"temperature": 0, "top_p": 0.7, "jsonable": True}, "llm_result_1_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_1", "scenario_2", "prompt_1_2",
             {"temperature": 0.9, "top_p": 0.8, "jsonable": True}, "llm_result_1_2",
             "fail", 1.0, 0.0, 0.0, 0.0, 100.0],
            ["use_case_2", "scenario_1", "prompt_2_1",
             {"temperature": 0, "top_p": 0.8, "jsonable": True}, "llm_result_2_1",
             "pass", 0.0, 1.0, 0.0, 100.0, 0.0],
            ["use_case_2", "scenario_2", "prompt_2_2",
             {"temperature": 0.8, "top_p": 0.9, "jsonable": True}, "llm_result_2_2",
             "unknown", 0.0, 0.0, 1.0, 0.0, 0.0]
        ]
        expected_df = pd.DataFrame(data=expected_data, columns=expected_columns)

        actual_result_df = report.statistic_testing_result(original_df)

        assert actual_result_df.equals(expected_df)

    def test_given_dataframe_should_extract_keys_to_new_columns_if_it_is_json_string(self):
        original_columns = ["column1", "column2"]
        original_data = [
            ("row1", {"key1": "value11", "key2": "value21"}),
            ("row2", {"key1": "value12", "key2": "value22"}),
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
