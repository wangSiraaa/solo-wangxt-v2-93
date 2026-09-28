from django.db import models


class Election(models.Model):
    """A synthetic, non-production IRV demonstration election."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rule_duplicate_rankings = models.TextField(
        default="同一候选人重复排名时，只保留其第一次出现的最高偏好，后续重复项忽略。"
    )
    rule_unranked_candidates = models.TextField(
        default="选票中未列出的候选人视为未排名，不参与该选票分配；已排名偏好全部淘汰或无效后，选票穷尽。"
    )
    rule_invalid_candidates = models.TextField(
        default="不存在或不属于本次选举的候选人代码视为无效偏好并忽略；若剩余偏好为空，选票首轮即穷尽。"
    )
    rule_tie_break = models.TextField(
        default="最低票同票时，按事先配置的候选人代码 code 的字典升序淘汰代码较早者；不使用随机数。"
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title


class Candidate(models.Model):
    election = models.ForeignKey(Election, related_name="candidates", on_delete=models.CASCADE)
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["election", "code"], name="unique_candidate_code_per_election"),
        ]

    def __str__(self):
        return f"{self.code}: {self.name}"


class Ballot(models.Model):
    election = models.ForeignKey(Election, related_name="ballots", on_delete=models.CASCADE)
    synthetic_ballot_id = models.PositiveIntegerField(
        help_text="合成选票编号，不关联真实选民。"
    )
    raw_rankings = models.JSONField(
        help_text="提交的候选人代码数组，按偏好从高到低排列。"
    )
    normalized_rankings = models.JSONField(
        help_text="去除重复和无效候选人后的有效偏好代码。"
    )

    class Meta:
        ordering = ["synthetic_ballot_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["election", "synthetic_ballot_id"],
                name="unique_synthetic_ballot_id_per_election",
            )
        ]

    def __str__(self):
        return f"{self.election_id} ballot {self.synthetic_ballot_id}"
