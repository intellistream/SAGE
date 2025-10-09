"""
报告生成Agent
负责生成结构化的诊断报告
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class DiagnosisReport:
    """诊断报告"""
    diagnoses: List[str]  # 诊断列表
    confidence: float  # 置信度
    findings: List[str]  # 发现列表
    recommendations: List[str]  # 建议列表
    similar_cases: List[Dict[str, Any]]  # 相似病例
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
    
    def __init__(self, config: Dict):
        """
        初始化报告生成器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.llm_service = None
        self._setup_llm()
    
    def _setup_llm(self):
        """设置LLM服务"""
        print(f"   Loading LLM: {self.config['models']['llm_model']}")
        
        # TODO: 集成 SAGE VLLMService
        # Issue URL: https://github.com/intellistream/SAGE/issues/901
    # from sage.common.components.sage_vllm.service import VLLMService
        # self.llm_service = VLLMService(...)
        
        self.llm_service = "placeholder"
    
    def generate(
        self,
        image_features: Dict[str, Any],
        patient_info: Optional[Dict[str, Any]],
        similar_cases: List[Dict],
        medical_knowledge: List[Dict]
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
        prompt = self._build_prompt(
            image_features,
            patient_info,
            similar_cases,
            medical_knowledge
        )
        
        # Step 2: 调用LLM生成报告
        if self.llm_service != "placeholder":
            report_text = self._generate_with_llm(prompt)
        else:
            # 使用模板生成（演示用）
            report_text = self._generate_template_report(
                image_features,
                patient_info,
                similar_cases
            )
        
        # Step 3: 提取诊断和建议
        diagnosis_summary, findings, recommendations = self._parse_report(
            report_text,
            image_features
        )
        
        # 提取诊断列表
        diagnoses_list = []
        for abnorm in image_features.get('abnormalities', []):
            if abnorm['type'] == 'disc_herniation':
                diagnoses_list.append(f"{abnorm['location']}椎间盘突出症")
            elif abnorm['type'] == 'disc_degeneration':
                diagnoses_list.append(f"{abnorm['location']}椎间盘退行性变")
        
        if not diagnoses_list:
            diagnoses_list = ["未见明显异常"]
        
        # Step 4: 计算置信度
        confidence = self._calculate_confidence(
            image_features,
            similar_cases
        )
        
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
            quality_score=image_features.get('image_quality', 0.0)
        )
    
    def _build_prompt(
        self,
        image_features: Dict,
        patient_info: Optional[Dict],
        similar_cases: List[Dict],
        medical_knowledge: List[Dict]
    ) -> str:
        """构建LLM提示词"""
        prompt_parts = [
            "你是一位经验丰富的脊柱外科医生，正在为患者撰写腰椎MRI诊断报告。",
            "",
            "## 影像分析结果",
        ]
        
        # 添加影像发现
        if image_features.get('abnormalities'):
            prompt_parts.append("\n### 主要发现:")
            for abnorm in image_features['abnormalities']:
                prompt_parts.append(
                    f"- {abnorm['location']}: {abnorm['description']} "
                    f"(严重程度: {abnorm['severity']})"
                )
        
        # 添加患者信息
        if patient_info:
            prompt_parts.append("\n## 患者信息")
            if 'age' in patient_info:
                prompt_parts.append(f"年龄: {patient_info['age']}岁")
            if 'gender' in patient_info:
                prompt_parts.append(f"性别: {patient_info['gender']}")
            if 'symptoms' in patient_info:
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
        # TODO: 调用VLLMService
        # Issue URL: https://github.com/intellistream/SAGE/issues/900
        # response = self.llm_service.generate(
        #     prompt=prompt,
        #     max_tokens=1024,
        #     temperature=0.7
        # )
        # return response.text
        return ""
    
    def _generate_template_report(
        self,
        image_features: Dict,
        patient_info: Optional[Dict],
        similar_cases: List[Dict]
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
            if 'age' in patient_info:
                report_parts.append(f"年龄: {patient_info['age']}岁")
            if 'gender' in patient_info:
                gender_cn = "男" if patient_info['gender'] == 'male' else "女"
                report_parts.append(f"性别: {gender_cn}")
            if 'symptoms' in patient_info:
                report_parts.append(f"主诉: {patient_info['symptoms']}")
            report_parts.append("")
        
        # 影像描述
        report_parts.append("【影像描述】")
        report_parts.append(f"腰椎序列正常，可见L1-L5椎体及L1/L2-L5/S1椎间盘。")
        report_parts.append("")
        
        # 主要发现
        report_parts.append("【主要发现】")
        abnormalities = image_features.get('abnormalities', [])
        
        if abnormalities:
            for abnorm in abnormalities:
                severity_cn = {
                    'mild': '轻度',
                    'moderate': '中度',
                    'severe': '重度'
                }.get(abnorm.get('severity', 'mild'), '轻度')
                
                report_parts.append(f"{abnorm['location']}: {abnorm['description']} ({severity_cn})")
        else:
            report_parts.append("未见明显异常。")
        
        report_parts.append("")
        
        # 诊断结论
        report_parts.append("【诊断结论】")
        diagnoses = []
        
        for abnorm in abnormalities:
            if abnorm['type'] == 'disc_herniation':
                diagnoses.append(f"{abnorm['location']}椎间盘突出症")
            elif abnorm['type'] == 'disc_degeneration':
                diagnoses.append(f"{abnorm['location']}椎间盘退行性变")
        
        if diagnoses:
            for i, diag in enumerate(diagnoses, 1):
                report_parts.append(f"{i}. {diag}")
        else:
            report_parts.append("腰椎MRI未见明显异常。")
        
        report_parts.append("")
        
        # 治疗建议
        report_parts.append("【建议】")
        
        if any(a['type'] == 'disc_herniation' for a in abnormalities):
            report_parts.append("1. 建议休息，避免重体力劳动")
            report_parts.append("2. 可考虑物理治疗和药物治疗")
            report_parts.append("3. 如保守治疗无效，可考虑微创或手术治疗")
            report_parts.append("4. 建议脊柱外科门诊随诊")
        elif any(a['type'] == 'disc_degeneration' for a in abnormalities):
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
    
    def _parse_report(
        self,
        report_text: str,
        image_features: Dict
    ) -> tuple:
        """解析报告提取诊断和建议"""
        # 从报告中提取诊断
        diagnoses = []
        findings = []
        recommendations = []
        
        # 提取异常发现
        for abnorm in image_features.get('abnormalities', []):
            findings.append(f"{abnorm['location']}: {abnorm['description']}")
            
            if abnorm['type'] == 'disc_herniation':
                diagnoses.append(f"{abnorm['location']}椎间盘突出症")
            elif abnorm['type'] == 'disc_degeneration':
                diagnoses.append(f"{abnorm['location']}椎间盘退行性变")
        
        # 生成建议
        has_herniation = any(
            a['type'] == 'disc_herniation' 
            for a in image_features.get('abnormalities', [])
        )
        
        if has_herniation:
            recommendations = [
                "建议休息，避免重体力劳动",
                "可考虑物理治疗和药物治疗",
                "如保守治疗无效，可考虑微创或手术治疗"
            ]
        else:
            recommendations = [
                "保持良好生活习惯",
                "适当运动锻炼",
                "定期复查"
            ]
        
        diagnosis_summary = "; ".join(diagnoses) if diagnoses else "未见明显异常"
        
        return diagnosis_summary, findings, recommendations
    
    def _calculate_confidence(
        self,
        image_features: Dict,
        similar_cases: List[Dict]
    ) -> float:
        """计算诊断置信度"""
        confidence = 0.5  # 基础置信度
        
        # 影像质量影响
        quality = image_features.get('image_quality', 0.5)
        confidence += quality * 0.2
        
        # 相似病例数量影响
        if len(similar_cases) >= 5:
            confidence += 0.2
        elif len(similar_cases) >= 3:
            confidence += 0.1
        
        # 异常明确性影响
        abnormalities = image_features.get('abnormalities', [])
        if abnormalities:
            # 有明确病变，置信度提升
            confidence += 0.1
        
        return min(confidence, 1.0)


if __name__ == "__main__":
    # 测试
    config = {
        "models": {
            "llm_model": "Qwen/Qwen2.5-7B-Instruct"
        }
    }
    
    generator = ReportGenerator(config)
    
    # 模拟数据
    image_features = {
        "abnormalities": [
            {
                "type": "disc_herniation",
                "location": "L4/L5",
                "severity": "moderate",
                "description": "L4/L5 椎间盘突出"
            }
        ],
        "image_quality": 0.85
    }
    
    result = generator.generate(
        image_features=image_features,
        patient_info={"age": 45, "gender": "male", "symptoms": "腰痛"},
        similar_cases=[],
        medical_knowledge=[]
    )
    
    print(result.report)
