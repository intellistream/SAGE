#!/usr/bin/env python3
"""
F1 Score Analysis for Benchmark Memory Tests
Analyzes F1 scores from JSON test results and generates visualizations.

Usage: python run_f1_analysis.py
"""

# ============================================================================
# CONFIGURATION - Modify these paths as needed
# ============================================================================
INPUT_DIR = ".sage/benchmarks/benchmark_memory/locomo/251122/stm"
OUTPUT_DIR = ".sage/benchmarks/benchmark_memory/locomo/output/251122/stm"
# ============================================================================

import json
import sys
import string
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

try:
    import regex
    from nltk.stem import PorterStemmer
except ImportError as e:
    print(f"Error: {e}\nInstall: pip install regex nltk && python -m nltk.downloader porter_test")
    sys.exit(1)

ps = PorterStemmer()


# ============================================================================
# F1 Score Calculation Functions
# ============================================================================

def normalize_answer(s):
    """Normalize answer text for comparison."""
    s = s.replace(',', "")
    exclude = set(string.punctuation)
    s = ''.join(ch for ch in s if ch not in exclude)
    s = regex.sub(r'\b(a|an|the|and)\b', ' ', s.lower())
    return ' '.join(s.split())


def f1_score(prediction, ground_truth):
    """Calculate token-level F1 score."""
    pred_tokens = [ps.stem(w) for w in normalize_answer(prediction).split()]
    gt_tokens = [ps.stem(w) for w in normalize_answer(ground_truth).split()]
    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(gt_tokens)
    return (2 * precision * recall) / (precision + recall)


def f1_multi(prediction, ground_truth):
    """F1 for comma-separated multi-answers."""
    preds = [p.strip() for p in prediction.split(',')]
    gts = [g.strip() for g in ground_truth.split(',')]
    return np.mean([max([f1_score(p, gt) for p in preds]) for gt in gts])


def eval_question_answering(qas):
    """Evaluate QA with category-specific F1 calculation."""
    f1_scores = []
    for i, q in enumerate(qas):
        answer = str(q['answer'])
        if q['category'] == 3:
            answer = answer.split(';')[0].strip()
        output = q['prediction']
        
        if q['category'] in [2, 3, 4]:
            f1_scores.append(f1_score(output, answer))
        elif q['category'] == 1:
            f1_scores.append(f1_multi(output, answer))
        elif q['category'] == 5:
            f1_scores.append(1 if 'no information' in output.lower() or 'not mentioned' in output.lower() else 0)
        else:
            raise ValueError(f"Unknown category: {q['category']}")
    
    print(f"    {len(qas)} questions evaluated")
    return f1_scores


# ============================================================================
# Analysis Functions
# ============================================================================


def load_json_files(input_dir: str) -> Dict[str, dict]:
    """Load all JSON files from input directory."""
    json_files = {}
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"Error: '{input_dir}' not found!")
        sys.exit(1)
    for f in sorted(input_path.glob("*.json")):
        with open(f, 'r', encoding='utf-8') as fp:
            json_files[f.stem] = json.load(fp)
    print(f"Loaded {len(json_files)} JSON files")
    return json_files


def analyze_task(task_name: str, data: dict) -> Dict:
    """Analyze F1 scores for one task across rounds."""
    results = data.get('test_results', [])
    round_scores = []
    for test in results:
        qas = [{'answer': q.get('reference_answer', ''), 
                'prediction': q.get('predicted_answer', ''),
                'category': q.get('category', 1)} 
               for q in test.get('questions', [])]
        if qas:
            f1s = eval_question_answering(qas)
            round_scores.append({'round': test.get('test_index', 0), 'f1_score': np.mean(f1s)})
    return {
        'task_name': task_name,
        'round_scores': round_scores,
        'average_f1': np.mean([r['f1_score'] for r in round_scores]) if round_scores else 0
    }



