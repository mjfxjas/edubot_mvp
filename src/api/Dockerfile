# Lambda Python base
FROM public.ecr.aws/lambda/python:3.12

# Install deps into /opt/python (Lambda layer path)
COPY src/api/requirements.txt .
RUN python -m pip install -r requirements.txt -t /opt/python

# Copy your app code (handler + any helpers in src/api)
COPY src/api/ /var/task/

# ---- runtime env (override in Lambda config) ----
ENV BOOK_ID=philosophy \
    INDEX_PREFIX=indexes/philosophy/sections/ \
    TOP_K=5 \
    MAX_SECTIONS=200 \
    VERSION=v0.2-sprint2

# Lambda entrypoint: module.function
CMD ["handler.lambda_handler"]
