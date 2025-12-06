#!/usr/bin/env python3
"""
Test script for HuggingFace Hub authentication.
Usage: python test.py
Set HF_TOKEN environment variable before running.
"""

import os
import sys
from dotenv import load_dotenv
from huggingface_hub import HfApi, login

load_dotenv()

def test_hf_login():
    """Test HuggingFace Hub login with provided token."""
    
    # Get token from environment
    hf_token = os.getenv("HF_TOKEN")
    
    if not hf_token:
        print("❌ Error: HF_TOKEN environment variable not set")
        print("Usage: HF_TOKEN='your_token_here' python test.py")
        sys.exit(1)
    
    print("🔐 Testing HuggingFace Hub authentication...")
    print(f"Token length: {len(hf_token)} characters")
    
    try:
        # Attempt login
        login(token=hf_token, add_to_git_credential=False)
        print("✅ Login successful!")
        
        # Test API access
        api = HfApi()
        user_info = api.whoami(token=hf_token)
        
        print("\n📋 User Information:")
        print(f"  Username: {user_info.get('name', 'N/A')}")
        print(f"  Email: {user_info.get('email', 'N/A')}")
        print(f"  Account Type: {user_info.get('type', 'N/A')}")
        
        # Test gated model access (optional)
        print("\n🔍 Testing gated model access (EmbeddingGemma)...")
        try:
            model_info = api.model_info("google/embeddinggemma-300m", token=hf_token)
            print(f"✅ Access granted to gated model: {model_info.modelId}")
        except Exception as e:
            print(f"⚠️  Cannot access gated model: {str(e)}")
            print("   (You may need to accept the model's license agreement)")
        
        print("\n✨ Authentication test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Verify your token at https://huggingface.co/settings/tokens")
        print("2. Ensure token has 'read' permissions")
        print("3. For gated models, accept the license agreement on the model page")
        return False


if __name__ == "__main__":
    success = test_hf_login()
    sys.exit(0 if success else 1)
