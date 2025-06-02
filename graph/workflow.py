from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # Added AIMessage
from agents.math_agent import MathAgent
from agents.tutor_agent import TutorAgent
from agents.physics_agent import PhysicsAgent 


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str

class TutorWorkflow:
    def __init__(self, api_key: str):
        self.math_agent = MathAgent(api_key)
        self.physics_agent = PhysicsAgent(api_key)
        self.tutor = TutorAgent(api_key)

        workflow = StateGraph(State)
        workflow.add_node("tutor", self.tutor_node)
        workflow.add_node("math_agent", self.math_node)
        workflow.add_node("physics_agent",self.physics_agent_node)
        workflow.add_node("fallback", self.fallback_node)
        workflow.add_conditional_edges("tutor", self.should_continue, {
            "math_agent": "math_agent",
            "physics_agent": "physics_agent",
            "FINISH": "fallback",
        })
        workflow.add_edge("math_agent", END)
        workflow.add_edge("physics_agent", END)
        workflow.add_edge("fallback", END)
        workflow.set_entry_point("tutor")
        self.app = workflow.compile()

    def physics_agent_node(self, state: State):
        last = state["messages"][-1]
        response = self.physics_agent.process(last.content)
        self.tutor.memory.save_context(
               {"input": last.content},  # user message
                {"output": response}              # agent response
         )
        return {"messages": [AIMessage(content=response)]} # Changed BaseMessage to AIMessage
    
    def tutor_node(self, state: State):
        last = state["messages"][-1]
        decision = self.tutor.route(last.content)
        return {"next": decision}
    
    def fallback_node(self, state: State):
        last = state["messages"][-1]
        decision = self.tutor.route(last.content)
        fallback_message = self.tutor.generate_fallback(last.content)
        return {"messages": [AIMessage(content=fallback_message)]} # Changed BaseMessage to AIMessage
 

    def math_node(self, state: State):
        last = state["messages"][-1]
        response = self.math_agent.process(last.content)
        self.tutor.memory.save_context(
               {"input": last.content},  # user message
                {"output": response}              # agent response
         )
        return {"messages": [AIMessage(content=response)]} # Changed BaseMessage to AIMessage

    def should_continue(self, state: State):
        return state.get("next", "FINISH")

    def process_query(self, query: str) -> str:
        result = self.app.invoke({"messages": [HumanMessage(content=query)]})
        return result["messages"][-1].content
