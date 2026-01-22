"""
Example usage scenarios for the Comprehensive Anthropic Agent.

This file demonstrates various use cases for all middleware components.
Uses LangChain v1 API.
"""

from agent import create_comprehensive_agent


def example_memory_persistence():
    """Demonstrate memory persistence across conversation turns."""
    print("=" * 60)
    print("EXAMPLE 1: Memory Persistence")
    print("=" * 60)

    agent = create_comprehensive_agent()
    thread_id = "memory-demo"

    try:
        # Store information in memory
        print("\n[User]: Remember these facts about me:")
        print("  - Name: Alice")
        print("  - Role: Data Scientist")
        print("  - Current project: Customer churn prediction")
        print("  - Deadline: March 15th")

        response = agent.get_response(
            """Remember these facts about me:
            - Name: Alice
            - Role: Data Scientist
            - Current project: Customer churn prediction
            - Deadline: March 15th

            Confirm what you've stored.""",
            thread_id=thread_id
        )
        print(f"\n[Agent]: {response}\n")

        # Recall specific information
        print("[User]: What's my project deadline?")
        response = agent.get_response(
            "What's my project deadline?",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

    finally:
        agent.cleanup()


def example_file_operations():
    """Demonstrate text editor capabilities."""
    print("=" * 60)
    print("EXAMPLE 2: File Operations with Text Editor")
    print("=" * 60)

    agent = create_comprehensive_agent()
    thread_id = "file-ops-demo"

    try:
        # Create a Python project structure
        print("\n[User]: Create a Python data analysis project with:")
        print("  - /project/main.py (entry point)")
        print("  - /project/utils/data_loader.py (data loading utilities)")
        print("  - /project/utils/analyzer.py (analysis functions)")

        response = agent.get_response(
            """Create a Python data analysis project with the following structure:
            - /project/main.py - entry point with example usage
            - /project/utils/data_loader.py - data loading utilities
            - /project/utils/analyzer.py - analysis functions

            Include basic implementations for each file.""",
            thread_id=thread_id
        )
        print(f"\n[Agent]: {response}\n")

        # Edit a file
        print("[User]: Add a function to calculate mean and median in analyzer.py")
        response = agent.get_response(
            "Add a function called 'calculate_statistics' to /project/utils/analyzer.py "
            "that calculates mean and median",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # View file contents
        print("[User]: Show me the contents of analyzer.py")
        response = agent.get_response(
            "Show me the current contents of /project/utils/analyzer.py",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

    finally:
        agent.cleanup()


def example_file_search():
    """Demonstrate file search capabilities."""
    print("=" * 60)
    print("EXAMPLE 3: File Search")
    print("=" * 60)

    agent = create_comprehensive_agent()
    thread_id = "search-demo"

    try:
        # First create some files
        print("\n[User]: Create a web application project with multiple files")
        agent.get_response(
            """Create a simple web application with:
            - /project/app.py - Flask application
            - /project/models/user.py - User model
            - /project/models/product.py - Product model
            - /project/routes/api.py - API routes
            - /project/templates/index.html - HTML template
            - /project/static/style.css - CSS styles""",
            thread_id=thread_id
        )

        # Search for Python files
        print("\n[User]: Find all Python files in the project")
        response = agent.get_response(
            "Find all Python files in the /project directory",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Search for specific content
        print("[User]: Search for files containing 'Flask' or 'app'")
        response = agent.get_response(
            "Search for files that contain the word 'Flask' or 'app'",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

    finally:
        agent.cleanup()


def example_bash_commands():
    """Demonstrate bash tool capabilities."""
    print("=" * 60)
    print("EXAMPLE 4: Bash Command Execution")
    print("=" * 60)

    agent = create_comprehensive_agent()
    thread_id = "bash-demo"

    try:
        # Check Python version
        print("\n[User]: What version of Python is available?")
        response = agent.get_response(
            "What version of Python is available in the environment?",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Create and run a Python script
        print("[User]: Create a script that generates random numbers and run it")
        response = agent.get_response(
            """Create a Python script that generates 5 random numbers between 1 and 100,
            then execute it and show me the results.""",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

    finally:
        agent.cleanup()


def example_combined_workflow():
    """Demonstrate a complex workflow using all middleware."""
    print("=" * 60)
    print("EXAMPLE 5: Combined Workflow - Data Analysis Task")
    print("=" * 60)

    agent = create_comprehensive_agent()
    thread_id = "combined-demo"

    try:
        # Step 1: Store project context in memory
        print("\n[Step 1] Store project context")
        response = agent.get_response(
            """Remember this project context:
            - Project: Sales data analysis
            - Goal: Analyze Q4 2024 sales trends
            - Data format: CSV with columns (date, product, quantity, revenue)
            - Required outputs: Summary statistics and trend visualization""",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Step 2: Create project structure
        print("[Step 2] Create project structure")
        response = agent.get_response(
            """Create a data analysis project with:
            - /project/analyze.py - main analysis script
            - /project/data/ - directory for data files
            - /project/output/ - directory for results""",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Step 3: Generate sample data
        print("[Step 3] Generate sample CSV data")
        response = agent.get_response(
            """Create a sample CSV file at /project/data/sales.csv with 10 rows of sample sales data.
            Include columns: date, product, quantity, revenue""",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Step 4: Create analysis script
        print("[Step 4] Create analysis script")
        response = agent.get_response(
            """Create a Python script at /project/analyze.py that:
            1. Reads the CSV data
            2. Calculates total revenue and average quantity
            3. Prints the results""",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Step 5: Search for data files
        print("[Step 5] Find all data files")
        response = agent.get_response(
            "Find all CSV files in the project",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

        # Step 6: Recall project goal
        print("[Step 6] Recall project goal from memory")
        response = agent.get_response(
            "What was the goal of this project?",
            thread_id=thread_id
        )
        print(f"[Agent]: {response}\n")

    finally:
        agent.cleanup()


def example_prompt_caching_benefit():
    """Demonstrate prompt caching benefits with repeated context."""
    print("=" * 60)
    print("EXAMPLE 6: Prompt Caching Benefits")
    print("=" * 60)

    agent = create_comprehensive_agent()
    thread_id = "caching-demo"

    # Long system context that will be cached
    long_context = """
    You are working on a large codebase with the following structure:
    - 50+ Python modules
    - 200+ functions
    - Complex dependency graph
    - Extensive documentation

    [... imagine this is 5000+ tokens of context ...]
    """

    try:
        print("\n[Turn 1] First request - cache is created")
        response = agent.get_response(
            f"{long_context}\n\nCreate a new utility function for string processing.",
            thread_id=thread_id
        )
        print(f"[Agent]: {response[:200]}...\n")

        print("[Turn 2] Second request - cache is reused (faster & cheaper)")
        response = agent.get_response(
            f"{long_context}\n\nCreate another utility for date handling.",
            thread_id=thread_id
        )
        print(f"[Agent]: {response[:200]}...\n")

        print("Note: The second request reuses cached context, reducing latency and cost!")

    finally:
        agent.cleanup()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMPREHENSIVE ANTHROPIC AGENT - EXAMPLES")
    print("=" * 60 + "\n")

    # Run all examples
    examples = [
        ("Memory Persistence", example_memory_persistence),
        ("File Operations", example_file_operations),
        ("File Search", example_file_search),
        ("Bash Commands", example_bash_commands),
        ("Combined Workflow", example_combined_workflow),
        ("Prompt Caching", example_prompt_caching_benefit),
    ]

    print("Available examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...\n")

    for name, example_func in examples:
        try:
            example_func()
            print("\n")
        except Exception as e:
            print(f"\nError in {name}: {e}\n")

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
