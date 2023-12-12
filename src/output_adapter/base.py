import chinese2digits as c2d


class OutputAdapter:
    def process_output(self, output: object) -> object:
        raise NotImplementedError()

    def normalize_slot_value(self, output: str) -> str:
        raise NotImplementedError()


class BaseOutputAdapter(OutputAdapter):
    def process_output(self, output: object) -> object:
        return output

    def normalize_slot_value(self, slot_value: str) -> str:
        replaced_value = (slot_value
                          .replace("倒数", "负")
                          .replace("第", ""))
        result = c2d.takeNumberFromString(replaced_value)
        if len(result['digitsStringList']) > 0:
            return result['digitsStringList'][0]
        return result['replacedText']
