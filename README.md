# IRV 单席位排序选择投票 · 逐轮计票系统

社团联合会单席位排序选择投票（Instant-Runoff Voting, IRV / RCV-1）演示系统：

- **Django REST Framework** 实现固定规则的 IRV 计票；
- **PostgreSQL** 保存候选人、规则与**匿名合成选票**（不接入任何真实选举）；
- **React + Vite** 按轮次展示候选人得票、选票转移汇总与穷尽票；
- 计票引擎**无随机数、无时间依赖**，同票严格按事先配置的候选人代码顺序决胜。

## 1. 计票规则（选举前固定，不允许临场更改）

| 情形 | 处理方式 |
| --- | --- |
| 选票格式 | 候选人代码的有序偏好序列，如 `["A","C"]`；序列中没有的候选人视为**未排名** |
| 同一候选人在一张票上重复排名 | **保留第一次出现的位置**，删除后续重复项（如 `["C","C","D"] → ["C","D"]`） |
| 出现本次不存在的（无效）候选人代码 | **剔除该无效项**，其余偏好照常保留（如 `["D","X","A"] → ["D","A"]`） |
| 清洗后没有任何有效偏好（空白票、只填了无效代码） | 整票记为**入库无效票**，不参与任何一轮计票，但在汇总中单独列示 |
| 未排名候选人 | 正常；当该票上所有已排名候选人均被淘汰后，该票成为**穷尽票** |
| 穷尽票 | 不再计入任何候选人，但**每轮仍计入有效票总数**，作为过半门槛分母 |
| 当选条件 | 单席位，某候选人获得**严格过半**（`votes > 有效票/2`）即当选 |
| 无人过半 | 淘汰本轮票数最低者，其持有的票按各自**下一有效偏好**转移 |
| 最低票并列 | 按候选人 `code` **字典序升序**先淘汰（决胜顺序由候选人事先配置），**禁止随机** |
| 穷尽票过多、剩余者永远无法过半 | 只剩一名在场候选人时，由其按规则当选（`acclamation_last_standing`） |

> 规则字段保存在 PostgreSQL 的 `RuleSet` 表中，选举通过外键引用；演示数据创建后不可修改。

## 2. 目录结构

```
workspace/
├── backend/                 # Django + DRF
│   ├── config/              # 项目配置（DB 指向 127.0.0.1:55432/irv）
│   └── elections/
│       ├── models.py        # RuleSet / Election / Candidate / Ballot
│       ├── services/
│       │   ├── ballot_cleaning.py   # 选票清洗（重复/无效/空白）
│       │   └── tabulation.py        # IRV 纯函数引擎（逐轮、守恒断言）
│       ├── serializers.py / views.py / urls.py
│       ├── tests.py         # 14 个用例：清洗/守恒/决胜/API
│       └── management/commands/seed_demo.py  # 幂等写入两个合成样例
├── frontend/                # React 18 + Vite 5
│   └── src/
│       ├── App.jsx
│       └── components/      # RulesPanel / RoundCard / BallotList
├── scripts/                 # start.sh / stop.sh
└── .pgsql/                  # 本地解压版 PostgreSQL 15（数据目录 data/）
```

## 3. 快速启动

环境中使用本地解压版 PostgreSQL（无 root）与项目内 venv：

```bash
# 一次性准备（当前工作区已完成）：
#   python3 -m venv .venv            # pip 见 get-pip.py
#   .venv/bin/pip install -r backend/requirements.txt
#   apt 下载 postgresql-15 deb → 解压到 .pgsql/root → initdb → 端口 55432

bash scripts/start.sh
```

- 前端：<http://127.0.0.1:5173/>
- API：<http://127.0.0.1:8000/api/elections/>
- 停止：`bash scripts/stop.sh`

数据库重建与种子：

```bash
cd backend
../../.venv/bin/python manage.py flush --no-input
../../.venv/bin/python manage.py seed_demo     # 幂等
../../.venv/bin/python manage.py test elections
```

## 4. REST API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/elections/` | 选举列表（含规则、候选人/票数） |
| GET | `/api/elections/{id}/` | 单次选举与规则 |
| GET | `/api/elections/{id}/candidates/` | 候选人（代码、姓名、展示顺序） |
| GET | `/api/elections/{id}/ballots/` | 匿名合成选票（原始/清洗后偏好，无选民信息） |
| GET | `/api/elections/{id}/result/` | **逐轮 IRV 结果（每次实时重算，无缓存）** |

