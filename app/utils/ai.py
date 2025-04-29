import os
import logging
from typing import List
from openai import AsyncOpenAI
from app.dto.video_story import ImagePrompt
from app.utils.config import PROMPT_CONFIG

logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

async def generate_image_prompts(text: str, num_prompts: int) -> List[ImagePrompt]:
    """Generate image prompts from a story text using OpenAI"""
    try:
        logger.info(f"Generating {num_prompts} image prompts from text: {text[:100]}...")
        
        # Get prompt templates from config
        system_prompt = PROMPT_CONFIG.get("image_prompts", {}).get("system_prompt", "")
        user_prompt_template = PROMPT_CONFIG.get("image_prompts", {}).get("user_prompt_template", "")
        
        # Format user prompt with actual values
        user_prompt = user_prompt_template.format(
            num_prompts=num_prompts,
            text=text
        )
        
        # Get negative prompt from config
        default_negative_prompt = PROMPT_CONFIG.get("video_gen", {}).get(
            "default_negative_prompt", 
            "Overexposure, static, blurred details, subtitles, paintings, pictures, still, overall gray, worst quality"
        )
        
        # Call OpenAI to generate prompts
        response = await client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract prompts from response
        generated_text = response.choices[0].message.content
        prompt_lines = [line.strip() for line in generated_text.split('\n') if line.strip()]
        
        logger.info(f"Generated {len(prompt_lines)} image prompts")
        if len(prompt_lines) < num_prompts:
            logger.warning(f"Requested {num_prompts} prompts but only got {len(prompt_lines)}")
        
        # Convert to ImagePrompt objects
        image_prompts = []
        for i, prompt in enumerate(prompt_lines):
            if i >= num_prompts:  # Ensure we don't exceed the requested number
                break
                
            image_prompts.append(ImagePrompt(
                prompt=prompt,
                negative_prompt=default_negative_prompt,
                index=i
            ))
        
        # If we didn't get enough prompts, duplicate the last one to reach the requested count
        while len(image_prompts) < num_prompts:
            last_prompt = image_prompts[-1] if image_prompts else ImagePrompt(
                prompt="A cinematic scene with dramatic lighting",
                negative_prompt=default_negative_prompt,
                index=0
            )
            
            image_prompts.append(ImagePrompt(
                prompt=last_prompt.prompt,
                negative_prompt=last_prompt.negative_prompt,
                index=len(image_prompts)
            ))
        
        return image_prompts
    except Exception as e:
        logger.error(f"Error generating image prompts: {str(e)}")
        raise Exception(f"Failed to generate image prompts: {str(e)}")

async def generate_image(prompt: str) -> bytes:
    """Generate an image from a prompt using OpenAI DALL-E"""
    try:
        # Enhance prompt with quality terms from config
        image_quality_prompt = PROMPT_CONFIG.get("video_gen", {}).get(
            "image_quality_prompt", 
            "High quality, cinematic, detailed"
        )
        
        enhanced_prompt = f"{prompt}. {image_quality_prompt}"
        logger.info(f"Generating image for prompt: {enhanced_prompt[:100]}...")
        
        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            n=1,
            size="1024x1024",
            response_format="b64_json"
        )
        
        # Get image data
        image_data = response.data[0].b64_json
        import base64
        image_bytes = base64.b64decode(image_data)
        
        logger.info(f"Successfully generated image, size: {len(image_bytes)} bytes")
        return image_bytes
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        raise Exception(f"Failed to generate image: {str(e)}") 