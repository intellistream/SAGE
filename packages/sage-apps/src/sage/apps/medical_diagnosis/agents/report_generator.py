"""
报告生成Agent
负责生成结构化的诊断报告
"""

import contextlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:  # Optional dependency - fall back to template reports if unavailable
    from sage.common.components.sage_vllm import VLLMService

    _VLLM_COMPONENT_AVAILABLE = True
except Exception:  # pragma: no cover - vLLM extras may be missing in CI
    VLLMService = None  # type: ignore
    _VLLM_COMPONENT_AVAILABLE = False


@dataclass
class DiagnosisReport:
    """诊断报告"""

    diagnoses: list[str]  # 诊断列表
    confidence: float  # 置信度
    findings: list[str]  # 发现列表
    recommendations: list[str]  # 建议列表
    similar_cases: list[dict[str, Any]]  # 相似病例
    report: str  # 完整报告
    timestamp: str  # 时间戳
    quality_score: float = 0.0  # 质量评分


class ReportGenerator:
    """
    诊断报告生成器

    功能:
    1. 整合影像分析结果
    2. 参考相似病例
    3. 生成结构化诊断报告
    4. 提供治疗建议
    """

    def __init__(self, config: dict):
        """
        初始化报告生成器

        Args:
            config: 配置字典
        """
        self.config = config
        self.llm_service = None
        self._llm_generate_options: dict[str, Any] = {}
        self._setup_llm()

    def _setup_llm(self):
        """设置LLM服务"""
        print(f"   Loading LLM: {self.config['models']['llm_model']}")

        models_cfg = self.config.get("models", {}) or {}
        services_cfg = self.config.get("services", {}) or {}
        vllm_cfg = dict(services_cfg.get("vllm", {}) or {})
        self._llm_generate_options = self._resolve_generation_options(vllm_cfg)

        if not vllm_cfg.get("enabled", True):
            print("   Warning: vLLM service disabled via config, using template reports")
            return

        llm_model = models_cfg.get("llm_model")
        if not llm_model:
            print("   Warning: Missing 'llm_model' config, using template reports")
            return

        if not _VLLM_COMPONENT_AVAILABLE or VLLMService is None:
            print("   Warning: sage_vllm component unavailable, using template reports")
            return

        try:
            service_config = self._build_vllm_config(llm_model, vllm_cfg, models_cfg)
            self.llm_service = VLLMService(service_config)
            self.llm_service.setup()
            print("   ✓ vLLM service ready")
        except Exception as exc:  # pragma: no cover - runtime dependency issues
            print(f"   Warning: Failed to initialize vLLM service ({exc}), using template reports")
            self.llm_service = None

    def generate(
        self,
        image_features: dict[str, Any],
        patient_info: dict[str, Any] | None,
        similar_cases: list[dict],
        medical_knowledge: list[dict],
    ) -> DiagnosisReport:
        """
        生成诊断报告

        Args:
            image_features: 影像特征
            patient_info: 患者信息
            similar_cases: 相似病例
            medical_knowledge: 医学知识

        Returns:
            DiagnosisReport: 诊断报告
        """
        # Step 1: 构建提示词
        prompt = self._build_prompt(image_features, patient_info, similar_cases, medical_knowledge)

        # Step 2: 调用LLM生成报告
        if self.llm_service is not None:
            try:
                report_text = self._generate_with_llm(prompt)
            except Exception as exc:  # pragma: no cover - network/runtime failures
                print(f"   Warning: vLLM generation failed ({exc}), falling back to template")
                report_text = self._generate_template_report(
                    image_features, patient_info, similar_cases
                )
        else:
            report_text = self._generate_template_report(
                image_features, patient_info, similar_cases
            )

        # Step 3: 提取诊断和建议
        diagnosis_summary, findings, recommendations = self._parse_report(
            report_text, image_features
        )

        # 提取诊断列表
        diagnoses_list = []
        for abnorm in image_features.get("abnormalities", []):
            if abnorm["type"] == "disc_herniation":
                diagnoses_list.append(f"{abnorm['location']}椎间盘突出症")
            elif abnorm["type"] == "disc_degeneration":
                diagnoses_list.append(f"{abnorm['location']}椎间盘退行性变")

        if not diagnoses_list:
            diagnoses_list = ["未见明显异常"]

        # Step 4: 计算置信度
        confidence = self._calculate_confidence(image_features, similar_cases)

        # 获取时间戳
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return DiagnosisReport(
            diagnoses=diagnoses_list,
            confidence=confidence,
            findings=findings,
            recommendations=recommendations,
            similar_cases=similar_cases,
            report=report_text,
            timestamp=timestamp,
            quality_score=image_features.get("image_quality", 0.0),
        )

    def _build_prompt(
        self,
        image_features: dict,
        patient_info: dict | None,
        similar_cases: list[dict],
        medical_knowledge: list[dict],
    ) -> str:
        """构建LLM提示词"""
        prompt_parts = [
            "你是一位经验丰富的脊柱外科医生，正在为患者撰写腰椎MRI诊断报告。",
            "",
            "## 影像分析结果",
        ]

        # 添加影像发现
        if image_features.get("abnormalities"):
            prompt_parts.append("\n### 主要发现:")
            for abnorm in image_features["abnormalities"]:
                prompt_parts.append(
                    f"- {abnorm['location']}: {abnorm['description']} "
                    f"(严重程度: {abnorm['severity']})"
                )

        # 添加患者信息
        if patient_info:
            prompt_parts.append("\n## 患者信息")
            if "age" in patient_info:
                prompt_parts.append(f"年龄: {patient_info['age']}岁")
            if "gender" in patient_info:
                prompt_parts.append(f"性别: {patient_info['gender']}")
            if "symptoms" in patient_info:
                prompt_parts.append(f"主诉: {patient_info['symptoms']}")

        # 添加相似病例参考
        if similar_cases:
            prompt_parts.append("\n## 相似病例参考")
            for i, case in enumerate(similar_cases[:3], 1):
                prompt_parts.append(f"\n病例{i}:")
                prompt_parts.append(f"  诊断: {case.get('diagnosis', 'N/A')}")
                prompt_parts.append(f"  治疗: {case.get('treatment', 'N/A')}")

        # 添加医学知识
        if medical_knowledge:
            prompt_parts.append("\n## 相关医学知识")
            for knowledge in medical_knowledge:
                prompt_parts.append(f"- {knowledge.get('content', '')}")

        prompt_parts.append("\n## 任务")
        prompt_parts.append("请基于以上信息，撰写一份专业的诊断报告，包括:")
        prompt_parts.append("1. 影像描述")
        prompt_parts.append("2. 诊断结论")
        prompt_parts.append("3. 治疗建议")

        return "\n".join(prompt_parts)

    def _generate_with_llm(self, prompt: str) -> str:
        """使用LLM生成报告"""
        if self.llm_service is None:
            raise RuntimeError("LLM service not initialized")

        options = {k: v for k, v in self._llm_generate_options.items() if v is not None}
        outputs = self.llm_service.generate(prompt, **options)
        if not outputs:
            raise RuntimeError("vLLM service returned no outputs")

        generations = outputs[0].get("generations") or []
        if not generations:
            raise RuntimeError("vLLM service returned empty generations")

        text = generations[0].get("text", "")
        return text.strip()

    def _resolve_generation_options(self, vllm_cfg: dict[str, Any]) -> dict[str, Any]:
        """解析采样/生成参数供每次请求使用"""

        sampling_cfg = (
            vllm_cfg.get("sampling", {}) if isinstance(vllm_cfg.get("sampling"), dict) else {}
        )

        def _get_option(key: str, default: Any):
            if sampling_cfg.get(key) is not None:
                return sampling_cfg[key]
            if vllm_cfg.get(key) is not None:
                return vllm_cfg[key]
            return default

        try:
            max_tokens = int(_get_option("max_tokens", 768))
        except (TypeError, ValueError):
            max_tokens = 768

        try:
            temperature = float(_get_option("temperature", 0.7))
        except (TypeError, ValueError):
            temperature = 0.7

        try:
            top_p = float(_get_option("top_p", 0.95))
        except (TypeError, ValueError):
            top_p = 0.95

        return {
            "max_tokens": max(1, max_tokens),
            "temperature": max(0.0, temperature),
            "top_p": min(max(top_p, 0.0), 1.0),
        }

    def _build_vllm_config(
        self,
        llm_model: str,
        vllm_cfg: dict[str, Any],
        models_cfg: dict[str, Any],
    ) -> dict[str, Any]:
        """构建传递给 VLLMService 的配置字典"""

        engine_cfg = {}
        engine_cfg.update(
            vllm_cfg.get("engine", {}) if isinstance(vllm_cfg.get("engine"), dict) else {}
        )
        engine_cfg.setdefault("dtype", vllm_cfg.get("dtype", "auto"))
        engine_cfg.setdefault("tensor_parallel_size", int(vllm_cfg.get("tensor_parallel_size", 1)))
        engine_cfg.setdefault(
            "gpu_memory_utilization", float(vllm_cfg.get("gpu_memory_utilization", 0.9))
        )
        engine_cfg.setdefault("max_model_len", int(vllm_cfg.get("max_model_len", 4096)))

        sampling_cfg = {}
        sampling_cfg.update(
            vllm_cfg.get("sampling", {}) if isinstance(vllm_cfg.get("sampling"), dict) else {}
        )
        for key, value in self._llm_generate_options.items():
            sampling_cfg.setdefault(key, value)

        config_dict: dict[str, Any] = {
            "model_id": llm_model,
            "auto_download": bool(vllm_cfg.get("auto_download", True)),
            "auto_reload": bool(vllm_cfg.get("auto_reload", True)),
            "engine": engine_cfg,
            "sampling": sampling_cfg,
        }

        embedding_model = vllm_cfg.get("embedding_model_id") or models_cfg.get("embedding_model")
        if embedding_model:
            config_dict["embedding_model_id"] = embedding_model

        return config_dict

    def __del__(self):  # pragma: no cover - best-effort cleanup
        if getattr(self, "llm_service", None) and hasattr(self.llm_service, "cleanup"):
            with contextlib.suppress(Exception):
                self.llm_service.cleanup()

    def _generate_template_report(
        self,
        image_features: dict,
        patient_info: dict | None,
        similar_cases: list[dict],
    ) -> str:
        """使用模板生成报告（演示用）"""
        report_parts = []

        # 报告头
        report_parts.append("=" * 60)
        report_parts.append("腰椎MRI诊断报告")
        report_parts.append("=" * 60)
        report_parts.append(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_parts.append("")

        # 患者信息
        if patient_info:
            report_parts.append("【患者信息】")
            if "age" in patient_info:
                report_parts.append(f"年龄: {patient_info['age']}岁")
            if "gender" in patient_info:
                gender_cn = "男" if patient_info["gender"] == "male" else "女"
                report_parts.append(f"性别: {gender_cn}")
            if "symptoms" in patient_info:
                report_parts.append(f"主诉: {patient_info['symptoms']}")
            report_parts.append("")

        # 影像描述
        report_parts.append("【影像描述】")
        report_parts.append("腰椎序列正常，可见L1-L5椎体及L1/L2-L5/S1椎间盘。")
        report_parts.append("")

        # 主要发现
        report_parts.append("【主要发现】")
        abnormalities = image_features.get("abnormalities", [])

        if abnormalities:
            for abnorm in abnormalities:
                severity_cn = {
                    "mild": "轻度",
                    "moderate": "中度",
                    "severe": "重度",
                }.get(abnorm.get("severity", "mild"), "轻度")

                report_parts.append(
                    f"{abnorm['location']}: {abnorm['description']} ({severity_cn})"
                )
        else:
            report_parts.append("未见明显异常。")

        report_parts.append("")

        # 诊断结论
        report_parts.append("【诊断结论】")
        diagnoses = []

        for abnorm in abnormalities:
            if abnorm["type"] == "disc_herniation":
                diagnoses.append(f"{abnorm['location']}椎间盘突出症")
            elif abnorm["type"] == "disc_degeneration":
                diagnoses.append(f"{abnorm['location']}椎间盘退行性变")

        if diagnoses:
            for i, diag in enumerate(diagnoses, 1):
                report_parts.append(f"{i}. {diag}")
        else:
            report_parts.append("腰椎MRI未见明显异常。")

        report_parts.append("")

        # 治疗建议
        report_parts.append("【建议】")

        if any(a["type"] == "disc_herniation" for a in abnormalities):
            report_parts.append("1. 建议休息，避免重体力劳动")
            report_parts.append("2. 可考虑物理治疗和药物治疗")
            report_parts.append("3. 如保守治疗无效，可考虑微创或手术治疗")
            report_parts.append("4. 建议脊柱外科门诊随诊")
        elif any(a["type"] == "disc_degeneration" for a in abnormalities):
            report_parts.append("1. 注意腰部保护，避免久坐久站")
            report_parts.append("2. 适当功能锻炼，增强腰背肌力量")
            report_parts.append("3. 必要时可行保守治疗")
            report_parts.append("4. 定期复查")
        else:
            report_parts.append("1. 保持良好生活习惯")
            report_parts.append("2. 适当运动锻炼")
            report_parts.append("3. 如有症状变化，及时就诊")

        report_parts.append("")

        # 相似病例参考
        if similar_cases:
            report_parts.append("【参考病例】")
            report_parts.append(f"检索到 {len(similar_cases)} 个相似病例供参考。")

        report_parts.append("")
        report_parts.append("=" * 60)
        report_parts.append("注: 本报告由AI辅助生成，仅供参考，最终诊断需由专业医师确认。")
        report_parts.append("=" * 60)

        return "\n".join(report_parts)

    def _parse_report(self, report_text: str, image_features: dict) -> tuple:
        """解析报告提取诊断和建议"""
        # 从报告中提取诊断
        diagnoses = []
        findings = []
        recommendations = []

        # 提取异常发现
        for abnorm in image_features.get("abnormalities", []):
            findings.append(f"{abnorm['location']}: {abnorm['description']}")

            if abnorm["type"] == "disc_herniation":
                diagnoses.append(f"{abnorm['location']}椎间盘突出症")
            elif abnorm["type"] == "disc_degeneration":
                diagnoses.append(f"{abnorm['location']}椎间盘退行性变")

        # 生成建议
        has_herniation = any(
            a["type"] == "disc_herniation" for a in image_features.get("abnormalities", [])
        )

        if has_herniation:
            recommendations = [
                "建议休息，避免重体力劳动",
                "可考虑物理治疗和药物治疗",
                "如保守治疗无效，可考虑微创或手术治疗",
            ]
        else:
            recommendations = ["保持良好生活习惯", "适当运动锻炼", "定期复查"]

        diagnosis_summary = "; ".join(diagnoses) if diagnoses else "未见明显异常"

        return diagnosis_summary, findings, recommendations

    def _calculate_confidence(self, image_features: dict, similar_cases: list[dict]) -> float:
        """计算诊断置信度"""
        confidence = 0.5  # 基础置信度

        # 影像质量影响
        quality = image_features.get("image_quality", 0.5)
        confidence += quality * 0.2

        # 相似病例数量影响
        if len(similar_cases) >= 5:
            confidence += 0.2
        elif len(similar_cases) >= 3:
            confidence += 0.1

        # 异常明确性影响
        abnormalities = image_features.get("abnormalities", [])
        if abnormalities:
            # 有明确病变，置信度提升
            confidence += 0.1

        return min(confidence, 1.0)


if __name__ == "__main__":
    # 测试
    config = {"models": {"llm_model": "Qwen/Qwen2.5-7B-Instruct"}}

    generator = ReportGenerator(config)

    # 模拟数据
    image_features = {
        "abnormalities": [
            {
                "type": "disc_herniation",
                "location": "L4/L5",
                "severity": "moderate",
                "description": "L4/L5 椎间盘突出",
            }
        ],
        "image_quality": 0.85,
    }

    result = generator.generate(
        image_features=image_features,
        patient_info={"age": 45, "gender": "male", "symptoms": "腰痛"},
        similar_cases=[],
        medical_knowledge=[],
    )

    print(result.report)
