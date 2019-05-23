from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField, SelectField, SelectMultipleField, StringField, SubmitField, validators, ValidationError
from customized_flask_classes import SelectFieldWithoutPreValidation, SelectMultipleFieldWithoutPreValidation

access_checked = False
coverage_checked = False
ACCESS_1_LABEL = 'Access Score, Access Count, Access Time'
ACCESS_2_LABEL = 'Access Sum'
ACCESS_3_LABEL = 'Two-Step Floating Catchment Area Score'
COVERAGE_LABEL = 'Population Served, Per-Capita Spending'

def validate_access_or_coverage_chosen(form, field):
	
	"""
	This custom validator is used to verify that the user has checked at least one of the access measures checkbox
	or coverage measures checkbox. 
	"""

	global access_checked
	global coverage_checked

	if field.id in ("access_1_checkbox", "access_2_checkbox", "access_3_checkbox"):
		access_checked = field.data or access_checked
		return
	if field.id == "coverage_checkbox":
		coverage_checked = field.data
		print("Access Measure checkbox checked:", access_checked, "; Coverage Measure checkbox checked:", coverage_checked)
		if access_checked is False and coverage_checked is False:
			raise ValidationError("Please check at least one of the Access or Coverage checkboxes.'")
		else:
			return
	
class InputForm(FlaskForm):
	
	access_1_checkbox = BooleanField(ACCESS_1_LABEL, [validate_access_or_coverage_chosen])
	access_2_checkbox = BooleanField(ACCESS_2_LABEL, [validate_access_or_coverage_chosen])
	access_3_checkbox = BooleanField(ACCESS_3_LABEL, [validate_access_or_coverage_chosen])
	coverage_checkbox = BooleanField(COVERAGE_LABEL, [validate_access_or_coverage_chosen])
	travel_mode = SelectField('Travel mode',
		choices=[('walk', 'Walk'),
		# ('otp', 'Transit'),
		('bike', 'Bike'),
		('drive', 'Drive')])

	# Advanced settings
	# walk_speed = 
	decay_function = SelectField("Distance decay function <i class='material-icons md-18 infoButton' id='decayFunctionInfoButton' title='Click to view info text'>info</i>",
		choices=[('linear', 'Linear'),
		('root', 'Inverse square root'),
		('logit', 'Logit')])

	custom_weight_dict = StringField("Relative weight for the n<sup>th</sup> facility of the same category <i class='material-icons md-18 infoButton' id='facilityWeightListInfoButton' title='Click to view info text'>info</i>")

	origin_file = FileField('Origin file', [validators.DataRequired('Please specify an origin file.')])
	origin_unique_id_field = SelectFieldWithoutPreValidation("Unique ID field <i class='material-icons  md-18 infoButton' id='originUniqueIdFieldButton' title='Click to view info text'>info</i>", choices=[])
	origin_latitude_field = SelectFieldWithoutPreValidation("Latitude (y-coordinate) field", choices=[])
	origin_longitude_field = SelectFieldWithoutPreValidation("Longitude (x-coordinate) field", choices=[])
	origin_population_field = SelectFieldWithoutPreValidation("Population field", choices=[])
	destination_file = FileField('Destination file', [validators.DataRequired('Please specify a destination file.')])
	destination_unique_id_field = SelectFieldWithoutPreValidation("Unique id field <i class='material-icons  md-18 infoButton' id='destinationUniqueIdFieldButton' title='Click to view info text'>info</i>", choices=[])
	destination_latitude_field = SelectFieldWithoutPreValidation("Latitude (y-coordinate) field", choices=[])
	destination_longitude_field = SelectFieldWithoutPreValidation("Longitude (x-coordinate) field", choices=[])
	destination_capacity_field = SelectFieldWithoutPreValidation("Capacity field", choices=[])
	destination_category_field = SelectFieldWithoutPreValidation("Category field (Optional)", choices=[])
	destination_categories = SelectMultipleFieldWithoutPreValidation("Choose categories to calculate measures for (Optional)", choices=[])
	
	submit = SubmitField('Submit')