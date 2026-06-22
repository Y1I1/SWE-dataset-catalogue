import uuid

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.catalogue import catalogue_bp
from app.catalogue.forms import AccessRequestForm, CatalogueSearchForm
from app.models import AccessRequest, Classification, RequestStatus, SourceSystem
from app.services import access_requests as access_request_service
from app.services.catalogue import get_active_dataset, search_datasets
from app.services.permissions import can_view_dataset


def _populate_search_form(form: CatalogueSearchForm) -> None:
    form.classification.choices = [("", "All")] + [
        (c.label, c.label) for c in Classification.query.order_by(Classification.rank).all()
    ]
    form.source_system.choices = [("", "All")] + [
        (s.name, s.name) for s in SourceSystem.query.order_by(SourceSystem.name).all()
    ]


@catalogue_bp.route("/")
@login_required
def list_datasets():
    form = CatalogueSearchForm(request.args)
    _populate_search_form(form)
    datasets = search_datasets(
        q=form.q.data,
        classification=form.classification.data or None,
        source_system=form.source_system.data or None,
        sort=form.sort.data or "name",
    )
    return render_template(
        "catalogue/list.html",
        title="Catalogue",
        form=form,
        datasets=datasets,
        can_view=can_view_dataset,
    )


@catalogue_bp.route("/datasets/<uuid:dataset_id>")
@login_required
def dataset_detail(dataset_id: uuid.UUID):
    dataset = get_active_dataset(dataset_id)
    if dataset is None:
        abort(404)

    allowed = can_view_dataset(current_user, dataset)
    request_form = AccessRequestForm()
    pending = None
    if not allowed:
        pending = AccessRequest.query.filter_by(
            dataset_id=dataset.id,
            requested_by=current_user.id,
            status=RequestStatus.pending,
        ).first()

    return render_template(
        "catalogue/detail.html",
        title=dataset.name,
        dataset=dataset,
        allowed=allowed,
        request_form=request_form,
        pending_request=pending,
    )


@catalogue_bp.route("/datasets/<uuid:dataset_id>/request-access", methods=["POST"])
@login_required
def request_access(dataset_id: uuid.UUID):
    dataset = get_active_dataset(dataset_id)
    if dataset is None:
        abort(404)

    form = AccessRequestForm()
    if request.method != "POST" or not form.validate():
        flash("Please provide a valid reason (at least 10 characters).", "error")
        return redirect(url_for("catalogue.dataset_detail", dataset_id=dataset.id))

    try:
        access_request_service.create_request(current_user, dataset, form.reason.data)
        flash("Access request submitted.", "success")
    except access_request_service.AccessRequestError as exc:
        flash(str(exc), "error")

    return redirect(url_for("catalogue.dataset_detail", dataset_id=dataset.id))


@catalogue_bp.route("/my-requests")
@login_required
def my_requests():
    requests = access_request_service.list_user_requests(current_user)
    return render_template(
        "catalogue/my_requests.html",
        title="My access requests",
        requests=requests,
    )
