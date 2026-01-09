import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import mcp.types as types

# Windows Fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=[r"C:\Users\LokeshSharma\Downloads\New folder\server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        print("✅ Connection Open")

        # Reference holder to access session inside handlers
        session_ref = {}

        # --- 1. THE LOGGING HANDLER (For console logs) ---
        async def handle_log(params: types.LoggingMessageNotificationParams):
            msg = getattr(params.data, 'msg', params.data)
            print(f"📨 Log [{params.level}]: {msg}")

        # --- 2. THE MESSAGE HANDLER (The Fix) ---
        # This catches ALL server messages. We filter for the one we want.
        async def handle_message(message):
                method = getattr(message,"method",None)
                # Check for the specific Resource Changed event
                print("message: ",message)
                if method == "notifications/resources/list_changed":
                    print("\n🔔 EVENT RECEIVED: Resource List Changed!")
                    
                    # Access the session to fetch the new list
                    current_session = session_ref.get("session")
                    if current_session:
                        print("🔄 Fetching new list of resources...")
                        resources = await current_session.list_resources()
                        
                        # Display the new resources
                        for res in resources.resources:
                            print(f"   📄 Found Resource: {res.name}")
                            print(f"      Uri: {res.uri}")

        # --- 3. INITIALIZE SESSION ---
        # USE 'message_handler' instead of 'notification_handler'
        async with ClientSession(
            read, 
            write, 
            logging_callback=handle_log,     # Use logging_callback (as per your version)
            message_handler=handle_message   # <--- THE FIX
        ) as session:
            
            # Store session for the handler to use
            session_ref["session"] = session
            
            await session.initialize()
            print("✅ Session Initialized")
            
            # --- 4. PROGRESS HANDLER ---
            async def handle_progress(progress: float, total: float | None, message: str | None):
                percent = int(progress * 100)
                print(f"⏳ Progress: {percent}% - {message}")

            print("Available Tools : ",await session.list_tools())
            print("🔄 Calling tool...\n")
            
            result = await session.call_tool(
                "process_pdf",
                arguments={
                    "pdf_path": r"C:\Users\LokeshSharma\Downloads\New folder\pdf_files\LokeshSharma_Resume .pdf"
                },
                progress_callback=handle_progress
            )
            
            print(f"\n✅ Final Result: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())