
#import necessary modules
from typing import Annotated, Sequence, Any
from typing_extensions import TypedDict
from langchain_core import messages
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
import pandas
import PIL




#import necessary files
from graphUtils import systemPrompts
from graphUtils.tools import *


#setup API key and the large language model
llm = ChatOpenAI(model = "gpt-4o", temperature = 0.1)

class llmAgent(TypedDict): #stores internal data to be used throughout the Graph
    messages: Annotated[Sequence[messages.BaseMessage], add_messages]
    file: str
    df: Any #allows for unique data types such as pandas dataframes to be passed on

def clearNode(state:llmAgent) -> llmAgent:
    state['messages'] = []
    return state

def trimNode(state: llmAgent) -> llmAgent:
    """Removes least recent messages after the chat history reaches a certain size"""
    state['messages'] = state['messages'][4:]
    return state

def initialRouter(state: llmAgent) -> llmAgent:
    lastMessage = state['messages'][-1].content
    if lastMessage == "Code White":
        return "clearEdge"
    elif state['file'] == "":
        return "evaluateEdge"
    else:
        return "loadEdge"

def trimRouter(state: llmAgent) -> llmAgent: #to check if chat history is too long
    if len(state['messages']) > 15:
        return "trimEdge"
    else:
        return "endEdge"
    
def agentRouter(state: llmAgent) -> llmAgent: #decides if this prompt is for the plotting agent or the analysing agent
    wholePrompt = state['messages'][-1].content
    try:
        wholePrompt = wholePrompt.split("|||")
        return "plotEdge"
    except:
        return "evaluateEdge"
    
def evaluationRouter(state: llmAgent) -> llmAgent:
    lastMsg = state['messages'][-1]
    if not lastMsg.tool_calls:
        return "routerEdge"
    else:
        return "toolEdge"
    
def loadData(state:llmAgent) -> llmAgent:
    """Used to load data from a saved file and use it to create a pandas dataframe"""
    state['df'] = pandas.read_csv(state['file']) #loads the input file into the code
    return state

def promptAgent(state: llmAgent) -> llmAgent:
    systemPrompt = messages.SystemMessage(content = systemPrompts.promptAgentPrompt)
    columnList = state['df'].columns
    response = llm.invoke([systemPrompt] + state['messages'] + [f' | List of columns: {str(columnList)} |']) #inserts system prompt followed by input message
    state['messages'][-1] = messages.HumanMessage(content = response.content)
    return state

def plotAgent(state:llmAgent) -> llmAgent:
    wholePrompt = state['messages'][-1].content
    wholePrompt = wholePrompt.split("|||")
    currentPlotInstruction = messages.HumanMessage(wholePrompt[0])
    systemPrompt = messages.SystemMessage(content = systemPrompts.plotAgentPrompt)
    plottingTools = [plotDataWrapper(state['df']), displayDistributionWrapper(state['df']), 
                     checkMaxCorrelationWrapper(state['df']), checkMinCorrelationWrapper(state['df']), 
                     checkForAnomaliesWrapper(state['df']), filterColumnsWrapper(state['df']),
                     checkNANStatsWrapper(state['df']), returnDescriptionWrapper(state['df'])]
    plotllm = llm.bind_tools(plottingTools)
    response = plotllm.invoke([systemPrompt, currentPlotInstruction])
    if hasattr(response, 'tool_calls') and response.tool_calls:
        # Add tool execution logic here
        toolResults = []
        for toolCall in response.tool_calls:
            tool = next(t for t in plottingTools if t.name == toolCall['name'])
            result = messages.AIMessage(content = tool.invoke(toolCall['args']))
            toolResults.append(result)
        try:
            PIL.Image.open(toolResults[-1].content)
            state['messages'][-1] = messages.HumanMessage(content = [{"type": "text", "text": wholePrompt[1]}, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{toolResults[-1].content}"}}])
        except Exception as e:
            print(e)
        state['messages'] = state['messages'] + toolResults
    else:
        state['messages'].append(messages.AIMessage("No plotting tools were called"))
    return state

def evaluateAgent(state: llmAgent) -> llmAgent: #needs tools to access the previous agents' data
    systemPrompt = messages.SystemMessage(content = systemPrompts.evaluateAgentPrompt)
    response = llm.invoke([systemPrompt] + state['messages'])
    state['messages'] = state['messages'] + [response]
    return state

#adding all the nodes in the langgraph
agentGraph = StateGraph(llmAgent)
agentGraph.add_node("clearNode", clearNode)
agentGraph.add_node("loadData", loadData)
agentGraph.add_node("promptAgent", promptAgent)
agentGraph.add_node("plotAgent", plotAgent)
agentGraph.add_node("evaluateAgent", evaluateAgent)
agentGraph.add_node("trimNode", trimNode)

#adding the edges needed for travel between nodes
agentGraph.add_conditional_edges(START, initialRouter, {"loadEdge": "loadData", "evaluateEdge": "evaluateAgent", "clearEdge": "clearNode"})
agentGraph.add_edge("clearNode", END)
agentGraph.add_edge("loadData", "promptAgent")
agentGraph.add_conditional_edges("promptAgent", agentRouter, {"plotEdge": "plotAgent", "evaluateEdge": "evaluateAgent"})
agentGraph.add_edge("plotAgent", "evaluateAgent")
agentGraph.add_conditional_edges("evaluateAgent", trimRouter, {"trimEdge": "trimNode", "endEdge": END})
agentGraph.add_edge("trimNode", END)

eatronAssistant = agentGraph.compile()
