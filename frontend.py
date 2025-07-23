import gradio as gr
import os
from langchain_core import messages
import base64
from graph import eatronAssistant

server = None

def isBase64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s.encode()
    except:
        return False

# Main function to handle chat input
def invokeAgent(userInput, history, file):
    if userInput != "QUIT":
        try:
            if file:
                if not file.name.endswith(".csv"):
                    raise AttributeError("input file should end with .csv")
            try:
                response = eatronAssistant.invoke({
                "messages": [messages.HumanMessage(content=userInput)],
                "file": file.name
                 })
            except:
                response = eatronAssistant.invoke({
                "messages": [messages.HumanMessage(content=userInput)],
                "file": "" #for if no file was inputted
                 })
            
            if isinstance(response['messages'][-2], messages.HumanMessage): #meaning only plot/analyse/evaluation, not one of the former followed by the latter
                content = response['messages'][-1].content

                if isBase64(content):
                    img_html = f'<img src="data:image/png;base64,{content}" width="300"/>'
                    history.append((userInput, img_html))
                else:
                    history.append((userInput, content))
            else:
                imgContent = response['messages'][-2].content
                imgMarkdown = f'<img src="data:image/png;base64,{imgContent}" width="300"/>'
                textContent = response['messages'][-1].content
                totalContent = imgMarkdown + " " + textContent
                history.append((userInput, totalContent)) #adds to chat history
        except Exception as error:
            history.append((userInput, f"Error arose while processing request: {error}"))
    else:
        if server:
            server.close() #shuts down server
        os._exit(1) #stops code from running
        #I would recommend using os over sys here because sys only stops the subprocess, not the whole code
        
    
    return history, history

# Gradio Blocks UI
with gr.Blocks(title="Agent Chat") as demo:
    gr.Markdown("## Agent Chat - type QUIT to end the conversation")

    chatbot = gr.Chatbot(render_markdown=False)
    state = gr.State([])

    with gr.Row():
        fileInput = gr.File(label = " Upload a csv file ")
    
    with gr.Row():
        msgBox = gr.Textbox(placeholder = "Type your message here...", show_label = False)
        sendBtn = gr.Button("Send")

    # Bind send button click
    sendBtn.click(
        invokeAgent,
        inputs=[msgBox, state, fileInput],
        outputs=[chatbot, state]
    )

    # Also bind Enter key submission
    msgBox.submit(
        invokeAgent,
        inputs=[msgBox, state, fileInput],
        outputs=[chatbot, state]
    )

server = demo.launch(share = False)
