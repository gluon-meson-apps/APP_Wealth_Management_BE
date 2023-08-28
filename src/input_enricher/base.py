class InputEnricher:
    def enrich(self, input):
        raise NotImplementedError()


class BaseInputEnricher(InputEnricher):
    def enrich(self, input):
        return input
