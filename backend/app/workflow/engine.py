"""工作流引擎 — 四种协同模式实现"""

import asyncio
import re
from typing import Optional, Callable

from loguru import logger

from app.browser.pool import browser_pool
from app.models import WorkflowMode, WorkflowStep, InstanceStatus
from app.workflow.bus import message_bus, BusMessage, MessageType


class StepResult:
    """步骤执行结果"""
    def __init__(self, step_id: str, output: str, success: bool = True, error: Optional[str] = None):
        self.step_id = step_id
        self.output = output
        self.success = success
        self.error = error


class WorkflowEngine:
    """工作流引擎 — 实现四种协同模式"""

    def __init__(self):
        self._running = False
        self._paused = False
        self._abort = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def abort(self):
        self._abort = True

    async def _wait_if_paused(self):
        """等待暂停恢复"""
        while self._paused:
            await asyncio.sleep(0.5)
            if self._abort:
                raise asyncio.CancelledError("工作流已终止")

    async def _execute_step(self, step: WorkflowStep, context: dict,
                            on_log: Optional[Callable] = None) -> StepResult:
        """执行单个步骤"""
        instance = browser_pool.get(step.instance_id)
        if not instance:
            return StepResult(step.id, "", success=False, error=f"实例 {step.instance_id} 不存在")

        if instance.status not in (InstanceStatus.ONLINE, InstanceStatus.BUSY):
            return StepResult(step.id, "", success=False, error=f"实例 {step.instance_id} 状态异常: {instance.status.value}")

        # 渲染 prompt 模板
        prompt = self._render_template(step.prompt_template, context)
        if on_log:
            on_log(step.id, f"发送 prompt ({len(prompt)} 字): {prompt[:100]}...")

        # 发送消息
        for attempt in range(step.retries + 1):
            try:
                await self._wait_if_paused()
                response = await instance.send_message(prompt)
                if on_log:
                    on_log(step.id, f"收到回复 ({len(response)} 字): {response[:100]}...")

                # 通过消息总线广播
                await message_bus.send(BusMessage(
                    workflow_run_id=context.get("workflow_run_id", ""),
                    step_id=step.id,
                    source_id=step.instance_id,
                    msg_type=MessageType.RESPONSE,
                    content=response,
                ))

                return StepResult(step.id, response)

            except Exception as e:
                if attempt < step.retries:
                    logger.warning(f"[Engine] 步骤 {step.id} 失败，重试 {attempt + 1}/{step.retries}: {e}")
                    await asyncio.sleep(2)
                else:
                    return StepResult(step.id, "", success=False, error=str(e))

    def _render_template(self, template: str, context: dict) -> str:
        """渲染模板（支持 {user.input}, {prev.output}, {step_id.output} 等变量）"""
        result = template
        # 替换 {user.input}
        result = result.replace("{user.input}", context.get("user_input", ""))
        # 替换 {prev.output}
        result = result.replace("{prev.output}", context.get("prev_output", ""))
        # 替换 {step_id.output}
        for key, value in context.items():
            if key.endswith(".output"):
                result = result.replace(f"{{{key}}}", str(value))
        # 替换 {var.xxx}
        for key, value in context.get("variables", {}).items():
            result = result.replace(f"{{var.{key}}}", str(value))
        return result

    # ── 流水线（Pipeline）────────────────────────

    async def run_pipeline(self, steps: list[WorkflowStep], user_input: str,
                           workflow_run_id: str = "",
                           on_log: Optional[Callable] = None) -> list[StepResult]:
        """
        流水线模式：A → B → C
        每个 AI 负责一个环节，上一个的输出是下一个的输入。
        """
        results = []
        context = {
            "user_input": user_input,
            "workflow_run_id": workflow_run_id,
        }

        for i, step in enumerate(steps):
            await self._wait_if_paused()
            if self._abort:
                break

            if on_log:
                on_log(step.id, f"▶ 执行步骤 {i + 1}/{len(steps)}: {step.name}")

            result = await self._execute_step(step, context, on_log)
            results.append(result)

            if not result.success:
                if on_log:
                    on_log(step.id, f"❌ 步骤失败: {result.error}")
                break

            # 更新上下文
            context["prev_output"] = result.output
            context[f"{step.id}.output"] = result.output

        return results

    # ── 圆桌讨论（Roundtable）──────────────────

    async def run_roundtable(self, steps: list[WorkflowStep], user_input: str,
                             rounds: int = 1, workflow_run_id: str = "",
                             on_log: Optional[Callable] = None) -> list[StepResult]:
        """
        圆桌讨论模式：
        话题 → [AI-A 发言] → [AI-B 回应] → [AI-C 补充] → 第2轮 → ... → 总结
        每个 AI 都能看到前面所有人的发言。
        """
        results = []
        discussion_history = f"讨论话题：{user_input}\n\n"

        for round_num in range(rounds):
            if on_log:
                on_log("_round", f"🔄 第 {round_num + 1}/{rounds} 轮讨论")

            for i, step in enumerate(steps):
                await self._wait_if_paused()
                if self._abort:
                    break

                if on_log:
                    on_log(step.id, f"💬 {step.name} 发言中...")

                # 构造上下文：讨论历史 + 当前发言要求
                context = {
                    "user_input": user_input,
                    "prev_output": discussion_history,
                    "workflow_run_id": workflow_run_id,
                }

                result = await self._execute_step(step, context, on_log)
                results.append(result)

                if result.success:
                    discussion_history += f"\n【{step.name}】：\n{result.output}\n"
                else:
                    discussion_history += f"\n【{step.name}】：（发言失败：{result.error}）\n"

        return results

    # ── 审核循环（Review Loop）──────────────────

    async def run_review_loop(self, steps: list[WorkflowStep], user_input: str,
                              max_iterations: int = 3, workflow_run_id: str = "",
                              on_log: Optional[Callable] = None) -> list[StepResult]:
        """
        审核循环模式：
        任务 → [Coder 写] → [Reviewer 审] → 不通过 → [Coder 改] → [Reviewer 审] → 通过 → 输出

        steps[0] = Coder（执行者）
        steps[1] = Reviewer（审核者）
        """
        if len(steps) < 2:
            raise ValueError("审核循环至少需要 2 个步骤（Coder + Reviewer）")

        coder_step = steps[0]
        reviewer_step = steps[1]
        results = []
        current_output = ""

        for iteration in range(max_iterations):
            await self._wait_if_paused()
            if self._abort:
                break

            if on_log:
                on_log("_loop", f"🔁 第 {iteration + 1}/{max_iterations} 轮")

            # 1. Coder 执行
            coder_context = {
                "user_input": user_input,
                "prev_output": current_output if iteration > 0 else user_input,
                "workflow_run_id": workflow_run_id,
            }
            if iteration > 0:
                coder_step.prompt_template = (
                    f"请根据以下审核意见修改：\n审核意见：{results[-1].output}\n\n"
                    f"原始内容：\n{current_output}\n\n请修改。"
                )

            coder_result = await self._execute_step(coder_step, coder_context, on_log)
            results.append(coder_result)

            if not coder_result.success:
                break

            current_output = coder_result.output

            # 2. Reviewer 审核
            reviewer_context = {
                "user_input": user_input,
                "prev_output": current_output,
                "workflow_run_id": workflow_run_id,
            }
            reviewer_result = await self._execute_step(reviewer_step, reviewer_context, on_log)
            results.append(reviewer_result)

            if not reviewer_result.success:
                break

            # 检查审核结果
            review_text = reviewer_result.output.lower()
            if "通过" in review_text or "approve" in review_text or "合格" in review_text:
                if on_log:
                    on_log(reviewer_step.id, "✅ 审核通过")
                break
            else:
                if on_log:
                    on_log(reviewer_step.id, f"❌ 审核未通过，需要修改")

        return results

    # ── 辩论赛（Debate）────────────────────────

    async def run_debate(self, steps: list[WorkflowStep], user_input: str,
                         workflow_run_id: str = "",
                         on_log: Optional[Callable] = None) -> list[StepResult]:
        """
        辩论赛模式：
        辩题 → [正方 AI 发言] → [反方 AI 反驳] → ... → [评委 AI 总结]

        steps[:-1] = 辩手（正方/反方交替）
        steps[-1] = 评委（总结）
        """
        if len(steps) < 2:
            raise ValueError("辩论至少需要 2 个步骤（辩手 + 评委）")

        debaters = steps[:-1]
        judge = steps[-1]
        results = []
        debate_history = f"辩题：{user_input}\n\n"

        # 辩论环节
        for i, step in enumerate(debaters):
            await self._wait_if_paused()
            if self._abort:
                break

            side = "正方" if i % 2 == 0 else "反方"
            if on_log:
                on_log(step.id, f"🗣️ {side} ({step.name}) 发言...")

            context = {
                "user_input": user_input,
                "prev_output": debate_history,
                "workflow_run_id": workflow_run_id,
            }

            result = await self._execute_step(step, context, on_log)
            results.append(result)

            if result.success:
                debate_history += f"\n【{side} - {step.name}】：\n{result.output}\n"

        # 评委总结
        if not self._abort:
            if on_log:
                on_log(judge.id, "⚖️ 评委总结中...")

            judge_context = {
                "user_input": user_input,
                "prev_output": debate_history,
                "workflow_run_id": workflow_run_id,
            }
            judge_result = await self._execute_step(judge, judge_context, on_log)
            results.append(judge_result)

        return results
