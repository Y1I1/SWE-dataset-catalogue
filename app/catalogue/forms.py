from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class CatalogueSearchForm(FlaskForm):
    class Meta:
        csrf = False

    q = StringField("Search", validators=[Optional(), Length(max=255)])
    classification = SelectField("Classification", choices=[], validators=[Optional()])
    source_system = SelectField("Source system", choices=[], validators=[Optional()])
    sort = SelectField(
        "Sort by",
        choices=[("name", "Name"), ("last_refreshed", "Last refreshed")],
        default="name",
    )
    submit = SubmitField("Search")


class AccessRequestForm(FlaskForm):
    reason = TextAreaField(
        "Reason for access",
        validators=[DataRequired(), Length(min=10, max=2000)],
    )
    submit = SubmitField("Submit request")
