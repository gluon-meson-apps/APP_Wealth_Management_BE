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

## bank line validation result and rate info
{{user_data}}

## User question
{{user_input}}

## ATTENTION
in the reply template, if user is just asking about confirmation or financing or Post-acceptance discounting only, pls just reply that user asked in the email

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

Dear <Customer>,
At present, we do have bank line for your transaction.
Subject to availability of bank lines, terms and conditions of DC acceptable to us and internal approvals, our indicative rates are:
Confirmation only: {{rate}}%p.a. from date of confirmation to DC expiry (plus usance period, if any). Minimum confirmation fee of [user insert min. fee] applies

Post-acceptance discounting only: {{rate}}%p.a + [insert margin]%p.a. from date of discounting to bill maturity. Minimum discounting interest of [insert min. fee] per bill applies.

Confirmation and pre-acceptance discounting: 
For confirmation, {{rate}}%p.a. from date of confirmation to DC expiry (plus usance period, if any). Minimum confirmation fee of [insert min. fee] applies. 

For discounting, {{rate}}%p.a + [insert margin]%p.a. from date of discounting to bill maturity. Minimum discounting interest of [insert min. fee] per bill applies.
Thank you

## INSTRUCT
now, follow the reply template to answer user question AND based on the user question and reference data, give your summarize(NOT in email template)

"""

function_call_prompt = """
## User input
{{user_input}}
"""

validate_bank_line_prompt = """## Role
you are a helpful assistant, according to bank line rule, you need to validate LC amount and usance period and maturity
## bank line rule
{{bank_line_rule}}
## user data
{{user_data}}
## ATTENTION
1. if user not provide the LC amount or usance period or maturity, DON'T do the validation for LC amount or usance period or maturity
## OUTPUT FORMAT
{
"chain of thought": "...", // should start with "let's follow the flow of rule checking and think step by step"
"validation_failed_reason": {...}, // if the validation result is false, should give the validation failed reason
"validation_result": true/false
}
"""

tools = [
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "validate_bank_line",
            "description": "validate/check bank line",
        }
    }]


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


class RMAPricingAction(TBGuruAction):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "rma_pricing"

    async def _validate_bank_line(self, model, counterparty_bank, session_id, validity, tenor,
                                  amount: str = None) -> dict:
        validation_info = {}
        extra_fields = {"country_classification": counterparty_bank["country_credit_classification"]}
        query = f"search the counterparty bank line rule #extra infos: fields to be queried: {extra_fields}"
        response = await self.unified_search.search(SearchParam(query=query), session_id)
        if len(response) > 0 and response[0].total > 0:
            user_data = {
                "maturity": f"{validity.days + tenor.days} days",
                "usance period": f"{tenor.days} days",
                "lc amount": amount,
                "crr": counterparty_bank["crr"]
            }
            chat_message_preparation = ChatMessagePreparation()
            chat_message_preparation.add_message(
                "user",
                validate_bank_line_prompt,
                user_data=user_data,
                bank_line_rule=response[0].items
            )
            chat_message_preparation.log(logger)
            result = (await model.achat(**chat_message_preparation.to_chat_params(), max_length=256, jsonable=True,
                                        sub_scenario="validate bank line")).get_json_response()
            logger.info(f"function call result: {result}")
            validation_info.update({"reference": response[0].items, "result": result})
        return validation_info

    async def _search_pricing(self, counterparty_bank, tenor, session_id, pricing_type: str = "confirmation"):
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
            rate_info.update({"reference": response[0].items})
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

    async def _execute_function_call(self, model, counterparty_bank, tenor, validity, lc_mount, session_id, message) \
            -> tuple[dict, dict]:
        rate_info = {}
        validation_info = {}
        functions_dict = {item['function']['name']: item['function'] for item in message}
        if "validate_bank_line" in functions_dict:
            validation_info = await self._validate_bank_line(model, counterparty_bank, session_id, validity, tenor,
                                                             lc_mount)
            if validation_info.get("result", {}).get("validation_result", False):
                if "search_pricing" in functions_dict:
                    pricing_type = json.loads(functions_dict["search_pricing"]["arguments"])["pricing type"]
                    rate_info = await self._search_pricing(counterparty_bank, tenor, session_id, pricing_type)
        return validation_info, rate_info

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
        country_of_rma_holder = entity_dict.get("country of rma holder")
        bic_code = entity_dict.get("bic code")
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
        result = (await chat_model.achat(**chat_message_preparation.to_chat_params(), max_length=256,
                                         tools=tools, sub_scenario="function call")).response
        logger.info(f"function call result: {result}")

        # execute function and format replay template
        if isinstance(result, list):
            validation_info, rate_info = await self._execute_function_call(chat_model, counterparty_bank_dict, tenor,
                                                                           validity, entity_dict.get("LC amount"),
                                                                           context.conversation.session_id,
                                                                           result)
            logger.info("rma execute function call result, validation_info: {}, rate_info: {}",
                        validation_info.get("result"), rate_info.get("rate"))
            if validation_info.get("reference"):
                all_banks.extend(validation_info.get("reference"))
            if rate_info.get("reference"):
                all_banks.extend(rate_info.get("reference"))
            if validation_info.get("result") and validation_info.get("result").get("validation_result") is False:
                failed_reason = validation_info.get("result").get("validation_failed_reason")
                final_result = f"The transaction falls outside of delegated authority. Please seek for Trade Transaction Approval (TTA).{failed_reason}"
            else:
                chat_message_preparation = ChatMessagePreparation()
                chat_message_preparation.add_message(
                    "user",
                    prompt,
                    counterparty_bank=json.dumps(counterparty_bank_dict),
                    user_data=json.dumps(
                        {"bank_line_validation_result": validation_info.get("result"), "rate": rate_info.get("rate")}),
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
