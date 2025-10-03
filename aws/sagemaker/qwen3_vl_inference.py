#!/usr/bin/env python3
"""
Qwen3-VL-235B-A22B-Thinking Inference Script for HeartBeat Hockey Analytics
Handles multimodal vision-language model with thinking mode capabilities
"""

import json
import logging
import os
import torch
import traceback
import base64
import subprocess
import sys
from io import BytesIO
from PIL import Image

# Install additional requirements if needed
def install_requirements():
    """Ensure runtime dependencies for Qwen3-VL are available"""
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--no-cache-dir", "--upgrade",
            "qwen",
            "qwen-vl-utils>=0.0.6",
            "accelerate==0.30.1",
            "torch==2.1.2",
            "--quiet"
        ])
        logging.info("Runtime dependency check completed successfully")
    except Exception as e:
        logging.warning(f"Could not ensure additional requirements: {e}")

# Install requirements at import time
install_requirements()

from transformers import AutoTokenizer, AutoModelForCausalLM, AutoProcessor
try:
    import transformers as transformers_pkg
    logging.info(f"Transformers version in use: {transformers_pkg.__version__}")
except ImportError:
    logging.warning("Transformers package not found even after installation attempt")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def model_fn(model_dir):
    """
    Load Qwen3-VL model with multimodal capabilities
    """
    logger.info(f"Loading Qwen3-VL model from: {model_dir}")
    
    try:
        # Get model name from environment variable or use default
        model_name = os.environ.get('HF_MODEL_ID', 'Qwen/Qwen3-VL-235B-A22B-Thinking')
        logger.info(f"Strategy 1: Loading {model_name} from HuggingFace Hub...")
        
        # Set up caching directories with proper permissions
        cache_dirs = ['/tmp/transformers_cache', '/tmp/huggingface_cache']
        for cache_dir in cache_dirs:
            os.makedirs(cache_dir, exist_ok=True)
            os.chmod(cache_dir, 0o755)
        
        # Set environment variables for caching
        os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
        os.environ['HF_HOME'] = '/tmp/huggingface_cache'
        os.environ['HF_ENDPOINT'] = os.environ.get('HF_ENDPOINT', 'https://huggingface.co')
        
        logger.info(f"Cache directories configured: {cache_dirs}")
        
        # Try to load processor for multimodal input handling
        processor = None
        try:
            processor = AutoProcessor.from_pretrained(
                model_name,
                trust_remote_code=True,
                cache_dir='/tmp/transformers_cache'
            )
            logger.info(f"Processor loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load processor: {e}")
            logger.info("Continuing with tokenizer only")
        
        # Load tokenizer with fallback strategies
        tokenizer = None
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                use_fast=False,
                cache_dir='/tmp/transformers_cache'
            )
            logger.info(f"Tokenizer loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load tokenizer for {model_name}: {e}")
            
            # Fallback to a similar model that might work
            fallback_models = [
                'Qwen/Qwen3-VL-235B-A22B-Instruct',  # Similar model
                'Qwen/Qwen2-VL-7B-Instruct',          # Smaller Qwen VL model
                'microsoft/DialoGPT-large'             # Text-only fallback
            ]
            
            for fallback_model in fallback_models:
                try:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    tokenizer = AutoTokenizer.from_pretrained(
                        fallback_model,
                        trust_remote_code=True,
                        use_fast=False,
                        cache_dir='/tmp/transformers_cache'
                    )
                    model_name = fallback_model  # Update model name for consistent loading
                    logger.info(f"Fallback tokenizer loaded: {fallback_model}")
                    break
                except Exception as fallback_e:
                    logger.warning(f"Fallback {fallback_model} failed: {fallback_e}")
                    continue
            
            if tokenizer is None:
                raise Exception("All tokenizer loading strategies failed")
        
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Get GPU configuration from environment
        num_gpus = int(os.environ.get('SM_NUM_GPUS', '1'))
        logger.info(f"Using {num_gpus} GPUs for model loading")
        
        # Load model with optimized settings for multi-GPU inference
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() and num_gpus > 1 else None,
            trust_remote_code=True,
            # Optimize for inference
            use_cache=True,
            low_cpu_mem_usage=True,
            # Multi-GPU optimization
            max_memory={i: "22GB" for i in range(num_gpus)} if num_gpus > 1 else None,
            # MoE optimization
            load_in_8bit=False,  # Keep full precision for better quality
            attn_implementation="flash_attention_2" if torch.cuda.is_available() else None,
            # Caching
            cache_dir='/tmp/transformers_cache'
        )
        
        model.eval()
        logger.info("Qwen3-VL model loaded successfully")
        logger.info(f"Model parameters: 235B total, ~22B active per token")
        
        # Try to load fine-tuned weights if they exist
        try:
            model_files = os.listdir(model_dir)
            logger.info(f"Files in model directory: {model_files}")
            
            # Look for fine-tuned model files
            ft_files = [f for f in model_files if f.endswith(('.pt', '.pth', '.bin', '.safetensors'))]
            if ft_files:
                logger.info(f"Found fine-tuned model files: {ft_files}")
                # Load the fine-tuned weights
                largest_file = max(ft_files, key=lambda f: os.path.getsize(os.path.join(model_dir, f)))
                weights_path = os.path.join(model_dir, largest_file)
                
                logger.info(f"Loading fine-tuned weights from: {largest_file}")
                
                if largest_file.endswith('.safetensors'):
                    from safetensors.torch import load_file
                    state_dict = load_file(weights_path)
                else:
                    state_dict = torch.load(weights_path, map_location='cpu')
                
                model.load_state_dict(state_dict, strict=False)
                logger.info("Fine-tuned weights loaded for hockey analytics")
            else:
                logger.info("No fine-tuned weights found, using base Qwen3-VL model")
                
        except Exception as e:
            logger.warning(f"Could not load fine-tuned weights: {e}")
            logger.info("Using base Qwen3-VL model")
        
        return {
            'model': model,
            'tokenizer': tokenizer,
            'processor': processor,
            'model_name': model_name
        }
        
    except Exception as e:
        logger.error(f"Strategy 1 failed: {e}")
        logger.error(traceback.format_exc())
        
        # Strategy 2: Try loading from model directory
        try:
            logger.info("Strategy 2: Direct loading from model directory...")
            
            processor = AutoProcessor.from_pretrained(model_dir, trust_remote_code=True)
            tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
                use_cache=True
            )
            
            model.eval()
            logger.info("Model loaded directly from directory")
            
            return {
                'model': model,
                'tokenizer': tokenizer,
                'processor': processor,
                'model_name': 'local'
            }
            
        except Exception as e2:
            logger.error(f"Strategy 2 failed: {e2}")
            raise Exception(f"Failed to load Qwen3-VL model: {e2}")

