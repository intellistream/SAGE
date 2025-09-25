#!/usr/bin/env python3
"""
Full-featured SAGE video demo (end-to-end)

This example extends examples/video/video_demo.ipynb into a complete, scriptable pipeline:
- Read a local video and sample frames
- Generate per-frame textual captions (CLIP zero-shot classification or fallback)
- Index captions into ChromaDB using SAGE retriever backend and embedding model
- Run a RAG QA query against the indexed captions
- Optionally expose an Agent tool to search the video captions

The script is designed to run even in limited/offline environments:
- If CLIP or HF cannot be loaded, uses a lightweight text-only fallback
- If chromadb is unavailable, stores captions in memory and answers via a simple search
- If OpenAI-like generator is not configured, prints retrieved context and a heuristic answer

Usage:
  python examples/video/video_full_demo.py --video <path> [--query "What is happening?"]

Environment/test mode:
  - Set SAGE_EXAMPLES_MODE=test to force all components into lightweight mock fallbacks

"""
import os
import sys
import time
import json
import argparse
import copy
from typing import List, Dict, Any, Optional

# Make sure project root is importable when run as a script
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CUR_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# Soft dependencies
try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    import torch  # type: ignore
    from PIL import Image  # type: ignore
    from transformers import CLIPProcessor, CLIPModel  # type: ignore
except Exception:
    torch = None
    Image = None
    CLIPProcessor = None
    CLIPModel = None

# Optional config dependency
try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger

# RAG utilities from SAGE
from sage.libs.rag.retriever import ChromaRetriever
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.generator import OpenAIGenerator


# ----------------------
# 1) Video frame source
# ----------------------
class VideoBatch(BatchFunction):
    def __init__(self, video_path: str, sample_every: int = 5):
        """Read frames from a video. sample_every means take 1 frame every N frames."""
        super().__init__()
        if cv2 is None:
            raise RuntimeError("OpenCV (cv2) is required to read video frames.")
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise FileNotFoundError(f"Cannot open video: {video_path}")
        self.sample_every = max(1, int(sample_every))
        self.frame_index = 0

    def execute(self) -> Optional[Dict[str, Any]]:
        # Iterate until EOF; return None to stop
        while True:
            ok, frame = self.cap.read()
            if not ok:
                self.cap.release()
                return None
            self.frame_index += 1
            if (self.frame_index - 1) % self.sample_every != 0:
                # skip frames to reduce load
                continue
            # Convert BGR->RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            return {"frame": frame_rgb, "frame_number": self.frame_index}


# ----------------------------------
# 2) Video frame captioning (CLIP)
# ----------------------------------
class VideoAIAnalyzer(MapFunction):
    def __init__(self, analysis_interval: int = 1):
        super().__init__()
        self.analysis_interval = max(1, analysis_interval)
        self.counter = 0
        self.last_caption = ""

        # Predefined scene templates for zero-shot classification
        self.scene_templates = [
            "A person riding a bicycle",
            "A person exercising in a park",
            "Outdoor activity scenes",
            "A person walking on the street",
            "Sports and fitness activities",
            "Leisure time",
            "Activities in green environments",
            "Using transportation",
            "Everyday life scenes",
            "Healthy lifestyle",
        ]

        self.use_clip = False
        self.device = "cpu"
        try:
            if os.environ.get("SAGE_EXAMPLES_MODE") == "test":
                raise RuntimeError("Force fallback in test mode")
            if torch is not None and CLIPModel is not None and CLIPProcessor is not None:
                model_name = "openai/clip-vit-base-patch32"
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model = CLIPModel.from_pretrained(model_name).to(self.device)
                self.processor = CLIPProcessor.from_pretrained(model_name)
                self.use_clip = True
        except Exception as e:
            self.model = None
            self.processor = None
            self.use_clip = False
            self.logger.warning(f"CLIP unavailable, using heuristic captions. Reason: {e}")

    def _clip_caption(self, frame_rgb) -> str:
        if not self.use_clip or Image is None:
            return ""
        try:
            pil_image = Image.fromarray(frame_rgb)
            inputs = self.processor(
                text=self.scene_templates, images=pil_image, return_tensors="pt", padding=True
            ).to(self.device)
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            idx = probs.argmax().item()
            conf = probs[0][idx].item()
            label = self.scene_templates[idx]
            return f"{label} (p={conf:.2f})"
        except Exception as e:
            return f"Visual analysis error: {e}"

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if data is None:
            return data
        self.counter += 1
        frame = data["frame"]
        caption = self.last_caption
        if self.counter % self.analysis_interval == 0:
            cap = self._clip_caption(frame)
            if not cap:
                # Simple heuristic fallback based on frame number to keep it lightweight
                fn = data.get("frame_number", 0)
                cap = f"Video frame {fn}: generic outdoor activity"
            self.last_caption = cap
            caption = cap
        data["caption"] = caption
        return data


