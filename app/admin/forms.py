from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class DatasetForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=5000)])
    classification_id = SelectField("Classification", coerce=int, validators=[DataRequired()])
    source_system_id = SelectField("Source system", coerce=int, validators=[DataRequired()])
    owner_id = SelectField("Owner", validators=[DataRequired()])
    row_count = IntegerField("Row count", validators=[Optional(), NumberRange(min=0)])
    refresh_frequency = SelectField("Refresh frequency", validators=[DataRequired()])
    last_refreshed = DateField("Last refreshed", validators=[Optional()], format="%Y-%m-%d")
    is_active = BooleanField("Active")
    submit = SubmitField("Save")


class LookupForm(FlaskForm):
    label = StringField("Label", validators=[DataRequired(), Length(max=100)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Save")


class ClassificationForm(LookupForm):
    rank = IntegerField("Rank", validators=[DataRequired(), NumberRange(min=1)])


class SourceSystemForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    hostname = StringField("Hostname", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save")


class UserForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=255)])
    role = SelectField(
        "Role", choices=[("viewer", "Viewer"), ("admin", "Admin")], validators=[DataRequired()]
    )
    is_active = BooleanField("Active")
    submit = SubmitField("Save")


class ConfirmDeleteForm(FlaskForm):
    submit = SubmitField("Confirm delete")
