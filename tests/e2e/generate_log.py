import os
from pathlib import Path

from tests.e2e.e2e_util import standardize_session_name
from utils.utils import format_jinja_template

data_list = [
    {
        'user': 'Highlight specific provisions in the BR that include the agent / delegation clause',
        'intent': ('{"intent": "br_file_qa", "confidence": 0.95}', 'retry_round1_intent'),
        'entities': ('{ "document": "BR", "provisions": "agent / delegation clause" }', 'retry_round1_entities'),
        'response': (
            'The specific provision in the business resolution (BR) that includes the agent/delegation clause is as follows:\n\n"to appoint and amend, from time to time, authorized signatories for all matters in connection with the operation of the accounts of the Company. The authorized signatories, by joint action of at least two, shall operate the bank accounts, execute or endorse cheques, drafts, wire transfers or other similar instruments."\n\nThis provision allows the authorized signatories of the Company to delegate their authority to operate the bank accounts and perform various banking transactions, such as executing cheques, drafts, wire transfers, or other similar instruments. However, it specifies that such delegation must be done jointly by at least two authorized signatories.',
            'retry_round1_response'
        ),
        'round': 0,
        'round_name': 'round1',
        'imports': ['from tests.e2e.generated.br_qa_1.generated_e2e_test.br_qa_1_e2e import test_br_qa_1_round1'],
    },
    {
        'user': 'Highlight specific provisions in the BR that include the agent / delegation clause',
        'intent': ('{"intent": "br_file_qa", "confidence": 0.95}', 'retry_round1_intent'),
        'entities': ('{ "document_type": "BR", "clause": "agent / delegation clause" }', 'retry_round1_entities'),
        'response': (
            'The specific provision in the business resolution (BR) that includes the agent/delegation clause is as follows:\n\n"to appoint and amend, from time to time, authorized signatories for all matters in connection with the operation of the accounts of the Company. The authorized signatories, by joint action of at least two, shall operate the bank accounts, execute or endorse cheques, drafts, wire transfers or other similar instruments."\n\nThis provision allows the authorized signatories of the Company to delegate their authority to operate the bank accounts and perform various banking transactions, such as executing cheques, drafts, wire transfers, or other similar instruments. However, it specifies that such delegation must be done jointly by at least two authorized signatories.',
            'retry_round1_response'
        ),
        'round': 0,
        'round_name': 'test_round1',
        'imports': ['from tests.e2e.generated.br_qa_1.generated_e2e_test.br_qa_1_e2e import test_br_qa_1_round1'],
    },
    {
        'user': 'tell me more about authorized signatories',
        'intent': ('{"intent": "br_file_qa", "confidence": 0.95}', 'retry_round1_intent'),
        'entities': ('{}', 'retry_round1_entities'),
        'response': (
            "According to the business resolution file, the authorized signatories for COMPANY ABCD are PERSON A, PERSON B, PERSON C, and PERSON D. These authorized signatories are authorized to open, operate, and close accounts of any type with the Bank. They are also authorized to sign, execute, and deliver any account opening, cash management, trade, banking, and other related documentation as required. Additionally, they have the authority to appoint and amend authorized signatories for all matters related to the operation of the company's accounts. The authorized signatories, by joint action of at least two, can operate bank accounts, execute or endorse cheques, drafts, wire transfers, or other similar instruments. They can also give instructions to the Bank and any member of the Bank's Group in respect of electronic banking agreements and channels. Furthermore, they have the power to arrange, negotiate, and approve the terms of cash concentration services and credit facilities provided by the Bank and other banks. They can sign, execute, and deliver any cash concentration services agreements, facility letters, or other required documents on behalf of the company. If any agreement, instrument, or document requires the Common Seal of the Company, it can be affixed in accordance with the Company's Constitution. These authorized signatories will remain in force until an amending resolution is delivered to the Bank.",
            'retry_round1_response'
        ),
        'round': 1,
        'round_name': 'round2',
        'imports': ['from tests.e2e.generated.br_qa_1.generated_e2e_test.br_qa_1_e2e import test_br_qa_1_round1'],
    },
    {
        'user': 'tell me more about authorized signatories',
        'intent': ('{"intent": "br_file_qa", "confidence": 0.95}', 'retry_round1_intent'),
        'entities': ('{}', 'retry_round1_entities'),
        'response': (
            "According to the business resolution file, the authorized signatories for COMPANY ABCD are PERSON A, PERSON B, PERSON C, and PERSON D. These authorized signatories are authorized to open, operate, and close accounts of any type with the Bank. They are also authorized to sign, execute, and deliver any account opening, cash management, trade, banking, and other related documentation as required. Additionally, they have the authority to appoint and amend authorized signatories for all matters related to the operation of the company's accounts. The authorized signatories, by joint action of at least two, can operate bank accounts, execute or endorse cheques, drafts, wire transfers, or other similar instruments. They can also give instructions to the Bank and any member of the Bank's Group in respect of electronic banking agreements and channels. Furthermore, they have the power to arrange, negotiate, and approve the terms of cash concentration services and credit facilities provided by the Bank and other banks. They can sign, execute, and deliver any cash concentration services agreements, facility letters, or other required documents on behalf of the company. If any agreement, instrument, or document needs to be executed under the Common Seal of the Company, the Common Seal can be affixed in accordance with the Company's Constitution. These resolutions will remain in force until an amending resolution has been delivered to the Bank.",
            'retry_round1_response'
        ),
        'round': 1,
        'round_name': 'test_round2',
        'imports': ['from tests.e2e.generated.br_qa_1.generated_e2e_test.br_qa_1_e2e import test_br_qa_1_round1'],
    }]

# params_list = inner_df['params'].apply(process_one_params).tolist()
def generate_one_log(session_name, data_list, generate_dir_name='generated'):
    session_name = standardize_session_name(session_name)
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    with open(f"{cur_dir}/e2e_log_template.jinja2", "r") as rf:
        template = rf.read()
        Path(f"{cur_dir}/{generate_dir_name}/{session_name}/generated_e2e_test").mkdir(parents=True, exist_ok=True)
        with open(f"{cur_dir}/{generate_dir_name}/{session_name}/generated_e2e_test/{session_name}_log.py", "w") as wf:
            wf.write(format_jinja_template(template, data_list=data_list))
