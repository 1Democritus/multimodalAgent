#import necessary modules
from typing import Annotated, Sequence, Any
from typing_extensions import TypedDict
from langchain_core import messages
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
import pandas
from dotenv import load_dotenv



#import necessary files
import systemPrompts
from tools import *

#setup API key and the large language model
load_dotenv() #loads in API key from environment
llm = ChatOpenAI(model = "gpt-4o", temperature = 0)
llm.bind_tools([convertImage])

class llmAgent(TypedDict): #stores internal data to be used throughout the Graph
    messages: Annotated[Sequence[messages.BaseMessage], add_messages]
    file: str
    df: Any #allows for unique data types such as pandas dataframes to be passed on

def clearNode(state:llmAgent) -> llmAgent:
    state['messages'] = ''
    return state

def trimNode(state: llmAgent) -> llmAgent:
    """Removes least recent messages after the chat history reaches a certain size"""
    state['messages'] = state['messages'][4:]
    return state

def initialRouter(state: llmAgent) -> llmAgent:
    lastMessage = state['messages'][-1].content
    if lastMessage == "Code White":
        return "clearEdge"
    elif state['file'] == "" or lastMessage[0] =="E":
        return "evaluateEdge"
    else:
        return "loadEdge"

def trimRouter(state: llmAgent) -> llmAgent: #to check if chat history is too long
    if len(state['messages']) > 15:
        return "trimEdge"
    else:
        return "endEdge"
    
def agentRouter(state: llmAgent) -> llmAgent: #decides if this prompt is for the plotting agent or the analysing agent
    key = state['messages'][-1].content[0]
    if key == "P":
        return "plotEdge"
    elif key == "A":
        return "analyzeEdge"
    elif key == "E":
        return "evaluateEdge"
    else:
        raise ValueError("Prompt doesn't have A or P at start like it should")
    
def agentRouterTwo(state: llmAgent) -> llmAgent:
    key = state['messages'][-2].content[1]
    if key == "E":
        return "evaluateEdge"
    else:
        return "routerEdge"
    
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
    response = llm.invoke([systemPrompt] + state['messages']) #inserts system prompt followed by input message
    state['messages'][-1] = messages.HumanMessage(content = response.content)
    return state

def analyticsAgent(state: llmAgent) -> llmAgent:
    systemPrompt = messages.SystemMessage(content = systemPrompts.analyticAgentPrompt)
    analyticTools = [checkMaxCorrelationWrapper(state['df']), checkMinCorrelationWrapper(state['df']), 
                     checkForAnomaliesWrapper(state['df']), filterColumnsWrapper(state['df']),
                     checkNANStatsWrapper(state['df']), returnDescriptionWrapper(state['df'])]
    analysellm = llm.bind_tools(analyticTools) #now the llm can use them
    response = analysellm.invoke([systemPrompt] + state['messages'])

    if hasattr(response, 'tool_calls') and response.tool_calls: 
    #checked for tools inside the agent because if i bind them to a tool node externall they can't access input files
        # Add tool execution logic here
        toolResults = []
        for toolCall in response.tool_calls:
            tool = next(t for t in analyticTools if t.name == toolCall['name'])
            result = messages.AIMessage(tool.invoke(toolCall['args']))
            toolResults.append(result)
        #state['messages'].append(messages.AIMessage(toolResults[0]))
        state['messages'] = state['messages'] + toolResults
    else:
        state['messages'] = state['messages'] + [response]
    return state

def plotAgent(state:llmAgent) -> llmAgent:
    systemPrompt = messages.SystemMessage(content = systemPrompts.plotAgentPrompt)
    plottingTools = [plotDataWrapper(state['df']), displayDataWrapper(), displayDistributionWrapper(state['df'])]
    plotllm = llm.bind_tools(plottingTools)
    response = plotllm.invoke([systemPrompt] + state['messages'])

    if hasattr(response, 'tool_calls') and response.tool_calls:
        # Add tool execution logic here
        toolResults = []
        for toolCall in response.tool_calls:
            tool = next(t for t in plottingTools if t.name == toolCall['name'])
            result = messages.AIMessage(tool.invoke(toolCall['args']))
            toolResults.append(result)
        #state['messages'].append(messages.AIMessage(toolResults[0]))

        state['messages'] = state['messages'] + toolResults
    else:
        state['messages'] = state['messages'] + [response]
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
agentGraph.add_node("analyticAgent", analyticsAgent)
agentGraph.add_node("evaluateAgent", evaluateAgent)
evaluateTool = ToolNode(tools = [convertImage])
agentGraph.add_node("evaluateTool", evaluateTool)
agentGraph.add_node("router", lambda x: x)
agentGraph.add_node("trimNode", trimNode)

#adding the edges needed for travel between nodes
agentGraph.add_conditional_edges(START, initialRouter, {"loadEdge": "loadData", "evaluateEdge": "evaluateAgent", "clearEdge": "clearNode"})
agentGraph.add_edge("clearNode", END)
agentGraph.add_edge("loadData", "promptAgent")
agentGraph.add_conditional_edges("promptAgent", agentRouter, {"plotEdge": "plotAgent", "analyzeEdge": "analyticAgent", "evaluateEdge": "evaluateAgent"})
agentGraph.add_conditional_edges("plotAgent", agentRouterTwo, {"evaluateEdge": "evaluateAgent", "routerEdge": "router"})
agentGraph.add_conditional_edges("analyticAgent", agentRouterTwo, {"evaluateEdge": "evaluateAgent", "routerEdge": "router"})
agentGraph.add_conditional_edges("evaluateAgent", evaluationRouter, {"routerEdge": "router", "toolEdge": "evaluateTool"})
agentGraph.add_edge("evaluateTool", "evaluateAgent")
agentGraph.add_conditional_edges("router", trimRouter, {"trimEdge": "trimNode", "endEdge": END})
agentGraph.add_edge("trimNode", END)

eatronAssistant = agentGraph.compile()
