from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.math_tools import calculator

class MathAgent:
    def __init__(self, api_key):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=api_key,
            temperature=0.1
        )
        self.tools = [calculator]
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful math agent. You solve mathematical problems and solve the problems using the tools when needed finally after receiving the results form the tools iterate your answer and remeber to do the following."
            "1. Explain the problem and the solution in depth with example and also provide a question similar to the user's query. Furthermore, make sure to give the response in humanized way and don't sound like a robot. "
            "While solving calculation problems do the following: "
            "1. Analyze the problem and breat it down into smaller steps "
            "2. Use tools when needed "
            "3. If no tools are matching the query then use the LLM to solve the problem."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, max_execution_time=5
                                      )

    def process(self, query: str) -> str:
        return self.executor.invoke({"input": query})["output"]
