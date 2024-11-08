# coding: utf-8

"""
    FastAPI

    No description provided (generated by Openapi Generator https://github.com/openapitools/openapi-generator)

    The version of the OpenAPI document: 0.1.0
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


from __future__ import annotations
import pprint
import re  # noqa: F401
import json

from pydantic import BaseModel, ConfigDict, StrictBool, StrictFloat, StrictInt, StrictStr
from typing import Any, ClassVar, Dict, List, Optional, Union
from nearai.openapi_client.models.response_format import ResponseFormat
from nearai.openapi_client.models.stop import Stop
from typing import Optional, Set
from typing_extensions import Self

class CompletionsRequest(BaseModel):
    """
    Request for completions.
    """ # noqa: E501
    model: Optional[StrictStr] = 'fireworks::accounts/fireworks/models/mixtral-8x22b-instruct'
    provider: Optional[StrictStr] = None
    max_tokens: Optional[StrictInt] = None
    logprobs: Optional[StrictInt] = None
    temperature: Optional[Union[StrictFloat, StrictInt]] = 1
    top_p: Optional[Union[StrictFloat, StrictInt]] = 1
    frequency_penalty: Optional[Union[StrictFloat, StrictInt]] = None
    n: Optional[StrictInt] = 1
    stop: Optional[Stop] = None
    response_format: Optional[ResponseFormat] = None
    stream: Optional[StrictBool] = False
    tools: Optional[List[Any]] = None
    prompt: StrictStr
    __properties: ClassVar[List[str]] = ["model", "provider", "max_tokens", "logprobs", "temperature", "top_p", "frequency_penalty", "n", "stop", "response_format", "stream", "tools", "prompt"]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )


    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of CompletionsRequest from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([
        ])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of stop
        if self.stop:
            _dict['stop'] = self.stop.to_dict()
        # override the default output from pydantic by calling `to_dict()` of response_format
        if self.response_format:
            _dict['response_format'] = self.response_format.to_dict()
        # set to None if provider (nullable) is None
        # and model_fields_set contains the field
        if self.provider is None and "provider" in self.model_fields_set:
            _dict['provider'] = None

        # set to None if max_tokens (nullable) is None
        # and model_fields_set contains the field
        if self.max_tokens is None and "max_tokens" in self.model_fields_set:
            _dict['max_tokens'] = None

        # set to None if logprobs (nullable) is None
        # and model_fields_set contains the field
        if self.logprobs is None and "logprobs" in self.model_fields_set:
            _dict['logprobs'] = None

        # set to None if frequency_penalty (nullable) is None
        # and model_fields_set contains the field
        if self.frequency_penalty is None and "frequency_penalty" in self.model_fields_set:
            _dict['frequency_penalty'] = None

        # set to None if stop (nullable) is None
        # and model_fields_set contains the field
        if self.stop is None and "stop" in self.model_fields_set:
            _dict['stop'] = None

        # set to None if response_format (nullable) is None
        # and model_fields_set contains the field
        if self.response_format is None and "response_format" in self.model_fields_set:
            _dict['response_format'] = None

        # set to None if tools (nullable) is None
        # and model_fields_set contains the field
        if self.tools is None and "tools" in self.model_fields_set:
            _dict['tools'] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of CompletionsRequest from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "model": obj.get("model") if obj.get("model") is not None else 'fireworks::accounts/fireworks/models/mixtral-8x22b-instruct',
            "provider": obj.get("provider"),
            "max_tokens": obj.get("max_tokens"),
            "logprobs": obj.get("logprobs"),
            "temperature": obj.get("temperature") if obj.get("temperature") is not None else 1,
            "top_p": obj.get("top_p") if obj.get("top_p") is not None else 1,
            "frequency_penalty": obj.get("frequency_penalty"),
            "n": obj.get("n") if obj.get("n") is not None else 1,
            "stop": Stop.from_dict(obj["stop"]) if obj.get("stop") is not None else None,
            "response_format": ResponseFormat.from_dict(obj["response_format"]) if obj.get("response_format") is not None else None,
            "stream": obj.get("stream") if obj.get("stream") is not None else False,
            "tools": obj.get("tools"),
            "prompt": obj.get("prompt")
        })
        return _obj


