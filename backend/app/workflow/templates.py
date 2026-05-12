"""预置工作流模板"""

from app.models import WorkflowMode, WorkflowStep


TEMPLATES = {
    "article-pipeline": {
        "name": "文章流水线",
        "description": "大纲 → 初稿 → 审核，三步生成高质量文章",
        "mode": WorkflowMode.PIPELINE,
        "steps": [
            WorkflowStep(
                id="outline",
                name="生成大纲",
                instance_id="",  # 用户指定
                prompt_template="请为以下主题生成详细大纲，包含 3-5 个主要章节，每个章节有 2-3 个要点：\n\n主题：{user.input}",
                timeout=120,
            ),
            WorkflowStep(
                id="draft",
                name="写初稿",
                instance_id="",
                prompt_template="根据以下大纲写一篇完整文章（约 1500 字），要求语言流畅、逻辑清晰：\n\n大纲：\n{prev.output}",
                timeout=300,
            ),
            WorkflowStep(
                id="review",
                name="审核润色",
                instance_id="",
                prompt_template="请审核以下文章，指出问题并给出修改建议，最后给出修改后的完整版本：\n\n{prev.output}",
                timeout=300,
            ),
        ],
    },

    "code-review-loop": {
        "name": "代码审核循环",
        "description": "写代码 → 审核 → 修改 → 再审核，直到通过",
        "mode": WorkflowMode.REVIEW_LOOP,
        "steps": [
            WorkflowStep(
                id="coder",
                name="开发者",
                instance_id="",
                prompt_template="请根据以下需求编写代码：\n\n{user.input}",
                timeout=300,
            ),
            WorkflowStep(
                id="reviewer",
                name="审核者",
                instance_id="",
                prompt_template="请审核以下代码，检查：1) 正确性 2) 可读性 3) 性能 4) 安全性。如果通过请说「通过」，否则指出问题：\n\n{prev.output}",
                timeout=180,
            ),
        ],
    },

    "multi-perspective": {
        "name": "多角度分析",
        "description": "多个 AI 从不同角度分析同一问题",
        "mode": WorkflowMode.ROUNDTABLE,
        "steps": [
            WorkflowStep(
                id="analyst",
                name="数据分析师",
                instance_id="",
                prompt_template="作为数据分析师，请从数据和事实角度分析以下话题：\n\n{prev.output}",
                timeout=180,
            ),
            WorkflowStep(
                id="strategist",
                name="战略顾问",
                instance_id="",
                prompt_template="作为战略顾问，请从商业和战略角度分析以下话题，回应前面分析师的观点：\n\n{prev.output}",
                timeout=180,
            ),
            WorkflowStep(
                id="critic",
                name="批判性思考者",
                instance_id="",
                prompt_template="作为批判性思考者，请指出前面分析中的盲点和不足，补充被忽略的角度：\n\n{prev.output}",
                timeout=180,
            ),
        ],
    },

    "debate": {
        "name": "AI 辩论赛",
        "description": "正反双方辩论 + 评委总结",
        "mode": WorkflowMode.DEBATE,
        "steps": [
            WorkflowStep(
                id="pro",
                name="正方",
                instance_id="",
                prompt_template="你是正方辩手。请为以下辩题提出 3 个有力论点，每个论点用事实或逻辑支撑：\n\n辩题：{user.input}",
                timeout=180,
            ),
            WorkflowStep(
                id="con",
                name="反方",
                instance_id="",
                prompt_template="你是反方辩手。请针对正方的论点逐一反驳，并提出你自己的 3 个论点：\n\n{prev.output}",
                timeout=180,
            ),
            WorkflowStep(
                id="judge",
                name="评委",
                instance_id="",
                prompt_template="你是评委。请客观评价正反双方的论点，指出各自的强项和弱点，最后给出你的裁决和理由：\n\n{prev.output}",
                timeout=240,
            ),
        ],
    },

    "translate-review": {
        "name": "翻译校对",
        "description": "翻译 → 校对 → 润色",
        "mode": WorkflowMode.PIPELINE,
        "steps": [
            WorkflowStep(
                id="translate",
                name="翻译",
                instance_id="",
                prompt_template="请将以下内容翻译为英文，保持原意和风格：\n\n{user.input}",
                timeout=180,
            ),
            WorkflowStep(
                id="proofread",
                name="校对",
                instance_id="",
                prompt_template="请校对以下翻译，检查语法错误、用词不当、意思偏差，给出修改建议和修正后的版本：\n\n{prev.output}",
                timeout=180,
            ),
        ],
    },
}


def get_template(template_id: str) -> dict | None:
    """获取模板"""
    return TEMPLATES.get(template_id)


def list_templates() -> list[dict]:
    """列出所有模板"""
    return [
        {
            "id": tid,
            "name": t["name"],
            "description": t["description"],
            "mode": t["mode"].value,
            "step_count": len(t["steps"]),
        }
        for tid, t in TEMPLATES.items()
    ]
