import json

from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ResponseMessageType, ChatResponseAnswer, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from third_system.search_entity import SearchParam
from utils.action_helper import format_entities_for_search

prompt = """## Role
you are a helpful assistant, based on provided all banks info, retrieve EVERY bank's RMA status and bank info

## ATTENTION
if all banks has more than one item, should retrieve RMA status of country {{country_of_rma}} and bank info for every cbid

## all banks info

{{all_banks}}

## issuing bank

{{bank_info}}

## INSTRUCT

now, retrieve EVERY founded bank's RMA status of country {{country_of_rma}} and bank info(INCLUDE column names) one by one,
every counterparty bank has different cbid
"""


class RMACheckingAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "rma_checking"

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
            country_of_rma=entity_dict["country of rma"],
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
