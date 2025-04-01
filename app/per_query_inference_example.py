import sage

# Assume the query module exposes execute() to handle a single query

def main():
    # Session unaware query
    cur_query = "What is the Lisa?"
    response = sage.query.run_query(cur_query)
    print("Response:", response)

    # # Session aware query
    # response = sage.query.run_query("Hello, who are you?", session_id="user123")

if __name__ == "__main__":
    main()