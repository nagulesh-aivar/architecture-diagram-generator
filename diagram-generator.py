from dotenv import load_dotenv
import os

# Load AWS credentials from .env if needed
load_dotenv()

from mcp import stdio_client, StdioServerParameters
from strands import Agent
from strands.tools.mcp import MCPClient

def main():
    mcp_client = MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["awslabs.aws-diagram-mcp-server"]
        )
    ))

    with mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = Agent(tools=tools)
        print("Welcome to the AWS Architecture Diagram Chatbot!")
        print("Type your architecture prompt (or 'exit' to quit):")
        while True:
            user_prompt = input("You: ")
            if user_prompt.strip().lower() == "exit":
                print("Goodbye!")
                break
            # Add instructions for code and diagram output
            full_prompt = (
                f"{user_prompt} Show the Python code and save the diagram in "
                "your path here."
            )
            try:
                response = agent(full_prompt)
                print("\n--- Response ---")
                print(response)
                print("\n----------------\n")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()