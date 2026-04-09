import json
import os
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from sklearn.metrics.pairwise import cosine_similarity

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
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

def _encode(texts):
    _load()
    enc = _tokenizer(texts, padding=True, truncation=True, max_length=128, return_tensors="np")
    outputs = _session.run(None, {
        "input_ids": enc["input_ids"].astype(np.int64),
        "attention_mask": enc["attention_mask"].astype(np.int64),
    })
    mask = enc["attention_mask"][:, :, np.newaxis].astype(np.float32)
    pooled = (outputs[0] * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1e-9)
    norms = np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-9)
    return pooled / norms

def _similarity(a, b):
    emb = _encode([a, b])
    return float(np.clip(cosine_similarity(emb[0:1], emb[1:2])[0][0], 0.0, 1.0))

def _feedback(score):
    if score >= 0.90: return "Excellent! Your answer matches the expected response."
    if score >= 0.80: return "Good answer, but could be more precise."
    if score >= 0.60: return "Partially correct. Review the key concepts."
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
            results = []
            for p in pairs:
                score = _similarity(p['answer'], p['correct_answer'])
                results.append({'similarity': round(score, 4), 'feedback': _feedback(score)})
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'results': results})
            }

        score = _similarity(body['answer'], body['correct_answer'])
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'similarity': round(score, 4), 'feedback': _feedback(score)})
        }

    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
