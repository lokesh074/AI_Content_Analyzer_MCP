import streamlit as st
import asyncio
import sys
import json
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
import tempfile

load_dotenv()

# -------------------------------------------------
# Windows Event Loop Fix
# -------------------------------------------------
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# -------------------------------------------------
# Configuration & Path Setup
# -------------------------------------------------
st.set_page_config(page_title="AI Content Analyzer", page_icon="🤖", layout="wide")

# DEFINE PATHS HERE - VALIDATE THEY EXIST
UV_PATH = r"C:\Users\LokeshSharma\AppData\Local\Programs\Python\Python312\Scripts\uv.exe"
SERVER_SCRIPT = r"C:\Users\LokeshSharma\Downloads\New folder\server.py"
PYTHON_PATH = r"C:\Users\LokeshSharma\AppData\Local\Programs\Python\Python312\python.exe"

# Validate paths immediately
if not os.path.exists(UV_PATH):
    st.error(f"❌ Error: 'uv.exe' not found at: {UV_PATH}")
    st.stop()
if not os.path.exists(SERVER_SCRIPT):
    st.error(f"❌ Error: Server script not found at: {SERVER_SCRIPT}")
    st.stop()

SERVERS = {
    "Analysis Tools": {
        "command": "python",
        "args": [SERVER_SCRIPT],
        "env": {}, 
        "transport": "stdio"
    }
}

# -------------------------------------------------
# State Management
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# New: Store a list of resources instead of a single one
if "resources" not in st.session_state:
    st.session_state.resources = [] 
    # Structure: [{'id': 0, 'type': 'pdf', 'name': 'filename', 'data': path/json}, ...]

if "active_resource_index" not in st.session_state:
    st.session_state.active_resource_index = None

# -------------------------------------------------
# Logic
# -------------------------------------------------

@st.cache_resource
def get_llm_model():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found in .env")
        st.stop()
    return ChatGroq(
        model_name="qwen/qwen3-32b",
        temperature=0.0,
        api_key=api_key
    )

async def call_specific_tool(tool_name: str, tool_args: dict):
    """Call a specific MCP tool using async context manager"""
    try:
        client = MultiServerMCPClient(SERVERS)
        tools = await client.get_tools()
        named_tools = {tool.name: tool for tool in tools}
        
        if tool_name in named_tools:
            try:
                result = await named_tools[tool_name].ainvoke(tool_args)
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('text', str(result))
                elif hasattr(result, 'content'):
                    return result.content
                return str(result)
            except Exception as e:
                return f"Error executing {tool_name}: {str(e)}"
        else:
            return f"Tool '{tool_name}' not found. Available: {list(named_tools.keys())}"
    except Exception as e:
        return f"Connection Error: {str(e)}"

async def run_chat_with_tools(user_input, context=None):
    """Run chat with intelligent tool selection"""
    status = st.status("⚙️ Processing your request...", expanded=True)
    
    try:
        client = MultiServerMCPClient(SERVERS)
        try:
            tools = await client.get_tools()
        except Exception as e:
            status.update(label="❌ Connection Failed", state="error")
            return f"Could not connect to MCP Server. Check your paths.\nError: {e}"
        
        named_tools = {tool.name: tool for tool in tools}
        status.write(f"✅ Available Tools: {list(named_tools.keys())}")
        
        llm = get_llm_model()
        llm_with_tools = llm.bind_tools(tools)
        
        # System Prompt
        system_content = (
            "You are a helpful assistant with access to specialized tools. "
            "IMPORTANT RULES:\n"
            "1. If user asks for TRANSCRIPT, ONLY call 'get_youtube_transcript' tool\n"
            "2. If user asks for SUMMARY, ONLY call 'youtube_summary' tool\n"
            "3. If user asks about PDF content or questions, call 'pdf_qa' tool\n"
            "4. If user asks to VIEW FULL CONTENT or a specific page content, call 'extract_pdf_text' tool\n"
            "5. Always use the user's original input for tool arguments."
        )
        # st.write(context)
        
        if context:
            system_content += f"\n\nACTIVE RESOURCE CONTEXT:\n{context}"
        else:
            system_content += "\n\nCONTEXT: No specific resource selected. Answer generally."
        
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_input)
        ]
        
        status.write("🤔 AI is analyzing your request...")
        response = await llm_with_tools.ainvoke(messages)
        
        if not getattr(response, "tool_calls", None):
            status.update(label="✅ Response Ready", state="complete", expanded=False)
            return response.content
        
        tool_outputs = []
        status.write(f"🛠️ Calling {len(response.tool_calls)} tool(s)")
        
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            status.write(f"▶️ Executing: **{tool_name}** with Args:**{tool_args}**")
            
            if tool_name in named_tools:
                try:
                    result = await named_tools[tool_name].ainvoke(tool_args)
                    if isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'get'):
                        text_res = result[0].get('text', str(result))
                    elif hasattr(result, 'content'):
                         text_res = result.content
                    else:
                        text_res = str(result)
                except Exception as tool_err:
                    text_res = f"Tool Execution Error: {tool_err}"
                tool_outputs.append(f"### 🔧 {tool_name}\n\n{text_res}")
            else:
                tool_outputs.append(f"❌ Tool '{tool_name}' not found")
        
        status.update(label="✅ Complete", state="complete", expanded=False)
        return "\n\n---\n\n".join(tool_outputs)

    except Exception as e:
        status.update(label="❌ Critical Error", state="error", expanded=True)
        return f"⚠️ System Error: {str(e)}"

