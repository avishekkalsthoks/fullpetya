import os
from dotenv import load_dotenv
import sys

# Force utf-8 output if possible, otherwise just avoid special chars
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

print("Checking API Configuration...")

azure_endpoint = os.getenv('AZURE_VISION_ENDPOINT', '').strip()
azure_key = os.getenv('AZURE_VISION_KEY', '').strip()
openrouter_key = os.getenv('OPENROUTER_API_KEY', '').strip()

print(f"Azure Endpoint: {'[SET]' if azure_endpoint else '[MISSING]'}")
print(f"Azure Key:      {'[SET]' if azure_key else '[MISSING]'}")
print(f"OpenRouter Key: {'[SET]' if openrouter_key else '[MISSING]'}")

if not azure_endpoint and not azure_key and not openrouter_key:
    print("\nNo API keys are configured. You need to create a .env file with your keys.")
    print("You can copy .env.example to .env and fill in the values.")
else:
    print("\nAPI keys are present. Initializing AI Handler to test connection...")
    try:
        # Append logic to import handler and test if keys are valid
        # This requires the handler to be importable
        sys.path.append(os.getcwd())
        from handlers.ai_handler import AzureAIHandler
        
        try:
            handler = AzureAIHandler()
            if handler.openrouter_available:
                print("OpenRouter is configured in the handler.")
            if handler.vision_available:
                print("Azure Vision is configured in the handler.")
            print("Initialization successful.")
            
        except Exception as e:
            print(f"Handler initialization failed: {e}")

    except ImportError:
        print("Could not import handlers.ai_handler. Make sure you are in the project root.")
    except Exception as e:
        print(f"An error occurred: {e}")
