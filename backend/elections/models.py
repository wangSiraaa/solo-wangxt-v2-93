from django.db import models


class RuleSet(models.Model):
    """事先固定的 IRV 规则。一次选举创建后即不可临场更改。

    规则要点（与前端“规则说明”一致）：
    - 选票为候选人代码的偏好序列，如 ["A", "C"]；
    - 同一张选票上重复出现同一候选人：保留其**最先**出现的位置，
      后续重复项删除（dedup_first）；
    - 出现本次选举不存在（无效）的候选人代码：从序列中剔除该无效项，
      其余偏好照常保留（drop_invalid）；
    - 未给任何候选人排名（清洗后为空）：整票记为入库无效票，
      不参与任何一轮计票；
    - 选票上未排名的候选人：该票对这些候选人没有偏好；当票上尚有偏好的
      候选人全部被淘汰后，该票成为“穷尽票”，不再计入任何候选人，
      但每轮仍计入“已投出票数”用于过半门槛的分母；
    - 无人过半时淘汰本轮当前票数最低者；最低票并列时，
      严格按候选人 code 的字典序决胜（code_order 升序先淘汰），
      全程不使用任何随机选择；
    - 当选门槛：获得**严格过半**（votes > active/2）即当选。
    """

    name = models.CharField("规则名称", max_length=128, unique=True)
    duplicate_rank_handling = models.CharField(
        "重复排名处理",
        max_length=32,
        choices=[("dedup_first", "保留首次出现，剔除重复项")],
        default="dedup_first",
    )
    invalid_candidate_handling = models.CharField(
        "无效候选人代码处理",
        max_length=32,
        choices=[("drop_invalid", "剔除无效项，保留其余偏好")],
        default="drop_invalid",
    )
    unranked_handling = models.CharField(
        "未排名候选人处理",
        max_length=32,
        choices=[
            ("exhaust_when_gone", "所支持候选人全部淘汰后该票穷尽")
        ],
        default="exhaust_when_gone",
    )
    majority_rule = models.CharField(
        "过半口径",
        max_length=32,
        choices=[("strict_majority", "严格过半（>50%，含穷尽票分母）")],
        default="strict_majority",
    )
    tie_break = models.CharField(
        "同票决胜",
        max_length=32,
        choices=[("code_asc", "按候选人代码升序先淘汰")],
        default="code_asc",
    )
    description = models.TextField("规则说明", blank=True, default="")

    class Meta:
        verbose_name = "计票规则"
        verbose_name_plural = "计票规则"

    def __str__(self):
        return self.name


class Election(models.Model):
    """一次单席位排序选择投票（合成演示）。"""

    name = models.CharField("选举名称", max_length=200)
    seat_count = models.PositiveSmallIntegerField("应选席位", default=1)
    ruleset = models.ForeignKey(
        RuleSet, on_delete=models.PROTECT, verbose_name="适用规则"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(
        "备注", max_length=255, blank=True, default="",
        help_text="仅用于标注“匿名合成数据、非真实选举”。",
    )

    class Meta:
        verbose_name = "选举"
        verbose_name_plural = "选举"

    def __str__(self):
        return self.name


class Candidate(models.Model):
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE,
        related_name="candidates", verbose_name="所属选举",
    )
    code = models.CharField(
        "候选人代码", max_length=32,
        help_text="同一次选举内唯一；同时用于同票决胜的字典序。",
    )
    name = models.CharField("候选人姓名", max_length=128)
    display_order = models.PositiveIntegerField(
        "展示顺序", default=0,
        help_text="仅用于页面排序；决胜一律按 code 字典序。",
    )

    class Meta:
        verbose_name = "候选人"
        verbose_name_plural = "候选人"
        unique_together = ("election", "code")
        ordering = ["display_order", "code"]

    def __str__(self):
        return f"{self.code}·{self.name}"


class Ballot(models.Model):
    """匿名合成选票。不记录任何选民身份信息。

    preferences_raw：入库时的原始偏好序列（可能含重复/无效代码），
    preferences：按规则清洗后的有效偏好序列；
    is_valid=False 表示清洗后为空（未给任何有效排名），
    这类票不参与任何一轮计票，但在汇总中单独列示。
    """

    election = models.ForeignKey(
        Election, on_delete=models.CASCADE,
        related_name="ballots", verbose_name="所属选举",
    )
    preferences_raw = models.JSONField("原始偏好（候选人代码序列）", default=list)
    preferences = models.JSONField("清洗后偏好", default=list)
    weight = models.PositiveIntegerField("该合成票代表的票数", default=1)
    is_valid = models.BooleanField("是否为有效入库票", default=True)
    invalid_reason = models.CharField(
        "无效/清洗原因", max_length=255, blank=True, default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "匿名合成选票"
        verbose_name_plural = "匿名合成选票"
        indexes = [models.Index(fields=["election", "is_valid"])]

    def __str__(self):
        return f"Ballot#{self.pk} {self.preferences_raw}"
