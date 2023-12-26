from nlu.intent_with_entity import Slot


def test_equality():
    assert set() == {Slot(name="A", description="B")} - {
        Slot(name="A", description="BB")
    }
