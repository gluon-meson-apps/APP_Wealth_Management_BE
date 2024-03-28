import json
from datetime import datetime

import dateparser
from gluon_meson_sdk.models.abstract_models.chat_message_preparation import ChatMessagePreparation
from loguru import logger

from action.base import ActionResponse, ChatResponseAnswer, ResponseMessageType, GeneralResponse
from action.actions.tb_guru.base import TBGuruAction
from third_system.search_entity import SearchParam

prompt = """"## Role
you are a helpful assistant, you need to answer the user query based on the given reference data, AND follow the given reply template when formatting your output

## counterparty bank

{{counterparty_bank}}

## rate

{{rate}}

## User question
{{user_input}}

## reply template
Please find the counterparty bank details below:

counterparty bank details:
Counterparty bank name: ***
Counterparty bank country: ***
Counterparty bank type: ***
CBID: ***
Counterparty bank SWIFT: ***
Country Credit Classification: ***
CRR: ***
Confirmation/Negotiation Credit Status: ***
RMA with {{country_of_rma_or_bic}}: ***

## INSTRUCT
now, follow the reply template to answer user question and give the final result in detail
"""

function_call_prompt = """
## User input
{{user_input}}
"""

tools = [{
    "type": "function",
    "function": {
        "name": "search_pricing",
        "description": "search rate for confirmation/financing",
        "parameters": {
            "type": "object",
            "properties": {
                "pricing type": {
                    "type": "string",
                    "description": "rate or pricing type that user is asking",
                    "enum": ["confirmation", "financing"],

                }
            },
            "required": ["pricing type"]
        }
    }
}]


# {
#     "type": "function",
#     "function": {
#         "name": "validate_bank_line",
#         "description": "validate/check bank line",
#     }
# }]


def is_float(string) -> bool:
    try:
        float(string)
        return True
    except ValueError:
        return False


def validate_rma_status(counterparty_bank, rma_country, bic_code) -> bool:
    if rma_country:
        for key, value in counterparty_bank.items():
            if key.startswith(rma_country.lower()) and value and value.lower() != "no":
                return True
    if bic_code:
        for key, value in counterparty_bank.items():
            if key.endswith(bic_code.lower()) and value and value.lower() != "no":
                return True
    return False


def validate_credit_status(counterparty_bank) -> bool:
    credit_status = counterparty_bank["confirmation/negotiation_credit_status"]
    return credit_status and "PROCEED WITHIN DELEGATED AUTHORITY".lower() == credit_status.lower()


def validate_counterparty_bank(counterparty_bank, all_banks, intent,
                               bank_info, country_of_rma_holder, bic_code) -> ActionResponse:
    rma_status_validation_result = validate_rma_status(counterparty_bank, country_of_rma_holder, bic_code)
    logger.info("rma status validation result {}", rma_status_validation_result)
    if not rma_status_validation_result:
        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=f"HSBC {country_of_rma_holder or bic_code} don't have RMA with '{bank_info}'. Please seek for Trade Transaction Approval (TTA).",
            intent=intent,
            references=all_banks,
        )
        return GeneralResponse(code=200, message="failed", answer=answer, jump_out_flag=False)

    credit_status_validation_result = validate_credit_status(counterparty_bank)
    if not credit_status_validation_result:
        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content="The transaction falls outside of delegated authority. Please seek for Trade Transaction Approval (TTA).",
            intent=intent,
            references=all_banks,
        )
        return GeneralResponse(code=200, message="failed", answer=answer, jump_out_flag=False)


lc_amount_mapping = {
    (0.1, 1.2): 20000000,
    (2.1, 3.3): 10000000,
    (4.1, 6.1): 5000000,
    (6.2, 9): 1500000,
}


def validate_bank_line(counterparty_bank, validity, tenor, amount) -> bool:
    credit_classification = counterparty_bank["country_credit_classification"]
    maturity = validity.months + tenor.months
    if credit_classification and credit_classification.lower() in ["prm", "nor", "fair"]:
        if maturity > 12:
            return False
        if amount:
            crr = counterparty_bank["crr"]
            max_amount = next((value for key, value in lc_amount_mapping.items() if key[0] <= crr <= key[1]), None)
            if max_amount and amount > max_amount:
                return False
    if credit_classification and credit_classification.lower() in ["cbc", "rst", "con"]:
        if maturity > 12:
            return False
        if tenor.days > 180:
            return False
        if amount and amount > 500000:
            return False
    # todo: check Business requirement
    return False


class RMAPricingAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "rma_pricing"

    async def search_pricing(self, counterparty_bank, tenor, session_id, pricing_type: str = "confirmation"):
        rate_info = {}
        ratio = 1
        is_hsbc_group = False
        if "china" == counterparty_bank["country"].lower():
            extra_fields = {"crr": counterparty_bank["crr"], "cbid": counterparty_bank["cbid"],
                            "country_classification": counterparty_bank["country_credit_classification"]}
            query = f"search the China {pricing_type} price #extra infos: fields to be queried: {extra_fields}"
        else:
            counterparty_type = counterparty_bank["current_counterparty_type"]
            if counterparty_type and "hsbc group" == counterparty_type.lower():
                ratio = 100
                is_hsbc_group = True
                extra_fields = {"country_classification": counterparty_bank["country_credit_classification"]}
                query = f"search the intragroup price #extra infos: fields to be queried: {extra_fields}"
            else:
                ratio = 10000
                extra_fields = {"crr": counterparty_bank["crr"]}
                query = f"search the {pricing_type} price #extra infos: fields to be queried: {extra_fields}"
        logger.info(f"search query: {query}")

        response = await self.unified_search.search(SearchParam(query=query), session_id)
        if len(response) > 0 and response[0].total > 0:
            item = response[0].items[0]
            rate_info.update({"reference": item})
            field_mapping = {
                (1, 30): "30_days",
                (91, 180): "180_days",
                (181, 360): "360_days"
            }
            if is_hsbc_group:
                field_mapping.update({(31, 60): "60_days", (61, 90): "60_days"})
            else:
                field_mapping.update({(31, 90): "90_days"})
            for (start, end), field in field_mapping.items():
                if start <= tenor.days <= end:
                    rate_value = item.dict().get(field)
                    if is_float(rate_value):
                        rate_value = format(float(rate_value) / ratio, ".4f")
                    rate_info.update({"rate": rate_value})
        return rate_info

    async def execute_function_call(self, counterparty_bank, tenor, session_id, message):
        rate = None
        bank_line_validation_result = None
        for function_item in message:
            if function_item["type"] == "function":
                if function_item["function"]["name"] == "search_pricing":
                    pricing_type = json.loads(function_item["function"]["arguments"])["pricing type"]
                    return await self.search_pricing(counterparty_bank, tenor, session_id, pricing_type)
                else:
                    # todo: handle error
                    return None

    async def run(self, context) -> ActionResponse:
        logger.info(f"exec action: {self.get_name()} ")
        intent = context.conversation.current_intent.name
        chat_model = await self.scenario_model_registry.get_model(self.scenario_model, context.conversation.session_id)
        entity_dict = context.conversation.get_simplified_entities()
        expiry_date = dateparser.parse(entity_dict["expiry date"])
        issuance_date = dateparser.parse(entity_dict["issuance date"])
        tenor = datetime.now() - dateparser.parse(entity_dict["tenor"])
        validity = expiry_date - issuance_date
        logger.info("time info {} {} {}", expiry_date, issuance_date, tenor.days)

        fields_to_extract = ['bank entity name', 'country of bank', 'SWIFT code']
        bank_info = {field: entity_dict[field] for field in fields_to_extract if field in entity_dict}
        query = f"search the counterparty bank #extra infos: fields to be queried: {bank_info} "
        logger.info(f"search query: {query}")

        response = await self.unified_search.search(SearchParam(query=query), context.conversation.session_id)
        logger.info(f"search response: {response}")

        bank_info_str = ', '.join(bank_info.values())
        all_banks = [item for res in response for item in res.items]
        if len(all_banks) == 0:
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=f"the bank '{bank_info_str}' cannot be found in the Counterparty Bank file, please do further checks.",
                intent=context.conversation.current_intent.name,
            )
            return GeneralResponse(code=200, message="failed", answer=answer, jump_out_flag=False)

        # validate counterparty bank information
        counterparty_bank = next((bank for bank in all_banks if is_float(bank.crr)), None)
        if counterparty_bank is None:
            answer = ChatResponseAnswer(
                messageType=ResponseMessageType.FORMAT_TEXT,
                content=f"the bank '{bank_info_str}' don't have CRR. Please seek for Trade Transaction Approval (TTA).",
                intent=intent,
                references=all_banks,
            )
            return GeneralResponse(code=200, message="failed", answer=answer, jump_out_flag=False)
        counterparty_bank_dict = counterparty_bank.dict()
        country_of_rma_holder = entity_dict.get("country of rma holder", None)
        bic_code = entity_dict.get("bic code", None)
        validation_response = validate_counterparty_bank(counterparty_bank_dict, all_banks, intent,
                                                         bank_info_str, country_of_rma_holder, bic_code)
        if validation_response:
            return validation_response

        user_input = context.conversation.current_user_input
        chat_message_preparation = ChatMessagePreparation()
        chat_message_preparation.add_message(
            "user",
            function_call_prompt,
            user_input=user_input
        )
        chat_message_preparation.log(logger)
        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=512,
                                         tools=tools, sub_scenario="function call")).response
        logger.info(f"function call result: {result}")

        # calculate confirmation/pricing rate and format replay template
        if isinstance(result, list):
            rate_info = await self.execute_function_call(counterparty_bank_dict, tenor,
                                                                    context.conversation.session_id,
                                                                    result)
            if rate_info.get("reference"):
                all_banks.append(rate_info.get("reference"))
            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message(
                "user",
                prompt,
                counterparty_bank=json.dumps(counterparty_bank_dict),
                rate=rate_info.get("rate"),
                user_input=user_input,
                country_of_rma_or_bic=country_of_rma_holder or bic_code
            )
            chat_message_preparation.log(logger)
            final_result = (
                await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=2048)).response
            logger.info(f"final result: {final_result}")
        else:
            final_result = result

        # final response
        answer = ChatResponseAnswer(
            messageType=ResponseMessageType.FORMAT_TEXT,
            content=final_result,
            intent=intent,
            references=all_banks,
        )
        return GeneralResponse(code=200, message="success", answer=answer, jump_out_flag=False)
