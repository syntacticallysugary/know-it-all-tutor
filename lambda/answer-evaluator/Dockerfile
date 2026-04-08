FROM public.ecr.aws/lambda/python:3.12

# Copy ONNX model and tokenizer files
COPY MNRL-Similarity/onnx_model/ /opt/ml/model/

# Install onnxruntime (CPU) and tokenizer deps - no torch needed
RUN pip install --no-cache-dir onnxruntime transformers

# Copy Lambda function
COPY lambda/answer-evaluator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda/answer-evaluator/lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD ["lambda_function.handler"]
