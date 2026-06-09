import os
import json
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    load_dotenv()
    
    # 直接讀取我們在 .env 設定的 endpoint
    endpoint = os.getenv("PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    # 直接傳入 endpoint，不需要連接字串
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential()
    )
    
    # 獲取 OpenAI Client
    openai_client = project_client.get_openai_client()

    # (以下工具定義與對話邏輯保持不變)
    tools = [
        {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
        {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate cost.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
        {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate report.", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
    ]

    agent = openai_client.beta.assistants.create(
        model=deployment_name,
        name="astronomy-agent",
        instructions="You are an astronomy assistant.",
        tools=tools
    )
    
    thread = openai_client.beta.threads.create()
    
    print("Agent 已啟動！")
    # (後續迴圈邏輯...)
