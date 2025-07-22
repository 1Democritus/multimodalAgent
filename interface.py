import gradio as gr #needed for setting up interface
from langchain_core import messages
import io
from PIL import Image
import base64
from graph import eatronAssistant

def isBase64(s):
    try:
        # Attempt to decode and then re-encode and compare
        return base64.b64encode(base64.b64decode(s)) == s.encode()
    except:
        return False

def invokeAgent(userInput, history, file): #function used by the GUI to return output to input message
    if userInput != "QUIT":
        try:
            response = eatronAssistant.invoke({"messages": [messages.HumanMessage(content = userInput)], "file": file.name}) 
            print(response)
            print(response['messages'][-1])
            content = response['messages'][-1].content
            if isBase64(content):
                htmlImg = f"![image](data:image/png;base64, {content})"
                return htmlImg
            else:
                return content
        except Exception as error:
            return f"Error arose while processing request: {error}"
    else:
        raise gr.Error("Session ended by user.") #causes Interface to quit session by itself

fileInput = gr.File(label="Upload files") #so that it can also take files as input
demo = gr.ChatInterface(save_history=False , fn = invokeAgent, additional_inputs = fileInput,title ="Agent Chat", type="messages")
demo.saved_conversations.secret = "abcdefasd6200683922"
demo.launch(share = False)