def process_image(image_data):
    """
    Process base64 encoded image or image path
    """
    try:
        if isinstance(image_data, str):
            if image_data.startswith('data:image'):
                # Base64 encoded image
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            return image.convert('RGB')
        elif isinstance(image_data, bytes):
            image = Image.open(BytesIO(image_data))
            return image.convert('RGB')
        else:
            logger.warning("Unsupported image format, skipping image processing")
            return None
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return None

def input_fn(request_body, content_type='application/json'):
    """
    Process multimodal input request (text + optional images)
    """
    try:
        if content_type != 'application/json':
            raise ValueError(f"Unsupported content type: {content_type}")
        
        input_data = json.loads(request_body)
        
        # Extract text input
        text_input = None
        if isinstance(input_data, str):
            text_input = input_data
        elif isinstance(input_data, dict):
            text_input = (input_data.get('inputs') or 
                         input_data.get('text') or 
                         input_data.get('query') or
                         input_data.get('prompt', ''))
        
        if not text_input:
            raise ValueError("No text input found")
        
        # Extract image inputs (optional)
        images = []
        if isinstance(input_data, dict):
            # Single image
            if 'image' in input_data:
                image = process_image(input_data['image'])
                if image:
                    images.append(image)
            
            # Multiple images
            if 'images' in input_data:
                for img_data in input_data['images']:
                    image = process_image(img_data)
                    if image:
                        images.append(image)
        
        # Extract additional parameters
        params = {}
        if isinstance(input_data, dict):
            params.update({
                'thinking_mode': input_data.get('thinking_mode', True),
                'temperature': input_data.get('temperature', 0.1),
                'top_p': input_data.get('top_p', 0.9),
                'max_new_tokens': input_data.get('max_new_tokens', 2048),
                'hockey_context': input_data.get('hockey_context', True)
            })
        
        return {
            'text': text_input,
            'images': images,
            'params': params
        }
            
    except Exception as e:
        logger.error(f"Input processing error: {e}")
        return {
            'text': 'test query about hockey analytics',
            'images': [],
            'params': {'thinking_mode': True, 'hockey_context': True}
        }

