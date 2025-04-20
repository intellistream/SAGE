import sage
import logging
# Assume the query module exposes execute() to handle a single query

def main():
    # Session unaware query
    while(True):
        user_input = input("\n>>> ").strip()
        if user_input.lower() == "exit":
            logging.info("Exiting SAGE Interactive Console")
            print("Goodbye!")
            break
        sage.query.run_query(user_input)
    # # Session aware query
    # response = sage.query.run_query("Hello, who are you?", session_id="user123")

if __name__ == "__main__":
    main()