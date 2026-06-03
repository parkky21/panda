import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

def main():
    # Create a Bedrock Runtime client
    client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    model_id = 'moonshotai.kimi-k2.5'
    
    messages = [
        {"role": "user", "content": [{"text": "Hello, please reply with a short greeting."}]}
    ]
    
    print(f"Calling Bedrock model {model_id} via converse API...")
    try:
        response = client.converse(
            modelId=model_id,
            messages=messages
        )
        
        print("Success! Received response:")
        print(json.dumps(response['output'], indent=2))
        
    except Exception as e:
        print("Error calling Bedrock:")
        print(e)

if __name__ == "__main__":
    main()