`result` 关键结构：

```json
{
  "winner_code": "B",
  "winner_name": "乙",
  "terminated_reason": "majority",
  "total_valid_weight": 20,
  "invalid_ballots": 0,
  "total_ballots": 20,
  "tie_break_order": ["A", "B", "C", "D"],
  "conservation_ok": true,
  "rounds": [
    {
      "round_number": 3,
      "transfers_in": [
        {"from_code": "D", "from_name": "丁", "to_code": "A", "to_name": "甲", "votes": 1},
        {"from_code": "D", "from_name": "丁", "to_code": "B", "to_name": "乙", "votes": 1},
        {"from_code": "D", "from_name": "丁", "to_code": null,
         "to_name": "穷尽（无下一有效偏好）", "votes": 2}
      ],
      "exhausted_delta": 2,
      "tally_rows": [
        {"code": "A", "name": "甲", "votes": 8, "status": "standing"},
        {"code": "B", "name": "乙", "votes": 10, "status": "standing"},
        {"code": "C", "name": "丙", "votes": null, "status": "eliminated"},
        {"code": "D", "name": "丁", "votes": null, "status": "eliminated"}
      ],
      "active_ballots": 18,
      "exhausted_ballots": 2,
      "counted_ballots": 20,
      "majority_threshold": 11,
      "tied_min_codes": ["A"],
      "eliminated_codes": ["A"]
    }
  ]
}
```

## 5. 样例验证（首轮无过半 → 连续转移 → 穷尽票 → 守恒）

### 样例一：4 候选人 / 20 张合成票（含重复排名 `C,C` 与无效代码 `X`）

| 轮次 | A·甲 | B·乙 | C·丙 | D·丁 | 在投 | 穷尽 | 门槛 | 处置 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 7 | 7 | 3 | 3 | 20 | 0 | 11 | C、D 同为最低 3 票，按代码序淘汰 **C** |
| 2 | 7 | 9 | — | 4 | 20 | 0 | 11 | C 的 3 票 → B×2、D×1；淘汰 **D** |
| 3 | 8 | 10 | — | — | 18 | 2 | 11 | D 的 4 票 → A×1、B×1、**穷尽×2**；淘汰 **A** |
| 4 | — | **15** | — | — | 15 | 5 | 11 | A 的 8 票 → B×5、穷尽×3；**B 严格过半当选** |

守恒（每轮）：候选人票数之和 + 穷尽票 = 20 ✓
- R1：7+7+3+3+0 = 20；R3：8+10+0+2 = 20；R4：15+0+5 = 20。
- 转移量守恒：C 转出 3 = 2+1；D 转出 4 = 1+1+2；A 转出 8 = 5+3（引擎内置断言）。

### 样例二：3 候选人 / 15 张记录（3 张入库无效：空白×2、只填无效代码×1）

| 轮次 | X·梅花 | Y·兰花 | Z·竹子 | 在投 | 穷尽 | 门槛 | 处置 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 | 4 | 4 | 12 | 0 | 7 | 三方同票，按代码序淘汰 **X**（X 的 4 票均无下一偏好 → 全穷尽） |
| 2 | — | 4 | 4 | 8 | 4 | 7 | Y、Z 同票，按代码序淘汰 **Y** |
| 3 | — | — | **7** | 7 | 5 | 7 | Y 的 4 票 → Z×3、穷尽×1；**Z 严格过半当选** |

- 清洗演示：`["Q","Z"] → ["Z"]`、`["Z","Z"] → ["Z"]`；`[]` 与 `["Q"]` 记为无效票。
- 守恒：12 张有效票，R2/R3 分母恒为 12（4/5 张穷尽票始终在分母内），门槛恒为 7 ✓。

自动化验证：

```bash
.venv/bin/python manage.py test elections
# Ran 14 tests ... OK
```

覆盖：重复/无效/空白清洗、每轮票数守恒、穷尽票保留在过半分母、
代码序决胜、决胜顺序对胜者的确定性影响、重复运行结果一致、API 回归。
