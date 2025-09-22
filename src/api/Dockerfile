FROM public.ecr.aws/lambda/python:3.12


 COPY src/api/requirements.txt .
 RUN python -m pip install -r requirements.txt -t /opt/python

# copy your handler
COPY lambda/app/ask_handler.py ${LAMBDA_TASK_ROOT}

# env vars for the function
ENV CURRICULUM_BUCKET=edubot-mvp-147795258921-us-east-1-curriculum \
    BOOK_ID=philosophy \
    INDEX_PREFIX=indexes/philosophy/sections/ \
    TOP_K=5 \
    MAX_SECTIONS=200 \
    VERSION=v0.2-sprint2

# entrypoint: <module>.<function>

# copy code
COPY lambda/app/ask_handler.py /var/task

# entrypoint: <module>.<function>
CMD ["ask_handler.lambda_handler"]
