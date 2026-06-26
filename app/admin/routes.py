import uuid

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.admin import admin_bp
from app.admin.forms import (
    ClassificationForm,
    ConfirmDeleteForm,
    DatasetForm,
    SourceSystemForm,
    UserForm,
)
from app.db import db
from app.models import (
    AccessRequest,
    Classification,
    Dataset,
    RefreshFrequency,
    RequestStatus,
    SourceSystem,
    User,
    UserRole,
)
from app.models.audit_event import AuditAction
from app.security.decorators import role_required
from app.services import access_requests as access_request_service
from app.services.admin import (
    AdminValidationError,
    classification_in_use,
    parse_optional_date,
    parse_refresh_frequency,
    source_system_in_use,
    validate_dataset_name,
    validate_unique_label,
    validate_unique_name,
    validate_unique_rank,
)
from app.services.audit import write_audit


def _populate_dataset_form(form: DatasetForm) -> None:
    form.classification_id.choices = [
        (c.id, c.label) for c in Classification.query.order_by(Classification.rank).all()
    ]
    form.source_system_id.choices = [
        (s.id, s.name) for s in SourceSystem.query.order_by(SourceSystem.name).all()
    ]
    form.owner_id.choices = [
        (str(u.id), f"{u.full_name} ({u.email})") for u in User.query.order_by(User.email).all()
    ]
    form.refresh_frequency.choices = [
        (f.value, f.value.replace("_", " ").title()) for f in RefreshFrequency
    ]


@admin_bp.route("/")
@role_required(UserRole.admin)
def dashboard():
    pending_count = AccessRequest.query.filter_by(status=RequestStatus.pending).count()
    return render_template(
        "admin/dashboard.html",
        title="Admin",
        pending_count=pending_count,
    )


@admin_bp.route("/access-requests")
@role_required(UserRole.admin)
def access_requests():
    status_filter = request.args.get("status", "").strip()
    status = None
    if status_filter:
        try:
            status = RequestStatus(status_filter)
        except ValueError:
            flash("Invalid status filter.", "error")
    requests = access_request_service.list_all_requests(status)
    return render_template(
        "admin/access_requests.html",
        title="Access requests",
        requests=requests,
        status_filter=status_filter,
    )


@admin_bp.route("/access-requests/<uuid:request_id>/approve", methods=["POST"])
@role_required(UserRole.admin)
def approve_request(request_id: uuid.UUID):
    access_request = db.session.get(AccessRequest, request_id)
    if access_request is None:
        abort(404)
    try:
        access_request_service.decide_request(access_request, current_user, RequestStatus.approved)
        flash("Access request approved.", "success")
    except access_request_service.AccessRequestError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.access_requests"))


@admin_bp.route("/access-requests/<uuid:request_id>/reject", methods=["POST"])
@role_required(UserRole.admin)
def reject_request(request_id: uuid.UUID):
    access_request = db.session.get(AccessRequest, request_id)
    if access_request is None:
        abort(404)
    try:
        access_request_service.decide_request(access_request, current_user, RequestStatus.rejected)
        flash("Access request rejected.", "success")
    except access_request_service.AccessRequestError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.access_requests"))


@admin_bp.route("/datasets")
@role_required(UserRole.admin)
def datasets():
    rows = Dataset.query.order_by(Dataset.name).all()
    return render_template("admin/datasets/list.html", title="Datasets", datasets=rows)


@admin_bp.route("/datasets/new", methods=["GET", "POST"])
@role_required(UserRole.admin)
def dataset_create():
    form = DatasetForm()
    _populate_dataset_form(form)
    form.is_active.data = True
    if request.method == "POST" and form.validate():
        try:
            dataset = Dataset(
                name=validate_dataset_name(form.name.data),
                description=(form.description.data or "").strip() or None,
                classification_id=form.classification_id.data,
                source_system_id=form.source_system_id.data,
                owner_id=uuid.UUID(form.owner_id.data),
                row_count=form.row_count.data,
                refresh_frequency=parse_refresh_frequency(form.refresh_frequency.data),
                last_refreshed=parse_optional_date(form.last_refreshed.data, "Last refreshed"),
                is_active=form.is_active.data,
            )
            db.session.add(dataset)
            db.session.flush()
            write_audit(
                AuditAction.dataset_created,
                target_type="dataset",
                target_id=dataset.id,
                actor_id=current_user.id,
                meta={"name": dataset.name},
            )
            db.session.commit()
            flash("Dataset created.", "success")
            return redirect(url_for("admin.datasets"))
        except AdminValidationError as exc:
            flash(str(exc), "error")
    return render_template("admin/datasets/form.html", title="New dataset", form=form)


