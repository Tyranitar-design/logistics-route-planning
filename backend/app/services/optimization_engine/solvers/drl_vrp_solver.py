"""
深度强化学习 VRP 求解器
======================

基于 VRP-RL (NeurIPS 2018) 的神经网络 VRP 求解器
特点：端到端学习、快速推理

参考论文：https://arxiv.org/abs/1802.04240
参考代码：https://github.com/OptMLGroup/VRP-RL

作者: 小彩
日期: 2026-04-25
"""

import numpy as np
from typing import List, Dict, Any, Optional
import time

from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    ProblemType,
    timeit
)


class DRLVRPSolver(OptimizationSolver):
    """
    深度强化学习 VRP 求解器
    
    基于 Attention 机制的 Pointer Network
    训练后可以直接预测，无需迭代搜索
    
    支持：
    - CVRP (容量约束)
    - VRPTW (时间窗) - 需要扩展
    
    优点：
    - 推理速度快 (毫秒级)
    - 可端到端训练
    - 泛化能力强
    
    缺点：
    - 需要预训练模型
    - 大规模问题效果可能下降
    """
    
    def __init__(self, model_path: str = None, **kwargs):
        super().__init__("DRL-VRP", SolverType.DRL_VRP)
        
        self.model_path = model_path
        self.torch_available = False
        self.model = None
        self.device = kwargs.get('device', 'cpu')
        
        # 尝试导入 PyTorch
        try:
            import torch
            import torch.nn as nn
            import torch.nn.functional as F
            self.torch = torch
            self.nn = nn
            self.F = F
            self.torch_available = True
        except ImportError:
            print("⚠️ PyTorch 未安装，请运行: pip install torch")
    
    def is_available(self) -> bool:
        """检查求解器是否可用"""
        return self.torch_available
    
    def load_model(self, model_path: str):
        """加载预训练模型"""
        if not self.torch_available:
            raise RuntimeError("PyTorch 未安装")
        
        self.model = self._build_model()
        
        if model_path:
            self.model.load_state_dict(
                self.torch.load(model_path, map_location=self.device)
            )
        
        self.model.to(self.device)
        self.model.eval()
    
    def _build_model(self):
        """构建 Pointer Network 模型"""
        outer_torch = self.torch

        class Encoder(self.nn.Module):
            def __init__(self, input_dim, hidden_dim):
                super().__init__()
                self.lstm = self.nn.LSTM(input_dim, hidden_dim, batch_first=True)
                self.embedding = self.nn.Linear(input_dim, hidden_dim)
            
            def forward(self, x):
                embedded = self.embedding(x)
                output, (h, c) = self.lstm(embedded)
                return output, (h, c)
        
        class Attention(self.nn.Module):
            def __init__(self, hidden_dim):
                super().__init__()
                self.W1 = self.nn.Linear(hidden_dim, hidden_dim)
                self.W2 = self.nn.Linear(hidden_dim, hidden_dim)
                self.V = self.nn.Linear(hidden_dim, 1)
            
            def forward(self, decoder_state, encoder_outputs):
                score = self.V(self.F.tanh(self.W1(decoder_state) + self.W2(encoder_outputs)))
                attention_weights = self.F.softmax(score, dim=1)
                context = outer_torch.sum(attention_weights * encoder_outputs, dim=1)
                return context, attention_weights
        
        class Decoder(self.nn.Module):
            def __init__(self, hidden_dim, output_dim):
                super().__init__()
                self.attention = Attention(hidden_dim)
                self.lstm = self.nn.LSTM(hidden_dim * 2, hidden_dim, batch_first=True)
                self.pointer = self.nn.Linear(hidden_dim * 3, output_dim)
            
            def forward(self, decoder_input, hidden, encoder_outputs, mask):
                context, attn_weights = self.attention(hidden[0].transpose(0, 1), encoder_outputs)
                
                # LSTM step
                lstm_input = torch.cat([decoder_input, context], dim=1).unsqueeze(1)
                lstm_output, hidden = self.lstm(lstm_input, hidden)
                
                # Pointer logits
                logits = self.pointer(torch.cat([lstm_output.squeeze(1), context], dim=1))
                
                # Apply mask
                logits[mask] = -float('inf')
                
                return logits, hidden, attn_weights
        
        class VRPModel(self.nn.Module):
            def __init__(self, input_dim=2, hidden_dim=128, n_glimpses=1):
                super().__init__()
                self.encoder = Encoder(input_dim, hidden_dim)
                self.decoder = Decoder(hidden_dim, hidden_dim)
                self.n_glimpses = n_glimpses
                self.hidden_dim = hidden_dim
            
            def forward(self, coords, demand, capacity, return_attention=False):
                batch_size = coords.shape[0]
                n_nodes = coords.shape[1]
                
                # 编码
                encoder_out, (h, c) = self.encoder(coords)
                
                # 初始化
                mask = torch.zeros(batch_size, n_nodes, dtype=torch.bool)
                mask[:, 0] = True  # 禁止选择车场
                
                current_node = torch.zeros(batch_size, 1, self.hidden_dim).to(coords.device)
                routes = []
                load = torch.zeros(batch_size, 1).to(coords.device)
                
                for step in range(n_nodes - 1):
                    # 解码
                    logits, (h, c), _ = self.decoder(current_node, (h, c), encoder_out, mask)
                    
                    # 贪心选择
                    probs = self.F.softmax(logits, dim=1)
                    next_node = probs.argmax(dim=1)
                    
                    # 检查容量约束
                    for b in range(batch_size):
                        next_demand = demand[b, next_node[b]]
                        if load[b] + next_demand > capacity[b]:
                            # 违反约束，重新选择
                            mask[b] = True
                            probs[b, mask[b]] = -float('inf')
                            next_node[b] = probs[b].argmax()
                    
                    routes.append(next_node.cpu().numpy())
                    
                    # 更新mask和load
                    for b in range(batch_size):
                        demand_val = demand[b, next_node[b]]
                        if demand_val > 0:
                            load[b] += demand_val
                            if load[b] >= capacity[b]:
                                # 返回车场
                                mask[b, :] = True
                                mask[b, 0] = False
                                load[b] = 0
                        else:
                            mask[b, next_node[b]] = True
                
                return np.array(routes).T
        
        return VRPModel()
    
    def solve(self, problem: OptimizationProblem, 
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """
        使用 DRL 求解 VRP 问题
        
        Args:
            problem: VRP 优化问题
            time_limit: 时间限制（秒）
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        if not self.torch_available:
            raise RuntimeError("PyTorch 未安装")
        
        start_time = time.time()
        
        # 如果没有加载模型，创建一个简单的贪心求解器
        if self.model is None:
            solution = self._greedy_solve(problem)
        else:
            solution = self._model_solve(problem)
        
        # 计算目标值
        objective = self._calculate_objective(problem, solution)
        
        solve_time = time.time() - start_time
        
        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=solution,
            objective_values=np.array([objective]),
            solve_time=solve_time,
            iterations=1,
            routes=solution,
            metadata={
                'method': 'pointer_network' if self.model else 'greedy',
                'note': '如需使用神经网络求解，请先加载预训练模型'
            }
        )
    
    def _model_solve(self, problem: OptimizationProblem) -> List[List[int]]:
        """使用神经网络求解"""
        
        # 转换数据
        coords = self.torch.tensor(
            problem.coords, dtype=self.torch.float32
        ).unsqueeze(0).to(self.device)
        
        demands = self.torch.tensor(
            problem.demands, dtype=self.torch.float32
        ).unsqueeze(0).to(self.device)
        
        capacity = self.torch.tensor(
            [problem.capacity], dtype=self.torch.float32
        ).to(self.device)
        
        # 推理
        with self.torch.no_grad():
            routes = self.model(coords, demands, capacity)
        
        # 转换格式
        return self._convert_routes(routes[0].cpu().numpy())
    
    def _greedy_solve(self, problem: OptimizationProblem) -> List[List[int]]:
        """贪心求解（当没有预训练模型时）"""
        
        coords = problem.coords
        demands = problem.demands
        capacity = problem.capacity
        
        n_customers = len(coords) - 1  # 排除车场
        visited = [False] * (n_customers + 1)
        visited[0] = True  # 车场已访问
        
        routes = []
        current_route = [0]
        current_load = 0
        current_pos = 0
        
        while sum(visited) < n_customers + 1:
            # 找到最近的未访问客户
            min_dist = float('inf')
            nearest = -1
            
            for i in range(1, n_customers + 1):
                if not visited[i]:
                    dist = self._distance(coords[current_pos], coords[i])
                    if dist < min_dist:
                        min_dist = dist
                        nearest = i
            
            if nearest == -1:
                break
            
            # 检查容量约束
            if current_load + demands[nearest] <= capacity:
                current_route.append(nearest)
                current_load += demands[nearest]
                visited[nearest] = True
                current_pos = nearest
            else:
                # 返回车场，开始新车路线
                current_route.append(0)
                routes.append(current_route)
                current_route = [0]
                current_load = 0
                current_pos = 0
        
        # 添加最后一条路线
        if len(current_route) > 1:
            current_route.append(0)
            routes.append(current_route)
        
        return routes
    
    def _distance(self, p1, p2):
        """计算两点之间的距离"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _calculate_objective(self, problem: OptimizationProblem, routes: List[List[int]]) -> float:
        """计算目标值（总距离）"""
        total_distance = 0.0
        coords = problem.coords
        
        for route in routes:
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                total_distance += self._distance(coords[from_node], coords[to_node])
        
        return total_distance
    
    def _convert_routes(self, route_indices: np.ndarray) -> List[List[int]]:
        """转换路由格式"""
        routes = []
        current_route = [0]
        
        for idx in route_indices:
            if idx == 0:
                if len(current_route) > 1:
                    current_route.append(0)
                    routes.append(current_route)
                current_route = [0]
            else:
                current_route.append(int(idx))
        
        if len(current_route) > 1:
            current_route.append(0)
            routes.append(current_route)
        
        return routes if routes else [[0]]
    
    def train_model(self, problem_generator, n_instances=10000, n_epochs=100):
        """
        训练模型
        
        Args:
            problem_generator: 问题生成器
            n_instances: 训练实例数
            n_epochs: 训练轮数
        
        Note: 实际训练需要 GPU 和大量时间
        """
        if not self.torch_available:
            raise RuntimeError("PyTorch 未安装")
        
        print("📢 DRL 模型训练需要 GPU 和大量时间")
        print("📢 建议使用预训练模型，或使用 OR-Tools / PyVRP")
        
        # 这里只是框架，实际训练需要大量计算资源


# 注册求解器
from ..base import SolverRegistry

try:
    @SolverRegistry.register(SolverType.DRL_VRP)
    class _DRLVRPSolver(DRLVRPSolver):
        pass
except:
    pass
