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
            ("system", "You are a helpful math agent. You solve mathematical problems"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, max_execution_time=5
                                      )

    def process(self, query: str) -> str:
        return self.executor.invoke({"input": query})["output"]
