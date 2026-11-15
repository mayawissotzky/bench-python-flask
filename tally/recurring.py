from collections import defaultdict
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .services import recurring

bp = Blueprint("recurring", __name__, url_prefix="/recurring")


def _categories():
    return current_app.config["EXPENSE_CATEGORIES"]


def _form_context(**extra):
    return {"categories": _categories(), "frequencies": recurring.FREQUENCIES, **extra}


def _totals_by_currency(schedules):
    totals = defaultdict(Decimal)
    for schedule in schedules:
        if schedule.state == "active":
            totals[schedule.currency] += recurring.monthly_equivalent(schedule)
    return sorted(totals.items())


@bp.get("/")
@login_required
def index():
    schedules = recurring.owned_schedules(current_user.id)
    return render_template(
        "recurring/list.html",
        schedules=schedules,
        totals=_totals_by_currency(schedules),
        frequencies=recurring.FREQUENCIES,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        data = recurring.parse_form(request.form, _categories())
        if data.ok:
            schedule = recurring.create_schedule(current_user, data)
            flash("Recurring expense saved.", "success")
            return redirect(url_for("recurring.detail", schedule_id=schedule.id))
        for error in data.errors:
            flash(error, "error")
        return render_template("recurring/form.html", **_form_context(form=data, schedule=None)), 400
    return render_template("recurring/form.html", **_form_context(form=recurring.ScheduleForm(), schedule=None))


@bp.get("/<int:schedule_id>")
@login_required
def detail(schedule_id):
    schedule = recurring.get_owned_schedule(current_user.id, schedule_id)
    return render_template(
        "recurring/detail.html",
        schedule=schedule,
        upcoming=recurring.upcoming(schedule) if schedule.active else [],
        monthly=recurring.monthly_equivalent(schedule),
        frequencies=recurring.FREQUENCIES,
    )


@bp.route("/<int:schedule_id>/edit", methods=["GET", "POST"])
@login_required
def edit(schedule_id):
    schedule = recurring.get_owned_schedule(current_user.id, schedule_id)
    if request.method == "POST":
        data = recurring.parse_form(request.form, _categories())
        if data.ok:
            recurring.update_schedule(schedule, data)
            flash("Recurring expense updated.", "success")
            return redirect(url_for("recurring.detail", schedule_id=schedule.id))
        for error in data.errors:
            flash(error, "error")
        return render_template("recurring/form.html", **_form_context(form=data, schedule=schedule)), 400
    form = recurring.ScheduleForm(
        description=schedule.description,
        category=schedule.category,
        amount=schedule.amount,
        currency=schedule.currency,
        frequency=schedule.frequency,
        start_date=schedule.start_date,
        end_date=schedule.end_date,
        notes=schedule.notes,
    )
    return render_template("recurring/form.html", **_form_context(form=form, schedule=schedule))


@bp.post("/<int:schedule_id>/pause")
@login_required
def pause(schedule_id):
    schedule = recurring.get_owned_schedule(current_user.id, schedule_id)
    recurring.set_active(schedule, False)
    flash("Recurring expense paused.", "success")
    return redirect(url_for("recurring.detail", schedule_id=schedule.id))


@bp.post("/<int:schedule_id>/resume")
@login_required
def resume(schedule_id):
    schedule = recurring.get_owned_schedule(current_user.id, schedule_id)
    recurring.set_active(schedule, True)
    flash("Recurring expense resumed.", "success")
    return redirect(url_for("recurring.detail", schedule_id=schedule.id))


@bp.post("/<int:schedule_id>/skip")
@login_required
def skip(schedule_id):
    schedule = recurring.get_owned_schedule(current_user.id, schedule_id)
    if recurring.skip_next(schedule):
        flash("Skipped the next occurrence.", "success")
    else:
        flash("This schedule has no occurrences left.", "error")
    return redirect(url_for("recurring.detail", schedule_id=schedule.id))


@bp.post("/<int:schedule_id>/delete")
@login_required
def delete(schedule_id):
    schedule = recurring.get_owned_schedule(current_user.id, schedule_id)
    recurring.delete_schedule(schedule)
    flash("Recurring expense deleted. Expenses it already created are kept.", "success")
    return redirect(url_for("recurring.index"))


@bp.post("/generate")
@login_required
def generate():
    created = recurring.generate_due_for_owner(current_user.id)
    if created:
        flash(f"Created {created} expense{'s' if created != 1 else ''} from your recurring schedules.", "success")
    else:
        flash("Nothing is due yet.", "info")
    return redirect(url_for("recurring.index"))


@bp.get("/team")
@login_required
def team():
    if not current_user.team_id:
        return redirect(url_for("teams.create"))
    if not current_user.is_manager:
        abort(403)
    schedules = recurring.team_schedules(current_user.team_id)
    by_member = defaultdict(list)
    for schedule in schedules:
        by_member[schedule.owner].append(schedule)
    return render_template(
        "recurring/team.html",
        by_member=sorted(by_member.items(), key=lambda item: item[0].name.lower()),
        totals=_totals_by_currency(schedules),
        frequencies=recurring.FREQUENCIES,
    )
