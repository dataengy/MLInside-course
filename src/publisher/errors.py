"""publisher.errors — turn Google's API failures into the action that unblocks them.

Every failure this pipeline actually hit in the field was a *policy* problem wearing an API
error's clothes: a full Drive reads as `storageQuotaExceeded` (space, not rights), a
read-only share reads as a bare 403, a dead consent as `invalid_grant`. The raw message
gets recorded in the leg state either way — this module prepends the one sentence that says
what a human must do next, so `just publish-new` output and the git-tracked `published:`
block stay self-explanatory months later.

Pure and offline: string matching only, no API objects imported.
"""

from __future__ import annotations

# (needles, hint) — first match wins. Google reports the same condition in two shapes: a
# machine `reason` inside the error details and an English sentence; match either, since
# which one reaches str(exc) depends on how the client wrapped it.
_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("storagequotaexceeded", "storage quota has been exceeded"),
        "диск аккаунта-владельца папки переполнен — это место, а не права: "
        "расширить квоту (Google One) или перенести папку в аккаунт со свободным местом",
    ),
    (
        ("invalid_grant",),
        "консент умер — перелогинить ADC: "
        "just -f ~/.ai/scripts/gcloud/Justfile adc-login account=hnkovr@gmail.com",
    ),
    (
        ("insufficient authentication scopes", "scope has changed", "insufficient_scope"),
        "кредлу не выдан нужный скоуп — сверить auth.scopes в settings/publish.yml "
        "с тем, что реально выдано (google-auth роняет RefreshError на невыданный скоуп)",
    ),
    (
        (
            "caller does not have permission",
            "does not have sufficient permissions",
            "permission_denied",
        ),
        "нет права записи — выдать сервис-аккаунту лист-ленты роль Редактор на таблице",
    ),
    (
        ("has not been used in project", "it is disabled"),
        "в quota-проекте (auth.quota_project) выключен нужный API — включить его "
        "или указать проект, где он включён",
    ),
    (
        ("requires a quota project",),
        "user-ADC без quota-проекта: задать auth.quota_project в settings/publish.yml",
    ),
    # Последним: транзиентное пережило все ретраи (api.retries) — значит у Google
    # действительно плохо, и повтор прогона осмысленнее любой правки конфига.
    (
        ("backenderror", "internal error encountered", "service is currently unavailable"),
        "транзиентный отказ Google пережил все ретраи — просто повторить прогон "
        "(леги изолированы, уже ok не переотправятся)",
    ),
)


def explain(exc: BaseException | str) -> str:
    """``"<hint> · <original>"`` when the failure is a known one, else the original text.

    >>> explain("HttpError 403 ... The user's Drive storage quota has been exceeded.")[:24]
    'диск аккаунта-владельца '
    >>> explain("HttpError 403 ... The caller does not have permission").split(" · ")[0]
    'нет права записи — выдать сервис-аккаунту лист-ленты роль Редактор на таблице'
    >>> explain("boom")
    'boom'
    """
    text = str(exc)
    low = text.lower()
    for needles, hint in _HINTS:
        if any(n in low for n in needles):
            return f"{hint} · {text}"
    return text
