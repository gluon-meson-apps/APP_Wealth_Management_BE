import json
import os


def record_testing_details(use_case, scenario, prompt, params, llm_result):
    cwd = os.getcwd()
    target_file = cwd + "/e2e/detailed_test_data.xlsx"
    def collect_data():
        return [
            ["use_case", "scenario", "prompt", "param", "llm_result", "test_result"],
            [use_case, scenario, prompt, json.dumps(params), llm_result, ""]
        ]

    def write_testing_details_to_file(details):
        import openpyxl
        wb = openpyxl.load_workbook(target_file)
        ws = wb.active
        for row in details:
            ws.append(row)
        wb.save(target_file)

    data = collect_data()
    write_testing_details_to_file(data)

def extract_info_from_file_name(file_name):
    # file_name: test_round{n}_{scenario}_unit.py
    pass