def plot_task(analysis: Dict, output_dir: Path):
    """Plot F1 scores for one task."""
    name = analysis['task_name']
    rounds = [r['round'] for r in analysis['round_scores']]
    f1s = [r['f1_score'] for r in analysis['round_scores']]
    avg = analysis['average_f1']
    
    plt.figure(figsize=(10, 6))
    plt.plot(rounds, f1s, marker='o', linewidth=2, markersize=8, label='F1 per Round')
    plt.axhline(y=avg, color='r', linestyle='--', linewidth=2, label=f'Avg: {avg:.4f}')
    plt.xlabel('Round', fontsize=12)
    plt.ylabel('F1 Score', fontsize=12)
    plt.title(f'{name} - F1 Scores', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / f"{name}_f1.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ {name}_f1.png (Avg: {avg:.4f})")


def plot_summary(analyses: List[Dict], output_dir: Path):
    """Plot summary across all tasks."""
    max_rounds = max(len(a['round_scores']) for a in analyses)
    round_avgs = []
    for r in range(1, max_rounds + 1):
        scores = []
        for a in analyses:
            for rs in a['round_scores']:
                if rs['round'] == r:
                    scores.append(rs['f1_score'])
                    break
        if scores:
            round_avgs.append({'round': r, 'f1_score': np.mean(scores)})
    
    overall = np.mean([r['f1_score'] for r in round_avgs]) if round_avgs else 0
    rounds = [r['round'] for r in round_avgs]
    f1s = [r['f1_score'] for r in round_avgs]
    
    plt.figure(figsize=(12, 7))
    plt.plot(rounds, f1s, marker='s', linewidth=2.5, markersize=10, color='#2E86AB', label='Avg F1 (All Tasks)')
    plt.axhline(y=overall, color='r', linestyle='--', linewidth=2, label=f'Overall: {overall:.4f}')
    plt.xlabel('Round', fontsize=13)
    plt.ylabel('F1 Score', fontsize=13)
    plt.title('Summary: All Tasks Average F1', fontsize=15, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "summary_f1.png", dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  ✓ summary_f1.png (Overall: {overall:.4f})")
    return round_avgs, overall


def save_report(analyses: List[Dict], summary_rounds: List[Dict], overall: float, output_dir: Path):
    """Save JSON report."""
    report = {
        "summary": {
            "total_tasks": len(analyses),
            "rounds": [{"round": r['round'], "f1_score": round(r['f1_score'], 4)} for r in summary_rounds],
            "overall_average_f1": round(overall, 4)
        },
        "tasks": [
            {
                "task_name": a['task_name'],
                "rounds": [{"round": r['round'], "f1_score": round(r['f1_score'], 4)} for r in a['round_scores']],
                "task_average_f1": round(a['average_f1'], 4)
            } for a in analyses
        ]
    }
    with open(output_dir / "f1_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    print(f"  ✓ f1_report.json")


def main():
    """Main pipeline."""
    print("="*80)
    print("F1 Score Analysis")
    print("="*80)
    print(f"Input:  {INPUT_DIR}\nOutput: {OUTPUT_DIR}\n")
    
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    
    files = load_json_files(INPUT_DIR)
    if not files:
        print("No JSON files found.")
        return
    
    print(f"\n{'='*80}\nAnalyzing Tasks\n{'='*80}\n")
    analyses = []
    for name, data in files.items():
        print(f"{name}:")
        analysis = analyze_task(name, data)
        analyses.append(analysis)
        plot_task(analysis, output_path)
    
    print(f"\n{'='*80}\nSummary\n{'='*80}\n")
    summary_rounds, overall = plot_summary(analyses, output_path)
    save_report(analyses, summary_rounds, overall, output_path)
    
    print(f"\n{'='*80}\n✓ Complete!\n{'='*80}")
    print(f"Results: {OUTPUT_DIR}\n  • {len(analyses)} task plots\n  • 1 summary plot\n  • 1 JSON report\n")


if __name__ == "__main__":
    main()
