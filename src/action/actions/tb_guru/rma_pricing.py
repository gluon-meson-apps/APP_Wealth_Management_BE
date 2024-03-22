import json
from datetime import datetime

import dateparser
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ChatResponseAnswer, ResponseMessageType, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from third_system.search_entity import SearchParam
from utils.action_helper import format_entities_for_search

prompt = """"## Role
you are a helpful assistant, you need to check bank line and confirmation/financing pricing rate for counterparty bank

## steps
1. do the LC acceptable check for every counterparty bank with different CBID and different RMA column of
 {{country_of_service_offering_bank}} or {{bic_code}}
2. return EVERY bank's RMA status(es)(INCLUDE column names) and ALL bank info(INCLUDE column names, exclude RMA columns)

## counterparty bank

{{all_banks}}

## issuing bank

{{bank_info}}

## User input
{{user_input}}

## INSTRUCT

now, answer the question step by step, and reply step result and the final result
"""


class RMAPricingAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "rma_pricing"

    async def search_pricing(self, counterparty_bank, tenor, session_id, pricing_type: str = "confirmation"):
        extra_fields = {
            "country": counterparty_bank.country,
            "days": tenor.days,
            "counterparty_type": counterparty_bank.current_counterparty_bank
        }
        query = f"search the {pricing_type} price" + f"\n #extra infos: fields to be queried: {extra_fields} "
        logger.info(f"search query: {query}")

        return await self.unified_search.search(SearchParam(query=query), session_id)



    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        entity_dict = context.conversation.get_simplified_entities()
        expiry_date = dateparser.parse(entity_dict["expiry date"])
        issuance_date = dateparser.parse(entity_dict["issuance date"])
        tenor = datetime.now() - dateparser.parse(entity_dict["tenor"])
        logger.info("time info {} {} {}", expiry_date, issuance_date, tenor.days)

        bank_info = format_entities_for_search(context.conversation, ["country of service provider", "bic code"])
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
            country_of_service_provider=entity_dict["country of service provider"]
            if "country of service provider" in entity_dict.keys()
            else "None",
            bic_code=entity_dict["bic code"] if "bic code" in entity_dict.keys() else "None",
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