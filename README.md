# multimodalAgent

Building an agent which can take data from an input table, an perform actions required by employees: such as 
- Plotting two axes of data against each other
- Displaying the distribution of a column of data
- Displaying a row of anomalies for a column with a given z-score threshold
- return x columns with highest correlation with a column of the employee's choosing
- An evaluation agent, which can analyse previous plots and results
- And obviously, the ability to callback on previous prompts, like a normal conversation

Used langgraph for the internal agent structure, as it gives a clean, robust architecture to the relationship between different agents and their tools
Used gradio to build the chat interface, as it is flexible with usage



Omissions:
- Streaming the output in tokens as Langgraph doesn't support streaming to an interface