@admin_bp.route("/datasets/<uuid:dataset_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.admin)
def dataset_edit(dataset_id: uuid.UUID):
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None:
        abort(404)
    form = DatasetForm(obj=dataset)
    _populate_dataset_form(form)
    form.owner_id.data = str(dataset.owner_id)
    form.refresh_frequency.data = dataset.refresh_frequency.value
    if request.method == "POST" and form.validate():
        try:
            dataset.name = validate_dataset_name(form.name.data, dataset)
            dataset.description = (form.description.data or "").strip() or None
            dataset.classification_id = form.classification_id.data
            dataset.source_system_id = form.source_system_id.data
            dataset.owner_id = uuid.UUID(form.owner_id.data)
            dataset.row_count = form.row_count.data
            dataset.refresh_frequency = parse_refresh_frequency(form.refresh_frequency.data)
            dataset.last_refreshed = parse_optional_date(form.last_refreshed.data, "Last refreshed")
            dataset.is_active = form.is_active.data
            write_audit(
                AuditAction.dataset_updated,
                target_type="dataset",
                target_id=dataset.id,
                actor_id=current_user.id,
                meta={"name": dataset.name},
            )
            db.session.commit()
            flash("Dataset updated.", "success")
            return redirect(url_for("admin.datasets"))
        except AdminValidationError as exc:
            flash(str(exc), "error")
    return render_template(
        "admin/datasets/form.html",
        title=f"Edit {dataset.name}",
        form=form,
        dataset=dataset,
    )


@admin_bp.route("/datasets/<uuid:dataset_id>/delete", methods=["GET", "POST"])
@role_required(UserRole.admin)
def dataset_delete(dataset_id: uuid.UUID):
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None:
        abort(404)
    form = ConfirmDeleteForm()
    if request.method == "POST" and form.validate():
        dataset.is_active = False
        write_audit(
            AuditAction.dataset_deactivated,
            target_type="dataset",
            target_id=dataset.id,
            actor_id=current_user.id,
            meta={"name": dataset.name},
        )
        db.session.commit()
        flash("Dataset deactivated.", "success")
        return redirect(url_for("admin.datasets"))
    return render_template(
        "admin/datasets/delete.html",
        title=f"Deactivate {dataset.name}",
        form=form,
        dataset=dataset,
    )


@admin_bp.route("/classifications")
@role_required(UserRole.admin)
def classifications():
    rows = Classification.query.order_by(Classification.rank).all()
    return render_template(
        "admin/classifications/list.html",
        title="Classifications",
        classifications=rows,
    )


@admin_bp.route("/classifications/new", methods=["GET", "POST"])
@role_required(UserRole.admin)
def classification_create():
    form = ClassificationForm()
    if request.method == "POST" and form.validate():
        try:
            label = validate_unique_label(Classification, form.label.data)
            rank = validate_unique_rank(form.rank.data)
            row = Classification(
                label=label,
                rank=rank,
                description=(form.description.data or "").strip() or None,
            )
            db.session.add(row)
            db.session.flush()
            write_audit(
                AuditAction.classification_created,
                target_type="classification",
                target_id=row.id,
                actor_id=current_user.id,
                meta={"label": label, "rank": rank},
            )
            db.session.commit()
            flash("Classification created.", "success")
            return redirect(url_for("admin.classifications"))
        except AdminValidationError as exc:
            flash(str(exc), "error")
    return render_template("admin/classifications/form.html", title="New classification", form=form)


@admin_bp.route("/classifications/<int:item_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.admin)
def classification_edit(item_id: int):
    row = db.session.get(Classification, item_id)
    if row is None:
        abort(404)
    form = ClassificationForm(obj=row)
    if request.method == "POST" and form.validate():
        try:
            row.label = validate_unique_label(Classification, form.label.data, row.id)
            row.rank = validate_unique_rank(form.rank.data, row.id)
            row.description = (form.description.data or "").strip() or None
            write_audit(
                AuditAction.classification_updated,
                target_type="classification",
                target_id=row.id,
                actor_id=current_user.id,
                meta={"label": row.label, "rank": row.rank},
            )
            db.session.commit()
            flash("Classification updated.", "success")
            return redirect(url_for("admin.classifications"))
        except AdminValidationError as exc:
            flash(str(exc), "error")
    return render_template(
        "admin/classifications/form.html",
        title=f"Edit {row.label}",
        form=form,
        item=row,
    )


@admin_bp.route("/classifications/<int:item_id>/delete", methods=["GET", "POST"])
@role_required(UserRole.admin)
def classification_delete(item_id: int):
    row = db.session.get(Classification, item_id)
    if row is None:
        abort(404)
    form = ConfirmDeleteForm()
    if request.method == "POST" and form.validate():
        if classification_in_use(row.id):
            flash("Cannot delete: active datasets still use this classification.", "error")
        else:
            write_audit(
                AuditAction.classification_deleted,
                target_type="classification",
                target_id=row.id,
                actor_id=current_user.id,
                meta={"label": row.label},
            )
            db.session.delete(row)
            db.session.commit()
            flash("Classification deleted.", "success")
            return redirect(url_for("admin.classifications"))
    return render_template(
        "admin/classifications/delete.html",
        title=f"Delete {row.label}",
        form=form,
        item=row,
    )


@admin_bp.route("/source-systems")
@role_required(UserRole.admin)
def source_systems():
    rows = SourceSystem.query.order_by(SourceSystem.name).all()
    return render_template(
        "admin/source_systems/list.html",
        title="Source systems",
        source_systems=rows,
    )


@admin_bp.route("/source-systems/new", methods=["GET", "POST"])
@role_required(UserRole.admin)
def source_system_create():
    form = SourceSystemForm()
    if request.method == "POST" and form.validate():
        try:
            name = validate_unique_name(SourceSystem, form.name.data)
            row = SourceSystem(
                name=name,
                description=(form.description.data or "").strip() or None,
                hostname=(form.hostname.data or "").strip() or None,
            )
            db.session.add(row)
            db.session.flush()
            write_audit(
                AuditAction.source_system_created,
                target_type="source_system",
                target_id=row.id,
                actor_id=current_user.id,
                meta={"name": name},
            )
            db.session.commit()
            flash("Source system created.", "success")
            return redirect(url_for("admin.source_systems"))
        except AdminValidationError as exc:
            flash(str(exc), "error")
    return render_template("admin/source_systems/form.html", title="New source system", form=form)


@admin_bp.route("/source-systems/<int:item_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.admin)
def source_system_edit(item_id: int):
    row = db.session.get(SourceSystem, item_id)
    if row is None:
        abort(404)
    form = SourceSystemForm(obj=row)
    if request.method == "POST" and form.validate():
        try:
            row.name = validate_unique_name(SourceSystem, form.name.data, row.id)
            row.description = (form.description.data or "").strip() or None
            row.hostname = (form.hostname.data or "").strip() or None
            write_audit(
                AuditAction.source_system_updated,
                target_type="source_system",
                target_id=row.id,
                actor_id=current_user.id,
                meta={"name": row.name},
            )
            db.session.commit()
            flash("Source system updated.", "success")
            return redirect(url_for("admin.source_systems"))
        except AdminValidationError as exc:
            flash(str(exc), "error")
    return render_template(
        "admin/source_systems/form.html",
        title=f"Edit {row.name}",
        form=form,
        item=row,
    )


@admin_bp.route("/source-systems/<int:item_id>/delete", methods=["GET", "POST"])
@role_required(UserRole.admin)
def source_system_delete(item_id: int):
    row = db.session.get(SourceSystem, item_id)
    if row is None:
        abort(404)
    form = ConfirmDeleteForm()
    if request.method == "POST" and form.validate():
        if source_system_in_use(row.id):
            flash("Cannot delete: active datasets reference this source system.", "error")
        else:
            write_audit(
                AuditAction.source_system_deleted,
                target_type="source_system",
                target_id=row.id,
                actor_id=current_user.id,
                meta={"name": row.name},
            )
            db.session.delete(row)
            db.session.commit()
            flash("Source system deleted.", "success")
            return redirect(url_for("admin.source_systems"))
    return render_template(
        "admin/source_systems/delete.html",
        title=f"Delete {row.name}",
        form=form,
        item=row,
    )


@admin_bp.route("/users")
@role_required(UserRole.admin)
def users():
    rows = User.query.order_by(User.email).all()
    return render_template("admin/users/list.html", title="Users", users=rows)


@admin_bp.route("/users/<uuid:user_id>/edit", methods=["GET", "POST"])
@role_required(UserRole.admin)
def user_edit(user_id: uuid.UUID):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    form = UserForm(obj=user)
    form.role.data = user.role.value
    if request.method == "POST" and form.validate():
        old_role = user.role
        old_active = user.is_active
        user.full_name = form.full_name.data.strip()
        user.role = UserRole(form.role.data)
        user.is_active = form.is_active.data

        if user.role != old_role:
            write_audit(
                AuditAction.user_role_changed,
                target_type="user",
                target_id=user.id,
                actor_id=current_user.id,
                meta={"from": old_role.value, "to": user.role.value},
            )
        if user.is_active != old_active:
            action = AuditAction.user_activated if user.is_active else AuditAction.user_deactivated
            write_audit(
                action,
                target_type="user",
                target_id=user.id,
                actor_id=current_user.id,
            )

        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template(
        "admin/users/form.html", title=f"Edit {user.email}", form=form, user=user
    )
