import json

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ChatResponseAnswer, ResponseMessageType, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from third_system.search_entity import SearchParam
from utils.action_helper import format_entities_for_search

prompt = """"## Role
you are a helpful assistant, you need to check LC acceptable for every counterparty bank with different CBID
## LC acceptable check
1. check whether the issuing bank's {{country_of_rma}} RMA status is not NO and check whether the bank's counterparty type is one of FIG Client or HSBC Group or Network Bank.
if not, then return we are not able to accept a letter of credit from the $bank, if yes, then return we are able to accept a letter of credit from the $bank

## ATTENTION
1 if all banks has more than one item, should do the check for every cbid
2 if one bank has more than one RMA column, should do the check for every RMA column

## steps
1. do the LC acceptable check for every counterparty bank with different CBID and different RMA column of {{country_of_rma}}
2. return EVERY bank's {{country_of_rma}} RMA status(es)(INCLUDE column names) and ALL bank info(INCLUDE column names, exclude RMA columns)

## counterparty bank list

{{all_banks}}

## issuing bank

{{bank_info}}

## User input
{{user_input}}

## INSTRUCT

now, answer the question step by step, and reply step result and the final result
"""


class LCAcceptableAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "rma_lc_acceptable"

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        entity_dict = context.conversation.get_simplified_entities()

        bank_info = format_entities_for_search(context.conversation, ["country of HSBC bank", "country of rma"])
        query = "search the counterparty bank" + f"\n #extra infos: fields to be queried: {bank_info} "
        logger.info(f"search query: {query}")

        response = await self.unified_search.search(SearchParam(query=query), context.conversation.session_id)
        logger.info(f"search response: {response}")
        all_banks = []
        for item in response:
            all_banks.extend(item.items)
        if len(all_banks) == 0:
            bank_name = " ".join(json.loads(bank_info).values())
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=f"the bank '{bank_name}' cannot be found in the Counterparty Bank file, please do further checks.",
                intent=context.conversation.current_intent.name,
            )
            return GeneralResponse(code=200, message="failed", answer=answer, jump_out_flag=False)

        all_banks_str = "\n".join([bank.model_dump_json() for bank in all_banks])
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            prompt,
            country_of_rma=entity_dict["country of HSBC bank"],
            all_banks=all_banks_str,
            bank_info=bank_info,
            user_input=context.conversation.current_user_input,
        )
        chat_message_preparation.log(logger)

        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=2048)).response
        logger.info(f"chat result: {result}")

        references = []
        for res in response:
            references += res.items

        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=result,
            intent=context.conversation.current_intent.name,
            references=references,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
