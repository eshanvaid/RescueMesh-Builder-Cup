#!/usr/bin/env python3
"""Real, small, awaited model-access probe. Prints no credentials."""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from rescuemesh.ai import client
from google.genai import types

async def main():
    c=client(); model=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
    try:
        async with asyncio.timeout(30):
            result=await c.aio.models.generate_content(model=model,contents='Reply only: synthetic prototype model access verified.',config=types.GenerateContentConfig(max_output_tokens=256,thinking_config=types.ThinkingConfig(thinking_level='LOW')))
            print({'project':os.getenv('GOOGLE_CLOUD_PROJECT'),'model':model,'actual_response':result.text})
    finally: await c.aio.aclose()
asyncio.run(main())
