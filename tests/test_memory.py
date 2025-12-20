import pytest
from modules.memory import MemoryModule

@pytest.fixture
def memory_module():
    module = MemoryModule()
    module.initialize()
    return module

def test_initialization(memory_module):
    assert memory_module.history == []
    assert memory_module.concepts == {}
    assert memory_module.user_context == {}

def test_update_history(memory_module):
    memory_module.update("Hello", "Hi there")
    assert len(memory_module.history) == 2
    assert memory_module.history[0]["role"] == "user"
    assert memory_module.history[0]["content"] == "Hello"
    assert memory_module.history[1]["role"] == "assistant"
    assert memory_module.history[1]["content"] == "Hi there"

def test_short_term_memory(memory_module):
    # Add enough history
    for i in range(5):
        memory_module.update(f"Q{i}", f"A{i}")
    
    # Check default strategy includes short_term
    strategies = memory_module._decide_consultation_strategy("test")
    assert "short_term" in strategies
    
    # Consult
    results = memory_module._consult_memories("test", ["short_term"])
    assert len(results["short_term"]) <= 4 # Max 4 items (2 turns)
    assert results["short_term"][-1]["content"] == "A4"

def test_conceptual_memory_extraction(memory_module):
    # "Python" should be extracted as a concept (starts with Capital)
    # The regex in memory.py is r'\b[A-Z][a-zA-Z]+\b' and filters stoplist.
    
    memory_module.update("I like Python programming.", "Python is great.")
    
    assert "Python" in memory_module.concepts
    assert memory_module.concepts["Python"]["count"] == 1
    
    # Test retrieval
    results = memory_module._consult_memories("python", ["conceptual"])
    # Should find the messages associated with "Python"
    assert len(results["conceptual"]) > 0

def test_process_flow(memory_module):
    state = {"question": "What is Python?"}
    memory_module.update("Python is a language.", "Yes, it is.")
    
    new_state = memory_module.process(state)
    
    assert "memory_context" in new_state
    assert len(new_state["memory_context"]) > 0

def test_max_history_trimming(memory_module):
    # Max history is 20 by default. Logic trims if > max * 2. 
    # Let's set a small max history.
    small_mem = MemoryModule(config={"max_history": 2})
    small_mem.initialize()
    
    # Add 6 messages (3 turns). Threshold is 2*2 = 4 messages.
    # Logic: if len > 4, pop 2.
    
    small_mem.update("Q1", "A1")
    small_mem.update("Q2", "A2")
    # len = 4. Not > 4.
    assert len(small_mem.history) == 4
    
    small_mem.update("Q3", "A3")
    # len becomes 6. > 4. Should pop 2. len becomes 4.
    
    assert len(small_mem.history) == 4
    assert small_mem.history[0]["content"] == "Q2"
