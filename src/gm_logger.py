import inspect
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s: %(message)s')


def get_logger():
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    filename = module.__file__.split('/')[-1]
    # filename = module.__name__
    return logging.getLogger(filename)
