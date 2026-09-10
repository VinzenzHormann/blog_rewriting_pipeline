import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

def call_claude_api(prompt_text: str) -> str:
    """
    Sends the generated prompt to Claude 3.5 Sonnet and returns the raw response text.
    """
    # Initialize the client (automatically uses os.environ["ANTHROPIC_API_KEY"])
    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt_text}
        ]
    )
    
    text_blocks = [
            block.text for block in message.content 
            if getattr(block, "type", None) == "text" or hasattr(block, "text")
        ]
        
    if not text_blocks:
        raise ValueError("No text content returned from API response.")
            
    return "\n".join(text_blocks).strip()