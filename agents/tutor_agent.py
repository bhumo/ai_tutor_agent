from pydantic import BaseModel
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationSummaryMemory


class RouteDecision(BaseModel):
    next: Literal["math_agent", "physics_agent", "FINISH"]

class TutorAgent:
    def __init__(self, api_key: str):
        self.llm_raw = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=api_key,
            temperature=0.3,    
        )
        
        self.memory = ConversationSummaryMemory(
            llm=self.llm_raw,
            return_messages=True
        )
        self.router_llm = self.llm_raw.with_structured_output(RouteDecision)
    
    def route(self, input_text: str) -> str:
        # Get the current conversation summary and i am adding it later in worflow 
        summary = self.memory.load_memory_variables({}).get("history", "")
        if not summary:
            summary = "No conversation history available."
        print("Summary of conversation:", summary)
        print(self.memory.chat_memory)
        full_prompt = f"""
        Conversation Summary:{summary}
        You are a supervisor tasked with managing a conversation between the following agents:
        - math_agent: Handles simple arithmetic problems
        - physics_agent: Handles physics problems, constants, formulas, unit conversions
        User message: {input_text}
        Given the user question above, determine which agent should handle it. You can responde with "math_agent", "physics_agent", or "FINISH" if the question is not related to either agent. 
        If the question is answered satisfactorily,
        """

        try:
            result = self.router_llm.invoke(full_prompt)
            print("Routing decision:", result)
            return result.next
        except Exception as e:
            print(f"[TutorAgent Routing Error] {str(e)}")
            return "math_agent"  # default fallback
