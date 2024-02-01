import glob
import os
from enum import Enum
from pathlib import Path

from utils.utils import format_jinja_template


# get current file directory

class TestType(str, Enum):
    E2E = "E2E"
    UNIT = "UNIT"
    LOG = "LOG"

class TestFile:
    def __init__(self, path: str):
        self.path = Path(path)
        self.name = self.path.name
        self.test_type = self.parse_test_type(self.path)

    def get_name_without_extension(self):
        return self.path.name.replace(".py", "")

    def get_absolute_path(self):
        return self.path.absolute()

    def __str__(self):
        return self.path.name

    def __repr__(self):
        return self.__str__()

    def get_python_module_name(self):
        return "tests.e2e" + self.get_absolute_path().as_posix().split("tests/e2e")[1].replace("/", ".").replace(".py", "")

    def get_parent_python_module_name(self):
        return "tests.e2e" + self.get_absolute_path().parent.as_posix().split("tests/e2e")[1].replace("/", ".")


    def parse_test_type(self, path: Path) -> str:
        if path.parent.name == "generated_e2e_test":
            if path.name.endswith("e2e.py"):
                return TestType.E2E
            elif path.name.endswith("log.py"):
                return TestType.LOG
            else:
                raise ValueError("Invalid test type")
        elif path.parent.name == "generated_unit_test":
            return TestType.UNIT
        else:
            raise ValueError("Invalid test type")


class TestCollector:
    def __init__(self, test_folder: str = "generated_golden_test_set", calling_folder:str = "generated_golden_test_set_calling"):
        self.test_folder = test_folder
        self.current_file_dir = os.path.dirname(os.path.abspath(__file__))
        self.calling_folder = calling_folder

        self.files = glob.glob(f"{self.current_file_dir}/{self.test_folder}/**/*.py", recursive=True)
        self.test_files = [TestFile(f) for f in sorted(self.files)]
    def get_all_e2e_tests(self):
        return [f for f in self.test_files if f.test_type == TestType.E2E]

    def generate_one_file_to_call_all_e2e_test(self):
        e2e_tests = self.get_all_e2e_tests()
        e2e_imports = [f'from {f.get_parent_python_module_name()} import {f.get_name_without_extension()}' for f in e2e_tests]
        e2e_test_calls = [f"{f.get_name_without_extension()}.main()" for f in e2e_tests]
        with open(f"{self.current_file_dir}/overall_e2e_calling.jinja2", "r") as rf:
            template = rf.read()
            template = format_jinja_template(template, imports=e2e_imports, func_calls=e2e_test_calls)
        Path(f"{self.current_file_dir}/{self.calling_folder}/").mkdir(parents=True, exist_ok=True)
        with open(f"{self.current_file_dir}/{self.calling_folder}/overall_e2e_calling.py", "w") as wf:
            wf.write(template)


        return template

    def get_all_log(self):
        logs = [f for f in self.test_files if f.test_type == TestType.LOG]
        logs_imports = [f'from {f.get_parent_python_module_name()} import {f.get_name_without_extension()}' for f in logs]
        log_names = [f"{f.get_name_without_extension()}" for f in logs]
        with open(f"{self.current_file_dir}/overall_unit_test_calling.jinja2", "r") as rf:
            template = rf.read()
            template = format_jinja_template(template, imports=logs_imports, log_names=log_names)
        Path(f"{self.current_file_dir}/{self.calling_folder}/").mkdir(parents=True, exist_ok=True)
        with open(f"{self.current_file_dir}/{self.calling_folder}/overall_unit_test_calling.py", "w") as wf:
            wf.write(template)


        return template



if __name__ == "__main__":
    print(TestCollector().generate_one_file_to_call_all_e2e_test())
    print(TestCollector().get_all_log())
