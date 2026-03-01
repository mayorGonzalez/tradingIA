import asyncio
import sys
import os

# Add root to sys.path
sys.path.append(os.getcwd())

from app.services.ai_analyst import AIAnalyst

def test():
    a = AIAnalyst()
    resp = a.ask_question("/buy BTC 100")
    print(f"RESPONSE_START: {resp} :RESPONSE_END")

if __name__ == "__main__":
    test()
