# Benchmark Datasets

This directory is reserved for benchmark datasets.

## Supported Formats

### ShareGPT Dataset

The ShareGPT dataset format contains conversations in JSON format. To use:

1. Download the ShareGPT dataset (available from various sources)
2. Place the JSON file in this directory
3. Configure the benchmark with `dataset_path` pointing to the file

Example ShareGPT format:
```json
{
  "id": "conversation_1",
  "conversations": [
    {"from": "human", "value": "What is machine learning?"},
    {"from": "gpt", "value": "Machine learning is..."}
  ]
}
```

### Custom Datasets

Custom datasets should be in JSONL format with one prompt per line:

```jsonl
{"prompt": "Explain the concept of neural networks."}
{"prompt": "What is the difference between supervised and unsupervised learning?"}
{"prompt": "How does gradient descent work?"}
```

## Usage

Configure the dataset path in your benchmark configuration:

```python
config = BenchmarkConfig(
    dataset_path=Path("./datasets/sharegpt.json"),
    ...
)
```

Or via CLI:

```bash
sage-bench run --dataset ./datasets/sharegpt.json ...
```

## Notes

- Large datasets may require significant memory
- The benchmark will sample prompts randomly from the dataset
- Prompt lengths are adjusted to match the configured `prompt_len_range`
