from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.physics_tools import physics_constant_lookup, unit_converter

class PhysicsAgent:
    def __init__(self,api_key):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.3,
        )
        self.tools = [physics_constant_lookup, unit_converter]
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful math agent. You solve physics problems and explain all the concepts related to the physics. You try to solve the problems using the tools when needed finally after receiving the results form the tools iterate your answer the results in the following manner."
            "While solving calculation problems do the following: "
            "1. Analyze the problem and breat it down into smaller steps "
            "2. Use tools when needed "
            "3. If no tools are matching the query then use the LLM to solve the problem."
            "While explaining the concepts make sure to do the following: "
            "1. Explain the problem and the solution in depth with example and also provide a question similar to the user's query. Furthermore, make sure to give the response in humanized way and don't sound like a robot."),   
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