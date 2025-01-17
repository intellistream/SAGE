import json

class Corpus:
    def __init__(self, path):
        """
        Initialize the Corpus object.
        :param path: Path to the JSONL file containing the corpus data.
        """
        self.items = []
        self._load_from_jsonl(path)
        self.len = len(self.items)

    def _load_from_jsonl(self, path):
        """
        Load data from a JSONL file and populate the items list.
        :param path: Path to the JSONL file.
        """
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                data = json.loads(line.strip())
                id = data.get("_id")
                text = data.get("text")
                self.items.append({"external_id": id, "text": text, "db_id": ""})

    def get_item_text(self, n):
        """
        Retrieve the text of the nth item in the corpus.
        :param n: Index of the item.
        :return: The text of the nth item.
        :raises IndexError: If the index is out of range.
        """
        if 0 <= n < self.len:
            return self.items[n]["text"]
        else:
            raise IndexError(f"Index {n} is out of range. Corpus has {self.len} items.")

    def get_len(self):
        """
        Get the total number of items in the corpus.
        :return: The number of items in the corpus.
        """
        return self.len

    def get_db_id(self, n):
        """
        Get the db_id in the corpus.
        :return: The db_id in the corpus.
        """
        return self.items[n]["db_id"]

    def set_db_id(self, n, db_id):
        """
        Set the database ID for the nth item in the corpus.
        :param n: Index of the item.
        :param db_id: The database ID to set.
        :raises IndexError: If the index is out of range.
        """
        if 0 <= n < self.len:
            self.items[n]["db_id"] = db_id
        else:
            raise IndexError(f"Index {n} is out of range. Corpus has {self.len} items.")