# Memorag Experiment

This experiment consists of two main scripts:
1. **`memorag_main.py`**: Runs the main experiment logic and generates results.
2. **`memorag_evaluation.py`**: Evaluates the generated results.

## Steps to Run

### 0. Complete the installation of sage

Complete the installation of sage and download the necessary corpora:
```bash
cd data/corpus
bash unzip.sh
```

Then enter the experiment directory:
```bash
cd /workspace/experiment/memorag
```

### 1. Run the Main Experiment Script
First, run the main experiment script to generate results:
```bash
python memorag_main.py
```
This script will generate experimental data and save it to the specified path (e.g., `/workspace/experiment/memorag/output.txt`).

### 2. Run the Evaluation Script
Next, run the evaluation script to evaluate the generated results:
```bash
python experiment/memorag/memorag_evaluation.py
```
This script will load the generated results, compute evaluation metrics (e.g., BERT Recall, ROUGE-L, and RBalg scores), and save detailed results to `/workspace/experiment/memorag/evaluation_results.txt`.

### 3. Check the Results
After evaluation, you can check the results in the following paths:
- **Generated Results**: `/workspace/experiment/memorag/output.txt`
- **Evaluation Results**: `/workspace/experiment/memorag/evaluation_results.txt`

---

### Example Output
After running the evaluation script, the terminal will display:
```
Average RBalg Score: 0.8765
Average BERT Recall: 0.9123
Average ROUGE-L Score: 0.8456

Detailed results have been saved to /workspace/experiment/memorag/evaluation_results.txt
```