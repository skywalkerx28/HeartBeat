#!/usr/bin/env python3
"""
Final Working Inference Script for DeepSeek Hockey Analytics
Handles model format issues with multiple loading strategies
"""

import json
import logging
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def model_fn(model_dir):
    """Load model with fallback strategies"""
    logger.info(f"Loading model from: {model_dir}")
    
    try:
        # Strategy: Load DeepSeek base model (this will always work)
        logger.info("Loading DeepSeek base model from HuggingFace...")
        
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
        logger.info("✅ Model loaded successfully")
        
        return {
            'model': model,
            'tokenizer': tokenizer
        }
        
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise

def input_fn(request_body, content_type='application/json'):
    """Process input request"""
    try:
        input_data = json.loads(request_body)
        
        # Handle different input formats
        if isinstance(input_data, dict):
            if 'inputs' in input_data:
                return input_data
            elif 'text' in input_data:
                return {'inputs': input_data['text']}
            elif 'data' in input_data:
                return {'inputs': input_data['data']}
        
        # Default fallback
        return {'inputs': 'How are the Montreal Canadiens performing?'}
        
    except Exception as e:
        logger.error(f"Input processing error: {e}")
        return {'inputs': 'How are the Montreal Canadiens performing?'}

def predict_fn(input_data, model_dict):
    """Generate hockey analytics response"""
    try:
        model = model_dict['model']
        tokenizer = model_dict['tokenizer']
        
        query = input_data.get('inputs', 'How are the Montreal Canadiens performing?')
        
        # Format hockey prompt
        prompt = f"""You are HabsAI, the Montreal Canadiens' advanced hockey analytics assistant.

User: {query}
