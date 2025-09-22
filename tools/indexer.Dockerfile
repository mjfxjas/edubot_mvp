FROM public.ecr.aws/lambda/python:3.12

# deps for indexer
COPY tools/requirements-indexer.txt .
RUN python -m pip install -r requirements-indexer.txt

# app code
COPY tools/indexer.py /var/task/indexer.py
COPY tools/entrypoint.py /var/task/entrypoint.py

# IMPORTANT: override Lambda image's ENTRYPOINT so it doesn't expect a handler
ENTRYPOINT []

# run our script directly
CMD ["python", "/var/task/entrypoint.py"]
