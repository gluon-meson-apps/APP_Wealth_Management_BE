import asyncio
import importlib
import re

import streamlit as st
import os

from streamlit_tree_select import tree_select

from tests.e2e.generate_fix_test import generate_fix_test
from tests.e2e.folder_util import folder_to_dict, convert_folder_dict_list_like
from code_editor import code_editor

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        .stTextArea > label {
            font-size:105%;
            font-weight:bold;
            color:blue;
        }
    </style>
    """, unsafe_allow_html=True)


@st.experimental_memo
def get_nodes(rootdir):
    nodes = convert_folder_dict_list_like(folder_to_dict(rootdir))
    return nodes

def filter_nodes(nodes, id):
    return [node for node in nodes if node['label'].find(id.replace("-", "_")) != -1]


# Using "with" notation
with st.sidebar:
    log_env = st.selectbox("Select log environment", ["bj-3090", "local"])

    db = st.secrets[log_env + "-db"]

    for key in db:
        os.environ[key] = db[key]

    st.write("db name:", db['GLUON_MESON_SDK_LOG_DB_DATABASE'])
    log_id = st.text_input("Enter log id")
    if st.button("Generate Fix Test"):
        generate_fix_test([log_id])
        get_nodes.clear()
    st.write(f"Fix test {log_id} generated")
    root_folder_path = 'tests/e2e/generated'

    root_folder = st.text_input("Enter root folder path", root_folder_path)

    nodes = get_nodes(root_folder)

    if st.button("clear state of codes"):
        if st.session_state.get('current_file', None):
            del st.session_state['current_file']
    id_selector = st.text_input("filter by id")

    filtered_nodes = filter_nodes(nodes, id_selector)


    return_select = tree_select(filtered_nodes)
    st.write(return_select)

col1, col2 = st.columns([2, 3])
the_code = None
package = 'tests.e2e.generated'
round_pattern = re.compile(r"round\d+")

current_file = st.empty()
current_file_str = None

with col1:
    selected_log_files = [i for i in return_select['checked'] if i.find("log") != -1]
    if selected_log_files:
        log_file = package + selected_log_files[-1].replace('/', ".").replace(".py", "")

        # st.write("log file: ")
        # st.write(log_file)
        module = importlib.import_module(log_file)
        result = module.main()['all_local_vars']
        # st.write(result)

        for round_name, scenarios in result.items():
            if re.fullmatch(round_pattern, round_name):
                with st.expander(f"{round_name}: {scenarios['user'][:150]}..."):
                    for scenario_name, scenario_result in scenarios.items():
                        scenario_name_short = scenario_name.split('.')[-1]
                        st.text_area(scenario_name_short, scenario_result, key=scenario_name_short+'text_area'+round_name)
                        if scenario_name != "user":
                            if st.button("show code", key=scenario_name_short+'show_code'+round_name):
                                current_file = scenario_name + ".py"
                                current_file_str = current_file.replace(".", "/")[:-3] + ".py"
                                st.session_state.current_file = current_file_str








with col2:
    # st.write(current_file)

    if return_select and return_select['checked']:
        file = root_folder + "/" + return_select['checked'][-1]
        if st.session_state.get('current_file', None):
            file = st.session_state.current_file
        with open(file, "r") as f:
            the_code = code_editor(f.read())
            # st.write(the_code)
            if the_code["type"] == "submit":
                with open(file, "w") as wf:
                    wf.write(the_code["text"])
    if the_code and the_code["type"] == "submit":
        module_name = package + return_select['checked'][-1].replace('/', ".").replace(".py", "")
        module = importlib.import_module(module_name)
        # if hasattr(module, "get_params") and callable(module.get_params):
        #     st.write(module.get_params())

        # return use_case, scenario, chat_params["text"], json.dumps(params), result, ""
        st.write("result: " + asyncio.run(module.main())[4])
        # else:
        #     raise Exception(f"The module {module_name} does not have a get_params function or it's not callable")
