from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.physics_tools import physics_constant_lookup, unit_converter

class PhysicsAgent:
    def __init__(self,api_key):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=api_key,
            temperature=0.3,
        )
        self.tools = [physics_constant_lookup, unit_converter]
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful physics agent. You can answer questions related to physics constants and unit conversions."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True, max_execution_time=5)
    def process(self, query: str) -> str:  
        try:
            response = self.executor.invoke({"input": query})
            return response["output"]
        except Exception as e:
            print(f"[PhysicsAgent Error] {str(e)}")
            return f"An error {str(e)} occurred while processing your request."