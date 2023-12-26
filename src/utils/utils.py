import os
import logging
import logging.handlers

# from aliyun.log import QueuedLogHandler


def get_value_or_default_from_dict(dictionary, key, default_value=None):
    return dictionary[key] if key in dictionary else default_value


def init_logger(module_name):
    env = get_value_or_default_from_dict(os.environ, "DEVELOPMENT_ENV", "dev")
    log_file_folder_path = get_value_or_default_from_dict(
        os.environ, "LOG_FILE_FOLDER_PATH", ""
    )
    single_log_file_max_byte = int(
        get_value_or_default_from_dict(os.environ, "MAX_LOG_BYTES", 50000000)
    )
    log_backup_count = int(
        get_value_or_default_from_dict(os.environ, "LOG_BACKUP_COUNT", 5)
    )

    log_level_by_env = {
        "local": logging.DEBUG,
        "dev": logging.DEBUG,
        "sit": logging.INFO,
        "uat": logging.WARNING,
        "prd": logging.ERROR,
    }
    logger = logging.getLogger(module_name)
    logger.setLevel(log_level_by_env[env])

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_file_folder_path, "app.log"),
        maxBytes=single_log_file_max_byte,
        backupCount=log_backup_count,
    )

    file_handler.setLevel(logger.level)

    console_handler = logging.StreamHandler()
    # console_handler.setLevel(logger.level + 10)
    console_handler.setLevel(logger.level)

    # cloud_log_handler = QueuedLogHandler(
    #     get_value_or_default_from_dict(os.environ, "ALIYUN_ENDPOINT"),
    #     get_value_or_default_from_dict(os.environ, "ALIYUN_ACCESS_KEY_ID"),
    #     get_value_or_default_from_dict(os.environ, "ALIYUN_ACCESS_KEY"),
    #     "insh-gpt-poc",
    #     "log_store",
    #     "topic"
    # )
    # cloud_log_handler.setLevel(logger.level)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    # cloud_log_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    # logger.addHandler(cloud_log_handler)

    return logger
