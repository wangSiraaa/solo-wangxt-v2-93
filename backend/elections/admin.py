from django.contrib import admin

from .models import Ballot, Candidate, Election, RuleSet


@admin.register(RuleSet)
class RuleSetAdmin(admin.ModelAdmin):
    list_display = ("name", "duplicate_rank_handling",
                    "invalid_candidate_handling", "tie_break")


class CandidateInline(admin.TabularInline):
    model = Candidate
    extra = 0


class BallotInline(admin.TabularInline):
    model = Ballot
    extra = 0
    fields = ("preferences_raw", "preferences", "weight",
              "is_valid", "invalid_reason")


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "seat_count", "ruleset", "note")
    list_filter = ("ruleset",)
    inlines = [CandidateInline]


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "election", "display_order")
    list_filter = ("election",)


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ("id", "election", "preferences_raw",
                    "preferences", "weight", "is_valid")
    list_filter = ("election", "is_valid")
