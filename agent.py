import os
import json
import sys
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    # 1. 強制輸出緩衝，確保 print 內容能馬上看到
    sys.stdout.reconfigure(line_buffering=True)
    
    print("--- 程式開始啟動 ---")
    load_dotenv()
    
    endpoint = os.getenv("PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if not endpoint:
        print("致命錯誤: .env 檔案中找不到 PROJECT_ENDPOINT")
        return

    try:
        print(f"嘗試連接至: {endpoint}")
        project_client = AIProjectClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential()
        )
        
        print("成功建立 ProjectClient，正在取得 OpenAI Client...")
        openai_client = project_client.get_openai_client()

        tools = [
            {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
            {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate cost.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
            {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate report.", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
        ]

        print("正在註冊 Agent...")
        agent = openai_client.beta.assistants.create(
            model=deployment_name,
            name="astronomy-agent",
            instructions="You are an astronomy assistant.",
            tools=tools
        )
        
        thread = openai_client.beta.threads.create()
        print("--- Agent 已啟動！輸入 'quit' 結束 ---")

        while True:
            user_input = input("\nUSER: ").strip()
            if user_input.lower() == "quit": break

            openai_client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_input)
            run = openai_client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=agent.id)

            if run.status == 'requires_action':
                tool_outputs = []
                for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    result = None
                    if name == "next_visible_event": result = next_visible_event(**args)
                    elif name == "calculate_observation_cost": result = calculate_observation_cost(**args)
                    elif name == "generate_observation_report": result = generate_observation_report(**args)
                    
                    tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(result)})
                
                run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

            messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
            print(f"AGENT: {messages.data[0].content[0].text.value}")

    except Exception as e:
        print(f"\n[發生錯誤]: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
