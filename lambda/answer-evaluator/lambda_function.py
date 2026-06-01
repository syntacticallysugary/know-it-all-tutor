import json
import os
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_PATH = os.environ.get('MODEL_PATH', '/opt/ml/model')

# Loaded once per container
_session = None
_tokenizer = None

def _load():
    global _session, _tokenizer
    if _session is None:
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        _session = ort.InferenceSession(os.path.join(MODEL_PATH, 'model.onnx'), sess_options=opts)
        tok = Tokenizer.from_file(os.path.join(MODEL_PATH, 'tokenizer.json'))
        tok.enable_padding()
        tok.enable_truncation(max_length=512)
        _tokenizer = tok

def _similarity(a, b):
    _load()
    encoded = _tokenizer.encode(a, b)
    enc = {
        "input_ids": np.array([encoded.ids], dtype=np.int64),
        "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
    }
    logits = _session.run(None, enc)[0][0]
    # Sigmoid then min-max normalize using empirical range from calibration set
    sig = float(1.0 / (1.0 + np.exp(-logits[0])))
    return float(np.clip((sig - 0.0347) / (0.1689 - 0.0347), 0.0, 1.0))

PASS_THRESHOLD = 0.45

def _feedback(score):
    if score >= PASS_THRESHOLD: return "Excellent! Your answer matches the expected response."
    return "Incorrect. Please review the material."

def handler(event, context):
    try:
        path = event.get('path', '')
        method = event.get('httpMethod', 'POST')

        if method == 'GET' and '/health' in path:
            _load()
            return {'statusCode': 200, 'body': json.dumps({'status': 'healthy'})}

        body = event.get('body', event)
        if isinstance(body, str):
            body = json.loads(body)

        if '/batch' in path or body.get('batch'):
            pairs = body.get('answer_pairs', [])
            if len(pairs) > 100:
                return {'statusCode': 400, 'body': json.dumps({'error': 'Batch size exceeds limit of 100'})}
            results = []
            for p in pairs:
                answer = str(p['answer'])[:5000]
                correct = str(p['correct_answer'])[:5000]
                score = _similarity(answer, correct)
                results.append({'similarity': round(score, 4), 'feedback': _feedback(score)})
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'results': results})
            }

        answer = str(body['answer'])[:5000]
        correct = str(body['correct_answer'])[:5000]
        score = _similarity(answer, correct)
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'similarity': round(score, 4), 'feedback': _feedback(score)})
        }

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
