import asyncio
import importlib

import streamlit as st
import os

from streamlit_tree_select import tree_select

from tests.e2e.generate_fix_test import generate_fix_test
from tests.e2e.test import folder_to_dict, convert_folder_dict_list_like
from code_editor import code_editor

st.set_page_config(layout="wide")

@st.cache_data
def get_nodes(rootdir):
    nodes = convert_folder_dict_list_like(folder_to_dict(rootdir))
    return nodes

# Using "with" notation
with st.sidebar:
    log_env = st.selectbox("Select log environment", ["bj-3090", "local"])

    db = st.secrets[log_env+ "-db"]

    for key in db:
        os.environ[key] = db[key]

    st.write("db name:", db['GLUON_MESON_SDK_LOG_DB_DATABASE'])
    rootdir = './tests/e2e/generated'
    root_folder = st.text_input("Enter log id", rootdir)

    nodes = get_nodes(root_folder)
    return_select = tree_select(nodes)
    st.write(return_select)

col1, col2 = st.columns([3, 1])
the_code = None

with col1:
    log_id = st.text_input("Enter log id")


    if st.button("Generate Fix Test"):
        generate_fix_test([log_id])
    st.write(f"Fix test {log_id} generated")
    if return_select and return_select['checked']:
        with open(root_folder+"/"+return_select['checked'][-1], "r") as f:
            the_code = code_editor(f.read())
            st.write(the_code)
            if the_code["type"] == "submit":
                with open(root_folder+"/"+return_select['checked'][-1], "w") as wf:
                    wf.write(the_code["text"])


package = 'tests.e2e.generated'
with col2:
    if the_code and the_code["type"] == "submit":
        module_name = package + return_select['checked'][-1].replace('/', ".").replace(".py", "")
        module = importlib.import_module(module_name)
        # if hasattr(module, "get_params") and callable(module.get_params):
        #     st.write(module.get_params())

        # return use_case, scenario, chat_params["text"], json.dumps(params), result, ""
        st.write("result: "+ asyncio.run(module.main())[4])
        # else:
        #     raise Exception(f"The module {module_name} does not have a get_params function or it's not callable")