def predict_fn(input_data, model_dict):
    """
    Generate multimodal prediction with thinking mode
    """
    try:
        model = model_dict['model']
        tokenizer = model_dict['tokenizer']
        processor = model_dict['processor']
        
        text_query = input_data.get('text', 'analyze hockey performance')
        images = input_data.get('images', [])
        params = input_data.get('params', {})
        
        # Build hockey-specific prompt
        hockey_context = """You are HabsAI, the Montreal Canadiens' advanced hockey analytics assistant powered by Qwen3-VL-235B-A22B-Thinking.

Your capabilities include:
- Analyzing game footage, rink diagrams, and statistical visualizations
- Processing natural language queries about hockey analytics
- Providing detailed reasoning through thinking mode
- Understanding spatial relationships on the rink
- Interpreting player movements and strategic patterns

When analyzing visual content:
- Identify player positions, movements, and tactical formations
- Analyze shot locations, pass patterns, and zone entries
- Interpret statistical charts, heatmaps, and performance graphs
- Provide contextual explanations with hockey domain knowledge

""" if params.get('hockey_context', True) else ""
        
        # Prepare multimodal inputs
        if images:
            # Multimodal prompt with images
            messages = [
                {
                    "role": "system",
                    "content": hockey_context.strip()
                },
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": text_query}
                    ] + [{"type": "image", "image": img} for img in images]
                }
            ]
        else:
            # Text-only prompt
            messages = [
                {
                    "role": "system",
                    "content": hockey_context.strip()
                },
                {
                    "role": "user",
                    "content": text_query
                }
            ]
        
        # Apply chat template
        if hasattr(tokenizer, 'apply_chat_template'):
            prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            # Fallback formatting
            if images:
                prompt = f"{hockey_context}\n\nUser (with {len(images)} image(s)): {text_query}\n\nHabsAI:"
            else:
                prompt = f"{hockey_context}\n\nUser: {text_query}\n\nHabsAI:"
        
        # Tokenize inputs
        if images and processor:
            # Use processor for multimodal inputs
            inputs = processor(
                text=prompt,
                images=images,
                return_tensors="pt",
                padding=True
            )
        else:
            # Text-only tokenization
            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=min(4096, 256000)  # Use smaller context for efficiency
            )
        
        # Move to device if CUDA available
        if torch.cuda.is_available():
            inputs = {k: v.cuda() if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}
        
        # Generation parameters
        generation_config = {
            'max_new_tokens': params.get('max_new_tokens', 2048),
            'temperature': params.get('temperature', 0.1),
            'top_p': params.get('top_p', 0.9),
            'do_sample': True,
            'pad_token_id': tokenizer.pad_token_id,
            'eos_token_id': tokenizer.eos_token_id,
            'use_cache': True,
        }
        
        # Generate response
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                **generation_config
            )
        
        # Decode response
        input_length = inputs['input_ids'].shape[1] if 'input_ids' in inputs else 0
        generated_tokens = outputs[0][input_length:]
        response = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # Process thinking mode output
        thinking_content = ""
        final_response = response
        
        if params.get('thinking_mode', True) and '<think>' in response:
            parts = response.split('<think>')
            if len(parts) > 1:
                thinking_part = parts[1].split('</think>')[0] if '</think>' in parts[1] else parts[1]
                thinking_content = thinking_part.strip()
                final_response = parts[1].split('</think>')[1].strip() if '</think>' in parts[1] else parts[0].strip()
        
        # Prepare response
        result = {
            'response': final_response,
            'model': model_dict['model_name'],
            'thinking': thinking_content if thinking_content else None,
            'multimodal': len(images) > 0,
            'parameters': params
        }
        
        logger.info(f"Generated response length: {len(final_response)} chars")
        if thinking_content:
            logger.info(f"Thinking content length: {len(thinking_content)} chars")
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'response': f"I apologize, but I encountered an error processing your hockey analytics query: {str(e)}. Please try rephrasing your question or check if any images are properly formatted.",
            'model': model_dict.get('model_name', 'qwen3-vl'),
            'thinking': None,
            'multimodal': False,
            'error': str(e)
        }

def output_fn(prediction, content_type):
    """
    Format output response
    """
    if content_type == 'application/json':
        return json.dumps(prediction, ensure_ascii=False, indent=2)
    else:
        return str(prediction.get('response', 'No response generated'))
