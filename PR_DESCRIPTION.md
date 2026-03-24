# Pull Request Template

## 标题 (Title)
**feat: Implement LSTM anomaly detection model and risk scoring engine**

## 概述 (Overview)
实现基于 LSTM 深度学习的社交媒体账号被盗风险预警系统核心功能。

## 主要变更 (Changes)

### 1. LSTM 检测模型 (`app/ml/models/lstm_model.py`)
- 双向 LSTM + Attention 机制
- 输入：用户行为序列 (30时间步, 109特征)
- 输出：异常概率 (0-1)
- 方法：train_model(), predict(), save_model(), load_model()

### 2. 特征提取器 (`app/ml/feature_extractor.py`)
- 设备指纹：MD5 (User-Agent + screen + timezone)
- 地理位置异常：Haversine 距离
- 时间异常：圆形偏差计算

### 3. 风险评分引擎 (`app/services/risk_service.py`)
- LSTM 60% + 位置 20% + 设备 10% + 时间 10%
- 风险等级：低(0-30)/中(31-60)/高(61-80)/极高(81-100)

### 4. API 端点 (`app/api/v1/endpoints/risk.py`)
- POST /api/v1/risk/analyze - 实时风险分析
- GET /api/v1/risk/history/{user_id} - 历史记录
- POST /api/v1/risk/threshold - 更新阈值

### 5. 多渠道预警 (`app/services/alert_service.py`)
- 邮件(SMTP)、短信(占位符)、站内推送(Redis)
- 5分钟去重，风险>70分自动记录

### 6. 批量推理优化 (`app/ml/inference/predictor.py`)
- predict_batch_list() 支持 List[List[float]]
- batch_size 默认32，可配置

## 测试覆盖 (Test Coverage)
- 33 个测试通过
- 覆盖率：60%
- LSTM模型测试：初始化、前向、训练、保存加载、边界情况
- API测试：正常请求、认证、参数校验

## Breaking Changes
**无** - 此次为初始功能实现，不影响现有功能

## 相关 Issue
- Closes #1, #2, #3, #4