import gradio as gr
from langchain_core import messages
import base64
from graph import eatronAssistant

def isBase64(s):
    try:
        return base64.b64encode(base64.b64decode(s)) == s.encode()
    except:
        return False

# Main function to handle chat input
def invokeAgent(userInput, history, file):
    if userInput != "QUIT":
        try:
            response = eatronAssistant.invoke({
                "messages": [messages.HumanMessage(content=userInput)],
                "file": file.name
            })

            content = response['messages'][-1].content

            if isBase64(content):
                img_html = f'<img src="data:image/png;base64,{content}" width="300"/>'
                history.append((userInput, img_html))
            else:
                history.append((userInput, content))
        except Exception as error:
            history.append((userInput, f"Error arose while processing request: {error}"))
    else:
        raise gr.Error("Session ended by user.")
    
    return history, history

# Gradio Blocks UI
with gr.Blocks(title="Agent Chat") as demo:
    gr.Markdown("## Agent Chat")

    chatbot = gr.Chatbot(render_markdown=False)
    state = gr.State([])

    with gr.Row():
        fileInput = gr.File(label="Upload files")
    
    with gr.Row():
        msg = gr.Textbox(placeholder="Type your message here...", show_label=False)
        send_btn = gr.Button("Send")

    # Bind send button click
    send_btn.click(
        invokeAgent,
        inputs=[msg, state, fileInput],
        outputs=[chatbot, state]
    )

    # Also bind Enter key submission
    msg.submit(
        invokeAgent,
        inputs=[msg, state, fileInput],
        outputs=[chatbot, state]
    )

demo.launch(share=False)
