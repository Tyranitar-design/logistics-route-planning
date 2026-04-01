# 供应商管理模块设计

## 功能模块

### 1. 供应商档案
- 基本信息（名称、编码、类型、行业）
- 联系方式（地址、电话、邮箱、联系人）
- 资质证书（营业执照、资质等级、有效期）
- 合作历史（合作时长、累计交易额、订单数）
- 银行账户（开户行、账号）

### 2. 绩效评估
- 卡拉杰克矩阵分类（已有，复用）
  - 战略型：高价值、高风险
  - 杠杆型：高价值、低风险
  - 瓶颈型：低价值、高风险
  - 常规型：低价值、低风险
- 综合评分（质量、交付、成本、服务）
- 评估历史记录

### 3. 合同管理
- 合同创建（编号、类型、起止日期、金额）
- 合同条款（付款条件、违约责任、服务标准）
- 合同续签提醒
- 合同附件管理

### 4. 对账结算
- 账单生成
- 对账确认
- 付款记录
- 开票管理

### 5. 风险监控
- 风险等级（低/中/高/严重）
- 风险类型（财务、交付、质量、合规）
- 风险预警
- 风险处置记录

## 数据库设计

### suppliers 表
```sql
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(50) UNIQUE NOT NULL,        -- 供应商编码
    name VARCHAR(200) NOT NULL,               -- 供应商名称
    type VARCHAR(50),                         -- 类型（原材料/物流/设备/服务）
    industry VARCHAR(100),                    -- 所属行业
    
    -- 联系信息
    address TEXT,                             -- 地址
    phone VARCHAR(50),                        -- 电话
    email VARCHAR(100),                       -- 邮箱
    contact_person VARCHAR(100),              -- 联系人
    
    -- 资质信息
    license_no VARCHAR(100),                  -- 营业执照号
    license_expire DATE,                      -- 执照到期日
    qualification_level VARCHAR(50),          -- 资质等级
    
    -- 银行信息
    bank_name VARCHAR(100),                   -- 开户行
    bank_account VARCHAR(50),                 -- 银行账号
    
    -- 合作信息
    cooperation_start DATE,                   -- 合作开始日期
    status VARCHAR(20) DEFAULT 'active',      -- 状态（active/suspended/terminated）
    
    -- 评估信息
    kraljic_category VARCHAR(50),             -- 卡拉杰克分类
    quality_score DECIMAL(5,2),               -- 质量评分
    delivery_score DECIMAL(5,2),              -- 交付评分
    cost_score DECIMAL(5,2),                  -- 成本评分
    service_score DECIMAL(5,2),               -- 服务评分
    total_score DECIMAL(5,2),                 -- 综合评分
    
    -- 风险信息
    risk_level VARCHAR(20),                   -- 风险等级
    last_evaluation_date DATE,                -- 最近评估日期
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### supplier_contracts 表
```sql
CREATE TABLE supplier_contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    contract_no VARCHAR(50) UNIQUE NOT NULL,  -- 合同编号
    contract_type VARCHAR(50),                -- 合同类型（采购/物流/服务）
    title VARCHAR(200),                       -- 合同名称
    
    start_date DATE NOT NULL,                 -- 开始日期
    end_date DATE NOT NULL,                   -- 结束日期
    amount DECIMAL(15,2),                     -- 合同金额
    
    payment_terms TEXT,                       -- 付款条件
    service_terms TEXT,                       -- 服务条款
    penalty_terms TEXT,                       -- 违约条款
    
    status VARCHAR(20) DEFAULT 'active',      -- 状态（draft/active/expired/terminated）
    attachments TEXT,                         -- 附件JSON
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);
```

### supplier_settlements 表
```sql
CREATE TABLE supplier_settlements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    contract_id INTEGER,
    
    settlement_no VARCHAR(50) UNIQUE NOT NULL, -- 结算单号
    period_start DATE,                         -- 结算周期开始
    period_end DATE,                           -- 结算周期结束
    
    amount DECIMAL(15,2) NOT NULL,            -- 结算金额
    paid_amount DECIMAL(15,2) DEFAULT 0,      -- 已付金额
    
    status VARCHAR(20) DEFAULT 'pending',     -- 状态（pending/confirmed/paid）
    invoice_no VARCHAR(100),                  -- 发票号
    invoice_date DATE,                        -- 开票日期
    
    confirm_date DATE,                        -- 对账确认日期
    confirm_by VARCHAR(100),                  -- 确认人
    
    remark TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (contract_id) REFERENCES supplier_contracts(id)
);
```

### supplier_risks 表
```sql
CREATE TABLE supplier_risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    
    risk_type VARCHAR(50) NOT NULL,           -- 风险类型
    risk_level VARCHAR(20) NOT NULL,          -- 风险等级
    risk_score DECIMAL(5,2),                  -- 风险分数
    
    description TEXT,                         -- 风险描述
    impact TEXT,                              -- 影响分析
    mitigation TEXT,                          -- 缓解措施
    
    status VARCHAR(20) DEFAULT 'active',      -- 状态（active/mitigated/closed）
    reported_by VARCHAR(100),                 -- 上报人
    reported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    resolved_at DATETIME,
    resolved_by VARCHAR(100),
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);
```

## API 设计

### 供应商档案
- `GET /api/suppliers` - 供应商列表
- `GET /api/suppliers/{id}` - 供应商详情
- `POST /api/suppliers` - 创建供应商
- `PUT /api/suppliers/{id}` - 更新供应商
- `DELETE /api/suppliers/{id}` - 删除供应商

### 绩效评估
- `GET /api/suppliers/{id}/performance` - 绩效评估
- `POST /api/suppliers/{id}/evaluate` - 执行评估
- `GET /api/suppliers/performance-matrix` - 卡拉杰克矩阵分布

### 合同管理
- `GET /api/suppliers/{id}/contracts` - 合同列表
- `POST /api/suppliers/{id}/contracts` - 创建合同
- `PUT /api/contracts/{id}` - 更新合同
- `GET /api/contracts/expiring` - 即将到期合同

### 对账结算
- `GET /api/suppliers/{id}/settlements` - 结算记录
- `POST /api/suppliers/{id}/settlements` - 创建结算单
- `POST /api/settlements/{id}/confirm` - 确认对账
- `POST /api/settlements/{id}/pay` - 记录付款

### 风险监控
- `GET /api/suppliers/{id}/risks` - 风险记录
- `POST /api/suppliers/{id}/risks` - 上报风险
- `POST /api/risks/{id}/mitigate` - 风险处置
- `GET /api/suppliers/risk-dashboard` - 风险仪表盘

## 前端页面

### 页面结构
```
/suppliers
├── 供应商列表（表格 + 卡拉杰克矩阵图）
├── 供应商详情（Tab页）
│   ├── 基本信息
│   ├── 绩效评估
│   ├── 合同管理
│   ├── 对账结算
│   └── 风险监控
└── 新建/编辑供应商
```
