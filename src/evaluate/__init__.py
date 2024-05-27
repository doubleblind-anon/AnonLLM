import itertools
from dataclasses import dataclass

from .metrics import *

from src.evaluate.abstract_metric import AnonMetric
from src.data.abstract_task import AnonTask


@dataclass
class EvalParams:

    # dict where keys are task name, values are lists of metric to use to evaluate the task
    eval_tasks: dict[str, list[str]]
    eval_batch_size: int = None
    create_latex_table: bool = True

    @classmethod
    def from_parse(cls, eval_section: dict):

        # the eval section does not have any nested structure,
        # thus for now complex parsing is not needed
        obj = cls(**eval_section)

        # check that each eval task exists
        for task_name in obj.eval_tasks.keys():
            AnonTask.task_exists(task_name)

        # check that each metric exists
        for metric_name in itertools.chain.from_iterable(obj.eval_tasks.values()):
            AnonMetric.metric_exists(metric_name)

        return obj