# -------------------------------------------------
# 3) Index captions into Chroma or in-memory store
# -------------------------------------------------
class CaptionIndexer(MapFunction):
    def __init__(self, chroma_conf: Dict[str, Any], embedding_conf: Dict[str, Any], top_k: int = 5):
        super().__init__()
        self.top_k = top_k
        self._use_chroma = True
        self._retriever = None
        # Lightweight fallback store
        self._docs: List[str] = []
        try:
            self._retriever = ChromaRetriever({
                "dimension": embedding_conf.get("dimension", 384),
                "top_k": top_k,
                "embedding": embedding_conf,
                "chroma": chroma_conf,
            })
        except Exception as e:
            self._use_chroma = False
            self.logger.warning(f"Chroma unavailable, using in-memory caption store. Reason: {e}")

    def add_caption(self, text: str):
        if not text:
            return
        if self._use_chroma and self._retriever is not None:
            try:
                self._retriever.add_documents([text])
                return
            except Exception as e:
                self.logger.warning(f"Failed to add to Chroma, fallback to memory: {e}")
                self._use_chroma = False
        # Fallback
        self._docs.append(text)

    def search(self, query: str) -> List[str]:
        if self._use_chroma and self._retriever is not None:
            out = self._retriever.execute(query)
            results = out.get("results", [])
            texts = []
            for r in results:
                if isinstance(r, dict) and "text" in r:
                    texts.append(r["text"])
                elif isinstance(r, str):
                    texts.append(r)
                else:
                    texts.append(str(r))
            return texts
        # naive memory search
        q = (query or "").lower()
        hits = [d for d in self._docs if q in d.lower()]
        return hits[: self.top_k]

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # On streaming frames, keep indexing; pass-through
        caption = data.get("caption")
        if caption:
            self.add_caption(caption)
        return data


