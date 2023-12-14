from enum import Enum, unique

import chinese2digits as c2d


@unique
class NormalizeType(str, Enum):
    STRING = "STRING"
    PERCENTAGE = "PERCENTAGE"
    NUMBER = "NUMBER"


class OutputAdapter:
    def process_output(self, output: object) -> object:
        raise NotImplementedError()

    def normalize_slot_value(self, output: str, normalize_type: NormalizeType) -> str:
        raise NotImplementedError()


class BaseOutputAdapter(OutputAdapter):
    def process_output(self, output: object) -> object:
        return output

    def normalize_slot_value(self, slot_value: str, normalize_type: NormalizeType) -> str:
        if normalize_type == NormalizeType.PERCENTAGE:
            result = c2d.takeNumberFromString(slot_value)
            return str(round(float(result['digitsStringList'][0]) * 10) * 10)
        if normalize_type == NormalizeType.NUMBER:
            replaced_value = (slot_value
                              .replace("倒数", "负")
                              .replace("第", ""))
            result = c2d.takeNumberFromString(replaced_value)
            return result['digitsStringList'][0]
        return slot_value
