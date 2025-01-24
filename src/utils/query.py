import json

class Query:
    def __init__(self, path):
        """
        Initialize the Query object.
        :param path: Path to the JSONL file containing the query data.
        """
        self.dialogues = []
        self.dialogue_info = {}
        self._load_from_jsonl(path)

    def _load_from_jsonl(self, path):
        """
        Load data from a JSONL file and process it to store dialogues.
        Only the last occurrence of each conversation_id is processed.
        :param path: Path to the JSONL file.
        """
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for i in range(len(lines)):
                current_data = json.loads(lines[i].strip())
                current_conversation_id = current_data.get("conversation_id")

                if i < len(lines) - 1:
                    next_data = json.loads(lines[i + 1].strip())
                    next_conversation_id = next_data.get("conversation_id")
                    if current_conversation_id == next_conversation_id:
                        continue

                self._process_and_store_dialogue(current_data)

    def _process_and_store_dialogue(self, data):
        """
        Process a single dialogue entry and store it in the dialogues dictionary.
        :param data: A dictionary representing a single JSONL entry.
        """
        conversation_id = data.get("conversation_id")
        input_data = data.get("input", [])
        targets_data = data.get("targets", [])

        # Process input and targets to extract speaker and text
        dialogue = []
        for item in input_data:
            speaker = item.get("speaker")
            text = item.get("text")
            dialogue.append({"speaker": speaker, "text": text})

        for item in targets_data:
            speaker = item.get("speaker")
            text = item.get("text")
            dialogue.append({"speaker": speaker, "text": text})

        # Store the dialogue in the dictionary
        self.dialogues.append(dialogue)

        # Store dialogue length and initialize current turn to 0
        self.dialogue_info[len(self.dialogues) - 1] = {
            "length": len(dialogue),
            "dialogue_length": int(len(dialogue) / 2),
            "current_turn": 0
        }

    def iter_dialogue(self, n):
        """
        A generator to iterate through query-response pairs in the n-th dialogue.
        :param n: The index of the dialogue.
        :yield: A tuple of (query, response) for each turn.
        """
        if n >= len(self.dialogues):
            raise IndexError("Dialogue index out of range")

        for turn in range(self.dialogue_info[n]["dialogue_length"]):
            query_index = turn * 2
            response_index = turn * 2 + 1

            query = self.dialogues[n][query_index]["text"]
            response = self.dialogues[n][response_index]["text"]
            yield turn, query, response

    def iter_all_dialogues(self):
        """
        A generator to iterate through all query-response pairs in all dialogues.
        :yield: A tuple of (dialogue_index, query, response) for each turn.
        """
        for n in range(len(self.dialogues)):
            for turn, query, response in self.iter_dialogue(n):
                yield n, turn, query, response

    def get_all_response(self):
        """
        Returns all the lines spoken by the agent in all the conversations.
        :return: A list containing all the lines spoken by the agent.
        """
        agent_responses = []
        for dialogue in self.dialogues:
            for utterance in dialogue:
                if utterance["speaker"] == "agent":
                    agent_responses.append(utterance["text"])
        return agent_responses

if __name__ == "__main__":
    from src.utils.file_path import QUERY_FILE
    query = Query(QUERY_FILE)
    i = 0
    for dialogue_index, turn, q, r in query.iter_all_dialogues():
        i += 1
    print(i)