#!/usr/bin/env python3
import json
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def model_fn(model_dir):
    logger.info("Loading DeepSeek base model...")
    
    tokenizer = AutoTokenizer.from_pretrained(
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
        trust_remote_code=True
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", 
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model.eval()
    logger.info("Model loaded successfully")
    
    return {'model': model, 'tokenizer': tokenizer}

def input_fn(request_body, content_type='application/json'):
    try:
        input_data = json.loads(request_body)
        if isinstance(input_data, dict) and 'inputs' in input_data:
            return input_data
        return {'inputs': 'How are the Montreal Canadiens performing?'}
    except:
        return {'inputs': 'How are the Montreal Canadiens performing?'}

def predict_fn(input_data, model_dict):
    model = model_dict['model']
    tokenizer = model_dict['tokenizer']
    
    query = input_data.get('inputs', 'Hockey question')
    prompt = f"You are HabsAI, Montreal Canadiens hockey assistant. User: {query} Assistant:"
    
    inputs = tokenizer(prompt, return_tensors="pt", max_length=1024, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extract only the new generated text
    response = response[len(prompt):].strip()
    
    return {'generated_text': response}

def output_fn(prediction, accept='application/json'):
    return json.dumps(prediction)
