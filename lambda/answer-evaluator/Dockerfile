FROM python:3.12-slim

# Lambda runtime interface client
RUN pip install --no-cache-dir awslambdaric

# Copy ONNX model and tokenizer files
COPY stsb-cross-encoder-onnx-q8/ /opt/ml/model/

# Install onnxruntime and tokenizer deps - no torch needed
RUN pip install --no-cache-dir onnxruntime tokenizers

# Copy Lambda function
COPY lambda/answer-evaluator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda/answer-evaluator/lambda_function.py /var/task/

ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["lambda_function.handler"]
