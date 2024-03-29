def standardize_session_name(session_name, prefix=""):
    session_name = session_name.replace(" ", "_").replace("-", "_")
    return f"{prefix}{session_name}"


def get_log_id_filter(specific_log_ids: list[str]):
    log_id_filter = ""
    if specific_log_ids:
        log_ids = [f"'{log_id}'" for log_id in specific_log_ids]
        log_test_ids = [f"'test__e2e_test___{log_id}'" for log_id in specific_log_ids]
        log_id_filter = f" and log_id in ({','.join(log_ids + log_test_ids)})"
    return log_id_filter
