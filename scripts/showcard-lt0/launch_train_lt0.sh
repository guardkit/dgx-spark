#!/bin/bash
#
# SPDX-FileCopyrightText: Copyright (c) 1993-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the License);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an AS IS BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ---------------------------------------------------------------------------
# showcard LT-0 launcher — MIRRORS the playbook launch_train.sh FLAG-FOR-FLAG
# (nvidia/flux-finetuning/assets/launch_train.sh). The playbook defaults ARE the
# recorded training config; this file changes NOTHING about them. Deviations,
# exhaustively, are ONLY:
#   (a) --output_name=rw0man_lt0            (was flux_dreambooth) — LT-0 adapter name.
#   (b) docker run:  -d --name lt0-flux-train   instead of   -it --rm
#       Detached + named so training logs survive for retrieval and the container
#       can be inspected after exit. NOT auto-removed — the executor does
#       `docker rm lt0-flux-train` after logs are safely captured.
#   (c) nothing else. Every accelerate/flux_train_network flag, every mount, every
#       ulimit is byte-identical to the playbook launcher.
#
# MUST be run from the playbook assets dir so the $(pwd)/... bind-mounts resolve:
#   cd ~/dgx-spark-playbooks/nvidia/flux-finetuning/assets && \
#     bash <this-script>
# Requires the flux-train image built (docker build -f Dockerfile.train -t flux-train .).
# Dataset: flux_data/data.toml -> flux_data/rw0man (class_tokens "rw0man person").
# ---------------------------------------------------------------------------
CMD="accelerate launch \
    --num_processes=1 --num_machines=1 --mixed_precision=bf16 \
    --main_process_ip=127.0.0.1 --main_process_port=29500 \
    --num_cpu_threads_per_process=2 \
    flux_train_network.py \
    --pretrained_model_name_or_path=models/checkpoints/flux1-dev.safetensors \
    --clip_l=models/text_encoders/clip_l.safetensors \
    --t5xxl=models/text_encoders/t5xxl_fp16.safetensors \
    --ae=models/vae/ae.safetensors \
    --dataset_config=flux_data/data.toml \
    --output_dir=models/loras/ \
    --prior_loss_weight=1.0 \
    --output_name=rw0man_lt0 \
    --save_model_as=safetensors \
    --network_module=networks.lora_flux \
    --network_dim=256 \
    --network_alpha=256 \
    --learning_rate=1.0 \
    --optimizer_type=Prodigy \
    --lr_scheduler=cosine_with_restarts \
    --gradient_accumulation_steps 4 \
    --gradient_checkpointing \
    --sdpa \
    --max_train_epochs=100 \
    --save_every_n_epochs=25 \
    --mixed_precision=bf16 \
    --guidance_scale=1.0 \
    --timestep_sampling=flux_shift \
    --model_prediction_type=raw \
    --torch_compile \
    --persistent_data_loader_workers \
    --cache_latents \
    --cache_latents_to_disk \
    --cache_text_encoder_outputs \
    --cache_text_encoder_outputs_to_disk"

docker run -d \
    --name lt0-flux-train \
    --gpus all \
    --ipc=host \
    --net=host \
    --ulimit memlock=-1 \
    --ulimit stack=67108864 \
    -v $(pwd)/flux_data:/workspace/sd-scripts/flux_data \
    -v $(pwd)/models/vae:/workspace/sd-scripts/models/vae \
    -v $(pwd)/models/loras:/workspace/sd-scripts/models/loras \
    -v $(pwd)/models/checkpoints:/workspace/sd-scripts/models/checkpoints \
    -v $(pwd)/models/text_encoders:/workspace/sd-scripts/models/text_encoders \
    flux-train \
    bash -c "$CMD"
