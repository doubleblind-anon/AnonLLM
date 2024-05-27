# Sample Experiments

This directory contains all the `.yml` config files and results of *Experiment 2* and *Experiment 3*:
- **Experiment 2** aims at assessing, in a reproducible environment thanks to *AnonLLM*, the impact of the personalization strategy introduced in the [P5 paper](https://arxiv.org/pdf/2203.13366.pdf),
by using the same prompts defined in the mentioned paper
- **Experiment 3** aims at evaluating AnonLLM performances by varying the LLM backbone and use a novel set of more informative prompts.
Majority of the runs overcame results of the mentioned *P5 paper*. The new set of prompts can be found [here](https://doubleblind-anon.github.io/AnonLLM/yaml_usage/available_implementations/available_tasks/)

Each result directory contains a table storing metrics results for each task in both `.csv` and `.tex` format, generated with *AnonLLM*.

All runs have been tracked with **WandB**. The full workspace is available by clicking the following image:

<p align="center">
  <a href="https://github.com/doubleblind-anon/AnonLLM/tree/main/sample_experiments/redirect_wandb_links.txt" > 
    <img src="https://raw.githubusercontent.com/wandb/assets/main/wandb-logo-yellow-dots-black-wb.svg" alt="Visualize runs in WandB workspace" width="20%"/>
  </a>
</p>

**Note**: additional experiments can be found in the [`other_exp`](other_exp) subfolder!

## Experiment 2 results

These are the results of the T5-S LLM, with (***+W***) and without personalization, when trained and evaluated on the *Sequential*, *Direct* and *Rating Prediction* 
tasks with the **P5 prompts**. The *P5 prompts* used can be found [here](https://doubleblind-anon.github.io/AnonLLM/yaml_usage/available_implementations/available_tasks/#p5-tasks)

The evaluation is carried out on a *seen* prompt and an *unseen* one.
<p align="center">
    <img src="exp2_results.png" alt="Experiment 2 results"/>
</p>

- **T5-S**: [[.yml config](exp2/exp2_t5_s.yml)][[Results directory](exp2/metrics_results/exp2_t5_s)][[Visualize in WandB](redirect_wandb_links.txt)]
- **T5-S + W**: [[.yml config](exp2/exp2_t5_s+w.yml)][[Results directory](exp2/metrics_results/exp2_t5_s+w)][[Visualize in WandB](redirect_wandb_links.txt)]


## Experiment 3 results

These are the results of T5-S, FlanT5-S, FlanT5-B, GPT2, with (***+W***) and without personalization, when trained and evaluated on the *Sequential*, *Direct* and *Rating Prediction*
tasks with the novel set of prompts defined in AnonLLM. The evaluation is carried out on all prompts, already *seen* by the model during the fine-tuning phase,
and in the following table there are reported the best results for each metric achieved by any prompt of the specific task (*best-seen*).
<p align="center">
    <img src="exp3_results.png" alt="Experiment 3 results" width="90%"/>
</p>

### T5 Runs

- **T5-S**: [[.yml config](exp3/exp3_t5_s.yml)][[Results directory](exp3/metrics_results/exp3_t5_s)][[Visualize in WandB](redirect_wandb_links.txt)]
- **T5-S + W**: [[.yml config](exp3/exp3_t5_s+w.yml)][[Results directory](exp3/metrics_results/exp3_t5_s+w)][[Visualize in WandB](redirect_wandb_links.txt)]

### Flan T5 Runs

- **FlanT5-S**: [[.yml config](exp3/exp3_flan_t5_s.yml)][[Results directory](exp3/metrics_results/exp3_flan_t5_s)][[Visualize in WandB](redirect_wandb_links.txt)]
- **FlanT5-S + W**: [[.yml config](exp3/exp3_flan_t5_s+w.yml)][[Results directory](exp3/metrics_results/exp3_flan_t5_s+w)][[Visualize in WandB](redirect_wandb_links.txt)]
- **FlanT5-B**: [[.yml config](exp3/exp3_flan_t5_b.yml)][[Results directory](exp3/metrics_results/exp3_flan_t5_b)][[Visualize in WandB](redirect_wandb_links.txt)]
- **FlanT5-B + W**: [[.yml config](exp3/exp3_flan_t5_b+w.yml)][[Results directory](exp3/metrics_results/exp3_flan_t5_b+w)][[Visualize in WandB](redirect_wandb_links.txt)]

### GPT2 Runs

- **GPT2**: [[.yml config](exp3/exp3_gpt2.yml)][[Results directory](exp3/metrics_results/exp3_gpt2)][[Visualize in WandB](redirect_wandb_links.txt)]
- **GPT2 + W**: [[.yml config](exp3/exp3_gpt2+w.yml)][[Results directory](exp3/metrics_results/exp3_gpt2+w)][[Visualize in WandB](redirect_wandb_links.txt)]
