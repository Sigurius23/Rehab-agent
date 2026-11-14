#!/usr/bin/env bash
# Build an OpenCap Monocular environment for the RTX 5090 (compute capability 12.0), outside the repository.
# Its own recipe (installation/INSTALL_SLIM.md) pins torch 2.1.2+cu118 and a prebuilt mmcv-full 1.7.2, neither of which
# supports 12.0, so: torch 2.7.1+cu128, a CUDA 12.8 toolkit inside the environment (no sudo), and mmcv-full 1.7.2
# compiled from source. Everything else follows the recipe's order and pins. Environment only: no weights, no runs.
# Runs at the lowest CPU priority. Each step is logged; the script stops at the first failure.
set -euo pipefail
K=$HOME/rehab-agent-data/kinematics; O=$K/upstream/utahmobl/opencap-monocular; E=$K/envs/opencap-mono
CONDA=$HOME/miniconda3/bin/conda; PIP="$E/bin/python -m pip"
step() { echo "$(date '+%F %T') === $*"; }
step "1. ViTPose submodule (DPVO is not needed: the slim recipe drops it)"
GIT_TERMINAL_PROMPT=0 git -C "$O" submodule update --init --depth 1 WHAM/third-party/ViTPose
git -C "$O/WHAM/third-party/ViTPose" rev-parse HEAD
step "2. conda environment, Python 3.9, and OpenSim 4.4 (the recipe's build, numpy 1.21)"
[ -x "$E/bin/python" ] || "$CONDA" create -y -q -p "$E" -c conda-forge --override-channels python=3.9
"$CONDA" install -y -q -p "$E" -c opensim-org -c conda-forge opensim=4.4=py39np121
step "3. CUDA 12.8 toolkit inside the environment (for compiling mmcv's CUDA ops)"
"$CONDA" install -y -q -p "$E" -c nvidia/label/cuda-12.8.1 -c conda-forge --override-channels cuda-toolkit
"$E/bin/nvcc" --version | tail -1
step "4. PyTorch 2.7.1 + cu128 (supports compute capability 12.0)"
$PIP install -q torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
$PIP install -q numpy==1.21.6
"$E/bin/python" -c "import torch, numpy; print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), numpy.__version__)"
step "5. mmcv-full 1.7.2 from source, CUDA ops for 12.0"
$PIP install -q openmim wheel setuptools==69.5.1 ninja
# nvcc 12.8 accepts host GCC <= 14; the system's GCC is newer, so use conda-forge's GCC 13 inside the environment
"$CONDA" install -y -q -p "$E" -c conda-forge --override-channels gcc_linux-64=13 gxx_linux-64=13
GCC=$(ls "$E"/bin/x86_64-conda-linux-gnu-gcc); GXX=$(ls "$E"/bin/x86_64-conda-linux-gnu-g++); "$GXX" --version | head -1
export CC=$GCC CXX=$GXX CUDAHOSTCXX=$GXX NVCC_PREPEND_FLAGS="-ccbin $GXX"
# conda's CUDA puts its headers and libraries under targets/x86_64-linux, not $CUDA_HOME/include and lib64
export CPATH="$E/targets/x86_64-linux/include${CPATH:+:$CPATH}" LIBRARY_PATH="$E/targets/x86_64-linux/lib:$E/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
CUDA_HOME=$E MMCV_WITH_OPS=1 FORCE_CUDA=1 TORCH_CUDA_ARCH_LIST="12.0" MAX_JOBS=8 $PIP install -v --no-build-isolation mmcv-full==1.7.2 > "$K/envs/opencap-mono-mmcv-build.log" 2>&1
"$E/bin/python" -c "import mmcv, mmcv.ops; print('mmcv', mmcv.__version__, 'ops ok')"
# the conda compiler settings were for mmcv's CUDA build only; later builds (e.g. evdev) use the system compiler
unset CC CXX CUDAHOSTCXX NVCC_PREPEND_FLAGS CPATH LIBRARY_PATH
step "6. the recipe's pip requirements (requirements_slim.txt)"
$PIP install -q -r "$O/installation/requirements_slim.txt"
step "7. ViTPose and SLAHMR, editable"
$PIP install -q -e "$O/WHAM/third-party/ViTPose"
$PIP install -q -e "$O/slahmr"
step "8. verify (the recipe's own check, plus CUDA on the GPU)"
cd "$O" && "$E/bin/python" -c "
import torch; print('torch:', torch.__version__, '| CUDA:', torch.cuda.is_available(), torch.cuda.get_device_capability(0))
x = torch.randn(512, 512, device='cuda'); print('matmul ok', float((x @ x).sum()) != 0)
import mmcv; print('mmcv:', mmcv.__version__)
import opensim; print('opensim:', opensim.__version__)
import mmpose; print('ViTPose/mmpose:', mmpose.__version__)
import optimization; print('optimization: OK')
print('Installation successful.')"
"$CONDA" list -p "$E" --export > "$K/envs/opencap-mono.conda.txt"; $PIP freeze > "$K/envs/opencap-mono.freeze.txt"
step "done"
