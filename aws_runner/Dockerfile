FROM public.ecr.aws/docker/library/python:3.12.0-slim-bullseye
# enable streaming responses
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""

WORKDIR /aws_runner
COPY aws_runner/frameworks/requirements${FRAMEWORK}.txt /aws_runner

RUN pip install -r requirements${FRAMEWORK}.txt

RUN mkdir /aws_runner/nearai
COPY aws_runner/service.py /aws_runner/
COPY aws_runner/partial_near_client.py /aws_runner/aws_runner/
COPY nearai/agents /aws_runner/nearai/agents
COPY openapi_client /aws_runner/openapi_client
COPY shared /aws_runner/shared

CMD ["python", "/aws_runner/service.py" ]
