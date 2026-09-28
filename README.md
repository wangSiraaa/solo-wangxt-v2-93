# 社团联合会 IRV 单席位排序选择投票计票系统

这是一个仅使用**匿名合成选票**的演示项目，不接入真实选举。项目包含：

- Django REST Framework：实现单席位 Instant-Runoff Voting（IRV / 排序复选）规则和逐轮计票 API。
- PostgreSQL：保存选举、候选人、规则文本和匿名合成选票。
- React + Vite：按轮次展示候选人票数、有效票、穷尽票、当选/淘汰和选票转移汇总。
- 固定样例：覆盖首轮无人过半、连续转移、转移到其他候选人和穷尽票。

## 1. 本次 IRV 规则

1. 每张选票是候选人代码从高到低的数组，例如 `["A", "B", "C"]`。
2. **重复排名**：同一候选人代码重复出现时，只保留第一次出现的最高/最早偏好，后续重复项忽略。
3. **无效候选**：不存在或不属于本次选举的代码忽略；若忽略后没有有效偏好，该选票首轮即为穷尽票。
4. **未排名候选**：未列出的候选人不会获得该选票；当前候选人淘汰后，只在选票已列出的有效偏好中继续寻找下一偏好。
5. 每轮统计：
   - `valid_total`：当前仍分配给在局候选人的有效票。
   - `exhausted_total`：没有下一有效偏好的穷尽票。
   - `majority_threshold = floor(valid_total / 2) + 1`。
6. 若最高票候选人达到过半阈值，立即当选。
7. 若无人过半，淘汰当前最低票候选人，并把其选票按每张选票的下一有效偏好转移；无下一偏好则成为穷尽票。
8. **同票决胜不随机**：最低票同票时，按事先确定的候选人代码 `code` 字典升序，淘汰代码较早者。例如 A、C、D 同为最低票时淘汰 A。

## 2. 固定样例验证

种子数据共 25 张匿名合成选票、5 名候选人 A–E。其中选票 24 `["Z"]` 和 25 `[]` 首轮穷尽，选票 23 `["E", "X"]` 在 E 淘汰后穷尽，选票 19 `["D"]` 在 D 淘汰后穷尽；选票 4 包含重复排名 `["A", "B", "D", "A"]`，规范化后为 `["A", "B", "D"]`。

| 轮次 | A | B | C | D | E | 有效票 | 穷尽票 | 阈值 | 处理 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 5 | 6 | 4 | 4 | 4 | 23 | 2 | 12 | C、D、E 同为最低，按代码顺序淘汰 C |
| 2 | 8 | 6 | — | 4 | 5 | 23 | 2 | 12 | D 最低，淘汰 D |
| 3 | 9 | 8 | — | — | 5 | 22 | 3 | 12 | E 最低，淘汰 E |
| 4 | 10 | 11 | — | — | — | 21 | 4 | 11 | B 过半，B 当选 |

主要转移：

- 第 2 轮：C → A 3 票，C → E 1 票。
- 第 3 轮：D → A 1 票，D → B 2 票，D → 穷尽 1 票。
- 第 4 轮：E → A 1 票，E → B 3 票，E → 穷尽 1 票。

每轮都满足票数守恒：

```text
在局候选人票数合计 + 穷尽票 = 合成选票总数
```

自动化测试也会断言各轮票数、转移票数、最终当选人和重复运行结果一致。

## 3. 快速启动（Docker Compose）

要求本机有 Docker / Docker Compose。

```bash
docker compose up --build
```

启动后访问：

- React 页面：http://localhost:5173
- 计票 API：http://localhost:8000/api/elections/1/tally/
- 选举列表：http://localhost:8000/api/elections/

后端容器会自动执行：

```bash
python manage.py migrate
python manage.py seed_demo
```

## 4. 本地开发启动

### 后端

```bash
cd backend
uv sync
# 需要先有 PostgreSQL；也可使用 docker compose up db 单独启动数据库
export POSTGRES_HOST=localhost
export POSTGRES_DB=irv
export POSTGRES_USER=irv
export POSTGRES_PASSWORD=irv
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

Vite 已配置 `/api` 代理到 `http://localhost:8000`。

## 5. 运行测试和构建

后端测试使用内存 SQLite 验证纯计票逻辑；生产配置仍使用 PostgreSQL：

```bash
cd backend
.venv/bin/python manage.py test --settings=irv_backend.test_settings -v 2
```

前端生产构建：

```bash
cd frontend
npm run build
```

## 6. API 结构

`GET /api/elections/{id}/tally/` 的核心字段：

```json
{
  "winner_code": "B",
  "total_ballots": 25,
  "rounds": [
    {
      "round_number": 1,
      "status": "elimination",
      "valid_total": 23,
      "exhausted_total": 2,
      "exhausted_ballot_ids": [24, 25],
      "majority_threshold": 12,
      "eliminated_code": "C",
      "tie_break_applied": true,
      "candidate_results": [],
      "transfers": [],
      "ballot_tracks": []
    }
  ]
}
```

`transfers` 按来源、去向聚合，并包含具体合成选票编号，便于页面逐轮解释选票去向；`ballot_tracks` 保存每张合成选票在当前轮的目的地，可用于进一步审计和调试。
