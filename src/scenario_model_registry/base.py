import logging
import os
import requests
from gluon_meson_sdk.models.util import request_with_exception_process


class BaseScenarioModelRegistryCenter:
    def __init__(self) -> None:
        key = "GLUON_MESON_CONTROL_CENTER_ENDPOINT"
        if key not in os.environ:
            logging.warning(
                f"{key} not found in environment variables. and control_center_endpoint is not set; will be set to http://sz.private.gluon-meson.tech:18000")
            self.control_center_endpoint = "http://sz.private.gluon-meson.tech:11000/control-center"
        else:
            self.control_center_endpoint = os.environ.get(key)

    def get_model(self, scenario_model):
        raise NotImplementedError()


class DefaultScenarioModelRegistryCenter(BaseScenarioModelRegistryCenter):

    def get_model(self, scenario_model):
        scenario_model_info = self.get_scenario_model(scenario_model)
        if scenario_model_info is None:
            raise Exception(f'scenario model {scenario_model} not existed')
        #  TODO: call sdk to get  model instance

    def get_scenario_model(self, scenario_model: str):
        return request_with_exception_process(
            lambda: requests.get(f'{self.control_center_endpoint}/scenario_models?name={scenario_model}'))
