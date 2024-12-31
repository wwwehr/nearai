FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y gcc libffi-devel openssl-devel shadow-utils acl

# pass with --build-arg FRAMEWORK=-langgraph
ARG FRAMEWORK=""
ARG AGNER_RUNNER_USER="agent_runner"
ARG HUB_CONFIG_PATH="/opt/hub_config.env"

COPY nearai/aws_runner/frameworks/requirements${FRAMEWORK}.txt ${LAMBDA_TASK_ROOT}

RUN pip install -r requirements${FRAMEWORK}.txt

CMD /bin/sh -c "echo Setting agent runner user as $AGNER_RUNNER_USER"

RUN /usr/sbin/groupadd -r $AGNER_RUNNER_USER && \
    /usr/sbin/useradd -r -g $AGNER_RUNNER_USER -m $AGNER_RUNNER_USER

RUN mkdir -p /$AGNER_RUNNER_USER/.nearai/registry && \
    chown $AGNER_RUNNER_USER:$AGNER_RUNNER_USER /$AGNER_RUNNER_USER/.nearai/registry

COPY nearai/aws_runner/.env $HUB_CONFIG_PATH
RUN chown root:root $HUB_CONFIG_PATH && chmod 600 $HUB_CONFIG_PATH


RUN chown -R $AGNER_RUNNER_USER:$AGNER_RUNNER_USER /var/task

RUN setfacl -Rdm u:$AGNER_RUNNER_USER:rwx /tmp && \
    setfacl -Rm u:$AGNER_RUNNER_USER:rwx /tmp


RUN mkdir ${LAMBDA_TASK_ROOT}/nearai
COPY nearai ${LAMBDA_TASK_ROOT}/nearai

# USER lambda_user
CMD [ "nearai/aws_runner/service.handler" ]