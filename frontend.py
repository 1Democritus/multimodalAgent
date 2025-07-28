import gradio as gr
import os
from langchain_core import messages
import base64
from dotenv import load_dotenv
load_dotenv(override = True) #loads in API key from environment
from graph import eatronAssistant

class Conversation:
    def __init__(self):
        self._history = []
    def storeHistory(self, history):
        self._history = history
    def getHistory(self):
        return self._history

server = None

def isBase64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s.encode()
    except:
        return False
    
def clearChat(): #clears chat as well as message history on internal files
    eatronAssistant.invoke({
        "messages": [messages.HumanMessage(content = "Code Black")],
        "file": ""
    })
    return [], []

# Main function to handle chat input
conversationStorage = Conversation()
def invokeAgent(userInput, history, file):
    msghist = conversationStorage.getHistory()
    if userInput != "QUIT":
        try:
            response = eatronAssistant.invoke({
            "messages": msghist + [messages.HumanMessage(content=userInput)],
            "file": file.name if file else ""
                })
            conversationStorage.storeHistory(response['messages'])
            
            if isinstance(response['messages'][-2], messages.HumanMessage): #meaning only plot/analyse/evaluation, not one of the former followed by the latter
                content = response['messages'][-1].content

                if isBase64(content):
                    img_html = f'<img src="data:image/png;base64,{content}" width="300"/>'
                    history.append((userInput, img_html))
                else:
                    history.append((userInput, content))
            else:
                dataContent = response['messages'][-2].content
                if isBase64(dataContent):
                    dataContent = f'<img src="data:image/png;base64,{dataContent}" width="300"/>'
                textContent = response['messages'][-1].content
                totalContent = dataContent + " " + textContent
                history.append((userInput, totalContent)) #adds to chat history
        except Exception as error:
            history.append((userInput, f"Error arose while processing request: {error}"))
    else:
        if server:
            server.close() #shuts down server
        os._exit(0) #stops code from running
        #I would recommend using os over sys here because sys only stops the subprocess, not the whole code
    return history, history

# Gradio Blocks UI
with gr.Blocks(title="Agent Chat") as demo:
    gr.Markdown("""# Eatron Agent
    Upload data csv and give your request;
    receive novel insights;
    to stop the process, enter QUIT
                """)

    chatbot = gr.Chatbot(render_markdown=False, height = 600)
    state = gr.State([])

    with gr.Row(equal_height = True):
        fileInput = gr.File(label = " Upload a csv file ", file_types = [".csv"], interactive = True)
    
    with gr.Row(equal_height = True):
        msgBox = gr.Textbox(placeholder = "Enter your request here", show_label = False)
        sendBtn = gr.Button("Send")
        clearBtn = gr.Button("Click here to clean chat")

    with gr.Row(): #displays ... while chatbot is processing
        status = gr.Markdown("")

    # Bind send button click
    sendBtn.click(
        invokeAgent,
        inputs=[msgBox, state, fileInput],
        outputs=[chatbot, state],
        show_progress = True
    )

    clearBtn.click(
        clearChat,
        inputs = [],
        outputs = [chatbot, state]
    )

    # Also bind Enter key submission
    msgBox.submit(
        invokeAgent,
        inputs=[msgBox, state, fileInput],
        outputs=[chatbot, state]
    )

server = demo.launch(share = False)
