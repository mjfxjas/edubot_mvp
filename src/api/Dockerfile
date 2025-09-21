FROM public.ecr.aws/lambda/python:3.12

# libs
COPY src/api/requirements.txt .
RUN python -m pip install -r requirements.txt -t /opt/python

# code
COPY src/api/handler.py ${LAMBDA_TASK_ROOT}

# handler
CMD ["handler.lambda_handler"]
