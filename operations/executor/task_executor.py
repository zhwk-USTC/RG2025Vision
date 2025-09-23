# tasks/task_executor.py
import threading
import time
from typing import List, Dict, Any, Optional

from core.logger import logger
from ..debug_vars_enhanced import reset_debug_vars, set_debug_var, DebugLevel, DebugCategory
from ..nodes import _TASK_NODE_CLASSES, _COND_NODE_CLASSES
from operations.config.operation_config import OperationNodeConfig


class TaskStoppedException(Exception):
    pass


# ---- 全局线程状态 ----
_current_thread: Optional[threading.Thread] = None
_stop_requested: bool = False


def stop():
    """请求停止任务，在节点执行前会检查"""
    global _stop_requested
    _stop_requested = True
    set_debug_var(
        'task_process_stop_requested',
        True,
        DebugLevel.WARNING,
        DebugCategory.STATUS,
        "用户请求停止任务流程"
    )


def is_stop_requested() -> bool:
    return _stop_requested


def check_stop_request():
    if is_stop_requested():
        raise TaskStoppedException("Task stopped by user request")


class TaskExecutor:
    """
    任务执行器：伪线性执行
      - task: 顺序执行
      - condition: 条件为 True 顺序继续；False 跳到 同 id 的 target 节点
      - target: 占位锚点，到达后顺序继续
    """

    def __init__(self):
        self.flow: List[OperationNodeConfig] = []
        self.execution_context: Dict[str, Any] = {}

    def load_from_config(self):
        """从配置文件加载执行流程"""
        try:
            from operations.config.operation_config import get_current_operation
            config = get_current_operation()
            # 读取 nodes
            self.flow = list(config.nodes) if getattr(config, "nodes", None) else []
        except Exception as e:
            logger.error(f"加载执行流程配置失败: {e}")
            self.flow = []

    def execute(self) -> bool:
        """执行流程"""
        global _stop_requested
        _stop_requested = False  # 每次执行前重置

        # 每次执行前重置执行上下文，确保状态不会跨执行保留
        self.execution_context.clear()

        self.load_from_config()
        try:
            # 启动前运行 system_init
            self._execute_task_node('system_init', 'system_init', {})

            if not self.flow:
                logger.error("没有可执行的流程配置")
                return False

            reset_debug_vars()
            set_debug_var('task_process_status', 'starting', DebugLevel.INFO, DebugCategory.STATUS, "任务流程开始")
            set_debug_var('flow_config', [getattr(n, 'id', '?') for n in self.flow],
                          DebugLevel.INFO, DebugCategory.STATUS, f"流程配置: {len(self.flow)} 个节点")

            # 仅为 target 节点建表：id -> index
            target_map: Dict[str, int] = {
                n.id: idx
                for idx, n in enumerate(self.flow)
                if getattr(n, "id", None) and getattr(n, "type", None) == "target"
            }

            has_failed_tasks = False  # 跟踪是否有任务失败

            i = 0
            while i < len(self.flow):
                if is_stop_requested():
                    raise TaskStoppedException(f"Task stopped before node {self.flow[i].id}")

                node = self.flow[i]
                node_id: str = getattr(node, 'id', f'#{i}')
                node_type: str = getattr(node, 'type', 'unknown')
                class_name: str = getattr(node, 'name', '')  # OperationNode 的 name 字段即类名
                params: Dict[str, Any] = getattr(node, 'parameters', {}) or {}

                set_debug_var('current_node', node_id, DebugLevel.INFO, DebugCategory.STATUS,
                              f"当前节点：ID {node_id}, 类型 {node_type}, 类名 {class_name}")

                if node_type == 'task':
                    ok = self._execute_task_node(node_id, class_name, params)
                    self.execution_context[node_id] = ok
                    self.execution_context['last_result'] = ok
                    if not ok:
                        has_failed_tasks = True
                        set_debug_var('task_failed', node_id, DebugLevel.WARNING, DebugCategory.ERROR,
                                      f"任务节点 {node_id} 执行失败，继续下一个任务")
                        logger.warning(f"任务节点 {node_id} 执行失败，继续执行下一个任务")
                    i += 1

                elif node_type == 'condition':
                    next_idx = self._execute_condition_node(node_id, class_name, params, target_map)
                    i = next_idx if next_idx is not None else (i + 1)

                elif node_type == 'note':
                    self._execute_note_node(node_id, class_name, params)
                    i += 1
                    
                elif node_type == 'target':
                    i += 1

                else:
                    logger.warning(f"未知节点类型: {node_type}")
                    i += 1

            if has_failed_tasks:
                set_debug_var('task_process_status', 'completed_with_failures',
                              DebugLevel.WARNING, DebugCategory.STATUS,
                              f"任务流程完成但有失败任务：共处理 {len(self.flow)} 个节点")
                logger.warning("任务流程完成，但存在失败的任务")
                return False
            else:
                set_debug_var('task_process_status', 'completed_normally',
                              DebugLevel.SUCCESS, DebugCategory.STATUS,
                              f"任务流程正常完成：共处理 {len(self.flow)} 个节点")
                return True

        except TaskStoppedException as e:
            set_debug_var('task_process_status', f'stopped: {e}', DebugLevel.WARNING, DebugCategory.STATUS,
                          f"任务流程被用户停止: {e}")
            return False

        except Exception as e:
            set_debug_var('task_process_status', f'error: {e}', DebugLevel.ERROR, DebugCategory.ERROR,
                          f"任务流程执行异常: {e}")
            return False

        finally:
            # 结束前运行 system_cleanup
            self._execute_task_node('system_cleanup', 'system_cleanup', {})

    # ---------- 子步骤：任务节点 ----------
    def _execute_task_node(self, node_id: str, class_name: str, parameters: Dict[str, Any]) -> bool:
        """执行任务节点（OperationNode.name 为任务类名）"""
        if not class_name or not isinstance(class_name, str):
            set_debug_var('error', f'Missing class name for task {node_id}',
                          DebugLevel.ERROR, DebugCategory.ERROR, f"任务 {node_id} 缺少类名（name）")
            return False

        step_cls = _TASK_NODE_CLASSES.get(class_name)
        if not step_cls:
            set_debug_var('error', f'Unknown task class: {class_name}', DebugLevel.ERROR, DebugCategory.ERROR,
                          f"未知任务类: {class_name}")
            return False

        task_kwargs = dict(parameters)  # 全量透传 parameters
        if task_kwargs:
            set_debug_var('step_params', task_kwargs, DebugLevel.INFO, DebugCategory.STATUS,
                          f"步骤参数: {task_kwargs}")

        try:
            result = step_cls(**task_kwargs).run()
            ok = (result is not False)
            set_debug_var(f'task_{node_id}_raw_result', repr(result), DebugLevel.INFO, DebugCategory.STATUS,
                        f"任务 {node_id} 原始返回: {result!r}")
            set_debug_var(f'task_{node_id}_result', ok, DebugLevel.INFO, DebugCategory.STATUS,
                        f"任务 {node_id} 判定结果: {ok}")
            return ok
        except Exception as e:
            set_debug_var('task_error', f'Task {node_id} exception: {e}',
                          DebugLevel.ERROR, DebugCategory.ERROR, f"任务 {node_id} 执行异常: {e}")
            return False

    # ---------- 子步骤：条件节点 ----------
    def _execute_condition_node(
        self,
        node_id: str,
        class_name: str,
        parameters: Dict[str, Any],
        target_map: Dict[str, int],
    ) -> Optional[int]:
        """执行条件节点：run() -> bool，False 跳转到同 id 的 target 节点"""
        if not class_name or not isinstance(class_name, str):
            set_debug_var(
                "condition_config_error",
                {"node_id": node_id, "missing": "name(class)"},
                DebugLevel.ERROR, DebugCategory.ERROR,
                f"条件节点 {node_id} 缺少类名（name）"
            )
            return None

        condition_cls = _COND_NODE_CLASSES.get(class_name)
        if not condition_cls:
            set_debug_var(
                "condition_lookup_error",
                class_name,
                DebugLevel.ERROR, DebugCategory.ERROR,
                f"未找到条件类: {class_name}"
            )
            return None

        cond_kwargs = dict(parameters)
        try:
            set_debug_var(
                "condition_run",
                {"class": class_name, "kwargs": cond_kwargs},
                DebugLevel.INFO, DebugCategory.STATUS,
                f"执行条件类 {class_name}"
            )
            result_bool = bool(condition_cls(**cond_kwargs).run())
        except Exception as e:
            set_debug_var(
                "condition_run_error",
                str(e),
                DebugLevel.ERROR, DebugCategory.ERROR,
                f"条件类 {class_name} 运行异常: {e}"
            )
            return None

        self.execution_context[node_id] = result_bool
        self.execution_context["last_result"] = result_bool

        set_debug_var(
            f"condition_{node_id}_result",
            result_bool,
            DebugLevel.INFO, DebugCategory.STATUS,
            f"条件节点 {class_name} 结果: {result_bool}"
        )

        # True 顺序继续，False 跳到“同 id 的 target 节点”
        if result_bool:
            return None

        target_idx = target_map.get(node_id)
        if target_idx is None:
            set_debug_var(
                "jump_target_missing",
                node_id,
                DebugLevel.ERROR, DebugCategory.ERROR,
                f"未找到与条件节点 {node_id} 对应的 target 节点（请添加 type='target', id='{node_id}'）"
            )
            return None

        return target_idx
    # ---------- 子步骤：注释（note）节点 ----------
    def _execute_note_node(self, node_id: str, name: str, parameters: Dict[str, Any]) -> None:
        text = parameters.get('text')
        if text is None or text == '':
            text = name or node_id
        if not isinstance(text, str):
            try:
                text = repr(text)
            except Exception:
                text = str(text)

        preview = text if len(text) <= 1000 else (text[:1000] + '…')
        logger.info(f"[NOTE] {node_id}: {preview}")
        set_debug_var(
            f"note_{node_id}",
            {"text": preview},
            DebugLevel.INFO,
            DebugCategory.STATUS,
            f"注释节点 {node_id}"
        )


# ---- 全局执行器实例 ----
_task_executor = TaskExecutor()


def run_tasks_process() -> bool:
    return _task_executor.execute()


def is_task_process_running() -> bool:
    global _current_thread
    return _current_thread is not None and _current_thread.is_alive()


def start_task_process_thread() -> threading.Thread:
    global _current_thread
    if is_task_process_running():
        stop()
        time.sleep(0.1)

    def _worker():
        try:
            run_tasks_process()
        finally:
            global _current_thread
            _current_thread = None

    _current_thread = threading.Thread(target=_worker, daemon=True)
    _current_thread.start()
    return _current_thread
