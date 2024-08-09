import inspect
from typing import Annotated

from fastapi import Form


# Code from: https://stackoverflow.com/a/77113651/4950797
def as_form(cls):
    new_params = []

    for field_name, model_field in cls.model_fields.items():
        annotations = [*model_field.metadata, Form()]

        new_params.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.POSITIONAL_ONLY,
                default=model_field.default,
                annotation=Annotated[model_field.annotation, *annotations],  # type: ignore
            )
        )

    cls.__signature__ = cls.__signature__.replace(parameters=new_params)

    return cls
