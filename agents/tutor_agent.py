from pydantic import BaseModel
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationSummaryMemory
from langchain_core.messages import AIMessage # Added AIMessage import


class RouteDecision(BaseModel):
    next: Literal["math_agent", "physics_agent", "FINISH"]

class TutorAgent:
    def __init__(self, api_key: str):
        self.llm_raw = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=api_key,
            temperature=0.5,    
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
        Given the user question above and also have a look at the conversation summary and check if the user is refering to it or not, determine which agent should handle it. You can responde with "math_agent", "physics_agent", or "FINISH" if the question is not related to either agent. 
        Please answer in a helpful and conversational way, using the context above in the conversation summary if needed.
        """

        try:
            result = self.router_llm.invoke(full_prompt)
            print("Routing decision:", result)
            return result.next
        except Exception as e:
            print(f"[TutorAgent Routing Error] {str(e)}")
            return "math_agent"  # default fallback
        
    def generate_fallback(self, query: str) -> str: 
        print(f"Generating fallback response for query: {query}")
        fallback_prompt = f"""
        You are a helpful tutor agent. The user has asked a question that is not related to math or physics.
        User question: {query}
        Please provide a friendly and helpful response explaining that you can only assist with math or physics related questions at the moment.
        """

        response = self.llm_raw.invoke(fallback_prompt)
        print("Fallback response:", response.content)

        return response.content  