# --------------------------------------
# 4) Simple QA over the indexed captions
# --------------------------------------
class CaptionQARunner(SinkFunction):
    def __init__(self, indexer: CaptionIndexer, generator_conf: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.idx = indexer
        self.gen_conf = generator_conf or {}
        self._generator = None
        self._promptor = QAPromptor({})
        # Lazy init generator; allow no-op when missing
        if self.gen_conf:
            try:
                self._generator = OpenAIGenerator(self.gen_conf)
            except Exception as e:
                self.logger.warning(f"Generator unavailable, will print context only: {e}")
                self._generator = None

    def ask(self, question: str) -> Dict[str, Any]:
        context = self.idx.search(question)
        if not context:
            print("No context retrieved from captions.")
        prompt_input = {"query": question, "results": [{"text": c} for c in context]}
        user_query, messages = self._promptor.execute(prompt_input)
        if self._generator is None:
            # Heuristic answer fallback
            answer = context[0] if context else "I couldn't find relevant content in the video captions."
        else:
            _, answer = self._generator.execute([user_query, messages])
        return {"question": question, "context": context, "answer": answer}

    def execute(self, data: Dict[str, Any]):
        # Sink in streaming mode does nothing; queries are executed after pipeline finishes
        return None


def build_pipeline(video_path: str, chroma_conf: Dict[str, Any], embedding_conf: Dict[str, Any],
                   sample_every: int = 5, analysis_interval: int = 1, max_frames: int = 200) -> Dict[str, Any]:
    env = LocalEnvironment("VideoFullDemo")

    # Shared indexer instance
    indexer = CaptionIndexer(chroma_conf=chroma_conf, embedding_conf=embedding_conf)
    qa_sink = CaptionQARunner(indexer=indexer)

    # We stop after max_frames frames to bound runtime in examples
    class StopAfter(SinkFunction):
        def __init__(self, max_frames: int):
            super().__init__()
            self.max_frames = max_frames
            self.count = 0
        def execute(self, data):
            if data is None:
                return
            self.count += 1
            if self.count >= self.max_frames:
                # Trigger environment to stop
                raise SystemExit("Reached max frames, stopping pipeline")

    env.from_batch(VideoBatch, video_path=video_path, sample_every=sample_every) \
       .map(VideoAIAnalyzer, analysis_interval=analysis_interval) \
       .map(indexer) \
       .sink(StopAfter, max_frames=max_frames)

    return {"env": env, "indexer": indexer, "qa": qa_sink}


def main():
    parser = argparse.ArgumentParser(description="SAGE full video demo")
    parser.add_argument("--video", type=str, default=os.path.join(CUR_DIR, "mixkit-man-riding-a-bicycle-in-a-park-41868-hd-ready.mp4"))
    parser.add_argument("--query", type=str, default="What is happening in the video?")
    parser.add_argument("--sample-every", type=int, default=5)
    parser.add_argument("--analysis-interval", type=int, default=1)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--config", type=str, default=None, help="Path to YAML/JSON config for this demo")
    args = parser.parse_args()

    # Helpers
    def _expand_env(obj):
        if isinstance(obj, str):
            return os.path.expandvars(obj)
        if isinstance(obj, dict):
            return {k: _expand_env(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_expand_env(x) for x in obj]
        return obj

    # Base defaults with safe fallbacks
    default_chroma = {
        "collection_name": "video_captions",
        "persistence_path": os.path.join(CUR_DIR, "chroma_video_store"),
        "host": "localhost",
        "port": 8000,
        "use_embedding_query": True,
        "metadata": {"hnsw:space": "cosine"},
    }
    default_embedding = {
        # default uses HF sentence-transformers with auto fallback to mock in middleware
        "method": "default",  # maps to hf MiniLM with auto-fallback
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
    }

    video_path = args.video
    query = args.query
    chroma_conf = copy.deepcopy(default_chroma)
    embedding_conf = copy.deepcopy(default_embedding)
    gen_conf = None

    # Load config file if provided
    if args.config:
        cfg_path = args.config
        if not os.path.exists(cfg_path):
            print(f"Config file not found: {cfg_path}")
            sys.exit(2)
        try:
            cfg = None
            if cfg_path.endswith((".yaml", ".yml")):
                if yaml is None:
                    print("PyYAML is not installed. Please install pyyaml or provide a JSON config file.")
                    sys.exit(2)
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
            else:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            cfg = _expand_env(cfg or {})
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(2)

        # Apply config values
        if isinstance(cfg, dict):
            video_path = cfg.get("video_path", video_path)
            query = cfg.get("query", query)
            # Timings / limits
            if "sample_every" in cfg:
                args.sample_every = int(cfg["sample_every"])  # override defaults
            if "analysis_interval" in cfg:
                args.analysis_interval = int(cfg["analysis_interval"])  # override defaults
            if "max_frames" in cfg:
                args.max_frames = int(cfg["max_frames"])  # override defaults

            if isinstance(cfg.get("chroma"), dict):
                chroma_conf.update(cfg["chroma"])  # merge
            if isinstance(cfg.get("embedding"), dict):
                embedding_conf.update(cfg["embedding"])  # merge
            if isinstance(cfg.get("generator"), dict):
                gen_conf = cfg["generator"]

    # Fallback: env-based generator config if not set in config
    if gen_conf is None and os.environ.get("SAGE_OPENAI_BASE_URL") and os.environ.get("OPENAI_API_KEY"):
        gen_conf = {
            "method": "openai",
            "model_name": os.environ.get("SAGE_OPENAI_MODEL", "gpt-4o-mini"),
            "base_url": os.environ["SAGE_OPENAI_BASE_URL"],
            "api_key": os.environ["OPENAI_API_KEY"],
        }

    pipeline = build_pipeline(
        video_path=video_path,
        chroma_conf=chroma_conf,
        embedding_conf=embedding_conf,
        sample_every=args.sample_every,
        analysis_interval=args.analysis_interval,
        max_frames=args.max_frames,
    )

    env: LocalEnvironment = pipeline["env"]
    qa: CaptionQARunner = pipeline["qa"]

    t0 = time.time()
    try:
        env.submit(autostop=True)
    except SystemExit:
        pass
    except Exception as e:
        print(f"Pipeline run ended: {e}")
    dt = time.time() - t0

    print(f"Indexed captions in ~{dt:.1f}s. Now asking: {query}")
    # Inject generator config if available
    if gen_conf is not None:
        qa.gen_conf = gen_conf
        try:
            qa._generator = OpenAIGenerator(gen_conf)
        except Exception as e:
            print(f"Warning: failed to init generator, will fallback: {e}")
            qa._generator = None

    result = qa.ask(query)
    print("\n=== QA Result ===")
    print("Question:", result["question"])
    print("Context (top):", (result["context"][0] if result["context"] else "<none>"))
    print("Answer:", result["answer"])


if __name__ == "__main__":
    # Keep console clean
    CustomLogger.disable_global_console_debug()
    main()