# -------------------------------------------------
# UI Layout
# -------------------------------------------------
st.title("🤖 AI Content Analyzer")

# Sidebar - Resource Management
with st.sidebar:
    st.header("🗂️ Resource Manager")
    
    # 1. Add New Resource Section
    with st.expander("➕ Add New Resource", expanded=True):
        resource_type = st.selectbox(
            "Type",
            ["📄 PDF Document", "🎥 YouTube Video", "🌐 Website URL"]
        )
        
        if resource_type == "📄 PDF Document":
            uploaded_file = st.file_uploader("Upload PDF", type=['pdf'])
            if uploaded_file and st.button("Process PDF", type="primary"):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                with st.spinner("Processing PDF..."):
                    # Call process_pdf tool to get JSON metadata
                    result = asyncio.run(call_specific_tool("process_pdf", {"pdf_path": tmp_path}))
                    
                    try:
                        if isinstance(result, dict):
                             result_data = result
                        else:
                             result_data = json.loads(result)
                        
                        if "error" not in result_data:
                            # Store the processed JSON and path
                            st.session_state.resources.append({
                                "id": len(st.session_state.resources),
                                "type": "pdf",
                                "name": uploaded_file.name,
                                "path": tmp_path,
                                "metadata": result_data # Storing the JSON here
                            })
                            st.success("PDF added to resources!")
                        else:
                            st.error(result_data['error'])
                    except Exception as e:
                        # Fallback
                        st.session_state.resources.append({
                            "id": len(st.session_state.resources),
                            "type": "pdf",
                            "name": uploaded_file.name,
                            "path": tmp_path,
                            "metadata": {"raw_output": str(result)}
                        })
                        st.success("PDF added (Raw Mode)")

        elif resource_type == "🎥 YouTube Video":
            video_url = st.text_input("Enter YouTube URL:")
            if video_url and st.button("Add Video", type="primary"):
                st.session_state.resources.append({
                    "id": len(st.session_state.resources),
                    "type": "youtube",
                    "name": f"Video ({video_url[:30]}...)",
                    "url": video_url
                })
                st.success("Video added to resources!")

        elif resource_type == "🌐 Website URL":
            web_url = st.text_input("Enter Website URL:")
            if web_url and st.button("Add Website", type="primary"):
                with st.spinner("Scraping..."):
                    result = asyncio.run(call_specific_tool("scrape_web_url", {"url": web_url}))
                    if isinstance(result, dict):
                        result_data = result
                    else:
                        result_data = json.loads(result)

                st.write(result_data)
                st.session_state.resources.append({
                    "id": len(st.session_state.resources),
                    "type": "website",
                    "name": f"Web ({web_url[:30]}...)",
                    "url": web_url,
                    "metadata":result_data
                })
                st.success("Website added to resources!")

    st.divider()

    # 2. Select Active Resource Section
    st.subheader("📝 Active Resource")
    
    resource_options = ["🚫 None (General Chat)"] + [f"{r['type'].upper()}: {r['name']}" for r in st.session_state.resources]
    
    # Logic to map selection back to index
    selected_option = st.radio("Select context for AI:", resource_options)
    
    if selected_option == "🚫 None (General Chat)":
        st.session_state.active_resource_index = None
    else:
        # Find index based on selection string
        index = resource_options.index(selected_option) - 1 # -1 because of "None" option
        st.session_state.active_resource_index = index

    # Show details of selected resource
    if st.session_state.active_resource_index is not None:
        active_res = st.session_state.resources[st.session_state.active_resource_index]
        st.info(f"Context set to: {active_res['type']}")
        
        # PDF Specific Quick View Button
        if active_res['type'] == 'pdf':
            if st.button("📖 View Full Content"):
                 res = asyncio.run(call_specific_tool("extract_pdf_text", {
                        "pdf_path": active_res['path'], 
                        "page_numbers": "all"
                    }))
                 st.text_area("Content", res, height=200)


    if st.button("🗑️ Clear All Resources"):
        st.session_state.resources = []
        st.session_state.active_resource_index = None
        st.session_state.messages = []
        st.rerun()

# -------------------------------------------------
# Chat Area
# -------------------------------------------------
st.subheader("💬 Chat")

# Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input - No longer blocked by missing resource
if prompt := st.chat_input("Ask a question..."):
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Build Context based on Active Resource
    context = ""
    if st.session_state.active_resource_index is not None:
        res = st.session_state.resources[st.session_state.active_resource_index]
        
        if res['type'] == 'youtube':
            context = f"Resource Type: YouTube Video\nURL: {res['url']}\nInstruction: Use tools to get transcript/summary for this URL."
        elif res['type'] == 'website':
            context = f"Resource Type: Website\nURL: {res['metadata']}\nInstruction: Use web tools to analyze this URL."
        elif res['type'] == 'pdf':
            # Pass the path AND the stored JSON metadata
            context = f"Resource Type: PDF\nPath: {res['path']}\nMetadata (JSON): {res['metadata']}\nInstruction: Use pdf tools to answer user query"
    else:
        context = None # General chat
        
    with st.chat_message("assistant"):
        response_text = asyncio.run(run_chat_with_tools(prompt, context))
        st.markdown(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})