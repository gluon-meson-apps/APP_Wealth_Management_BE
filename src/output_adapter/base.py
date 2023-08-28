class OutputAdapter:
    def process_output(self, output: str) -> str:
        raise NotImplementedError()


class BaseOutputAdapter(OutputAdapter):
    def process_output(self, output: str) -> str:
        return output
