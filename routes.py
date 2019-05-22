from flask import Flask, render_template, request, send_file, flash
from forms import InputForm
import wtforms

from decouple import config

from werkzeug.utils import secure_filename
# from logging.config import dictConfig

# add folders to PATH so access/coverage modules can be accessed
import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
community_analytics_dir = os.path.join(parentdir, "analytics")
sys.path.insert(0, community_analytics_dir) 

from spatial_access import p2p, Models
import spatial_access

app = Flask(__name__)

# to handle csrf 
app.secret_key = "development-key"
# app.config["UPLOAD_FOLDER"] = config('upload_folder')
# app.config["DATA_FOLDER"] = config('data_folder')
INPUTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "inputs")
OUTPUTS_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "outputs")
if not os.path.exists(INPUTS_FOLDER):
	os.mkdir(INPUTS_FOLDER)
if not os.path.exists(OUTPUTS_FOLDER):
	os.mkdir(OUTPUTS_FOLDER)

@app.route("/", methods=['GET', 'POST'])
def index():

	form = InputForm()
	
	if request.method == 'POST':

		valid = True
		# Test weight dicts
		# category_weight_dict = {"Hospitals": [3,2,1], "Federally Qualified Health Centers": [3,2,1]}
		# weight_list = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
		# category_weight_dict = {"Hospitals": weight_list, 
		# 	"Federally Qualified Health Centers": weight_list,
		# 	"All Free Health Clinics": weight_list,
		# 	"Other Health Providers": weight_list,
		# 	"School-Based Health Centers": weight_list}
		category_weight_dict = None

		if form.validate():

			# Collect input values from the form and request objects
			options = collect_options(form, request)

			# execute spatial_access code
			output_files = analyze(options)
			
			return results(output_files)

		else:
			print(form.errors)
			return render_template('index.html', form=form)

	elif request.method == 'GET':
		
		if form.validate_on_submit:
			print('index GET validated')
			return render_template("index.html", form=form)
		else:
			print("index GET didn't validate")
			return render_template('about.html', form=form)

# @app.route('/data/<filename>')
@app.route("/return-file/<path:filename>")
def return_file(filename):
	print(flask.root_path)
	if filename.startswith('app'):  # Flask is stripping of the leading slash
		filename = '/' + filename
	if (not (filename.startswith(OUTPUTS_FOLDER) and filename.endswith('.csv'))) or '..' in filename:
		raise ValueError("Invalid file name: %s" % filename)
	else:
		return send_file(filename, as_attachment=True)

@app.route("/results/")
def results(output_files):
	flash(output_files)
	return render_template("results.html")

def generate_file_name(directory, keyword, extension="csv"):

	filename = '{}/{}_0.{}'.format(directory, keyword, extension)
	counter = 1
	while os.path.isfile(filename):
		filename = '{}/{}_{}.{}'.format(directory, keyword, counter, extension)
		counter += 1
	return filename

def parse_custom_weight_dict(input_string):

	try:
		# If user has input more than just a single default list, it'll be separated by ;
		if form.custom_weight_dict.data.find(";") != -1:
			custom_lists = form.custom_weight_dict.data.split(";")
			for ls in custom_lists:
				list_name, values_string = ls.split(":")
				values_list_string = values_string.split(",")
				values_list = [float(value.strip()) for value in values_list_string]
				category_weight_dict[list_name.strip()] = values_list
		# If a user has just input a default list
		else:
			list_name, values_string = form.custom_weight_dict.data.split(":")
			values_list_string = values_string.split(",")
			values_list = [float(value.strip()) for value in values_list_string]	
			category_weight_dict["Default"] = values_list

		return category_weight_dict

	except:
		print("Error parsing custom weight dictionary")
		valid = False

def collect_options(form, request):

	options = {}

	# retrieve file names and upload data to the server
	origin_file = request.files['origin_file']
	origin_filename = secure_filename(origin_file.filename)
	origin_file.save(os.path.join(INPUTS_FOLDER, origin_filename))
	origin_filename = os.path.join(INPUTS_FOLDER, origin_filename)
	options["origin_filename"] = origin_filename
	
	destination_file = request.files['destination_file']
	destination_filename = secure_filename(destination_file.filename)
	destination_file.save(os.path.join(INPUTS_FOLDER, destination_filename))
	destination_filename = os.path.join(INPUTS_FOLDER, destination_filename)
	options["destination_filename"] = destination_filename
	
	# create a dictionary associating field names used in the health code to the
	# fields in the data specified by the user
	options["matrix_origin_field_mapping"] = {
		"idx": form.origin_unique_id_field.data,
		"lat": form.origin_latitude_field.data,
		"lon": form.origin_longitude_field.data
	}

	options["matrix_destination_field_mapping"] = {
		"idx": form.destination_unique_id_field.data,
		"lat": form.destination_latitude_field.data,
		"lon": form.destination_longitude_field.data
	}

	options["model_origin_field_mapping"] = {
		"idx": form.origin_unique_id_field.data,
		"lat": form.origin_latitude_field.data,
		"lon": form.origin_longitude_field.data,
		"population": form.origin_population_field.data
	}

	options["model_destination_field_mapping"] = {
		"idx": form.destination_unique_id_field.data,
		"lat": form.destination_latitude_field.data,
		"lon": form.destination_longitude_field.data,
		"capacity": form.destination_capacity_field.data,
		"category": form.destination_category_field.data
	}

	options["coverage_checked"] = form.coverage_checkbox.data
	options["access_1_checked"] = form.access_1_checkbox.data
	options["access_2_checked"] = form.access_2_checkbox.data
	options["access_3_checked"] = form.access_3_checkbox.data

	# Replace form values with 'skip' for certain inputs 
	# (the skip value is used when entering inputs via command line)
	if not options["coverage_checked"] and not options["access_3_checked"]:
		options["model_origin_field_mapping"]["population"] = "skip"

	if not options["coverage_checked"] and not options["access_2_checked"] and not options["access_3_checked"]:
		options["model_destination_field_mapping"]["capacity"] = "skip"

	if options["model_destination_field_mapping"]["category"] == "":
		options["model_destination_field_mapping"]["category"] = "skip"

	options["categories"] = form.destination_categories.data
	options["maximum_travel_time"] = int(request.form["maximumTimeSlider"]) * 60
	options["travel_mode"] = form.travel_mode.data
	options["decay_function"] = form.decay_function.data
	options["epsilon"] = float(request.form["epsilonValueSlider"])
	options["walk_speed"] = float(request.form["walkSpeedSlider"])

	# Parse custom weight dict
	if form.custom_weight_dict.data != "":
		options["category_weight_dict"] = parse_custom_weight_dict(form.custom_weight_dict.data)
	else:
		options["category_weight_dict"] = {}
	
	print("categories:", options["categories"])
	print("model_origin_field_mapping:", options["model_origin_field_mapping"])
	print("model_destination_field_mapping:", options["model_destination_field_mapping"])

	return options

def analyze(options):

	create_transit_matrix = True
	transit_matrix_file = "/Users/georgeyoliver/Documents/GitHub/CSDS/GeoDaCenter/contracts/analytics/data/walk_full_results_3.csv"
	output_files = []

	print("\n&&&& transit matrix inputs")
	print(options["travel_mode"])
	print(options["origin_filename"])
	print(options["matrix_origin_field_mapping"])
	print(options["destination_filename"])
	print(options["matrix_destination_field_mapping"])
	print(options["epsilon"])
	print(options["walk_speed"])
	
	# Create a TransitMatrix if 
	if create_transit_matrix:
		transit_matrix = p2p.TransitMatrix(network_type=options["travel_mode"],
							epsilon=options["epsilon"],
							walk_speed=options["walk_speed"],
							primary_input=options["origin_filename"],
							primary_hints=options["matrix_origin_field_mapping"],
							secondary_input=options["destination_filename"],
							secondary_hints=options["matrix_destination_field_mapping"])

		transit_matrix.process()
		transit_matrix_filename = generate_file_name(OUTPUTS_FOLDER, "travel_matrix", "tmx")
		transit_matrix.write_tmx(transit_matrix_filename)
	
	print("\n&&&& model inputs")
	print(options["travel_mode"])
	print(options["origin_filename"])
	print(options["destination_filename"])
	print(options["model_origin_field_mapping"])
	print(options["model_destination_field_mapping"])
	print(transit_matrix_filename)
	print(options["decay_function"])
	print(options["maximum_travel_time"])
	print(options["category_weight_dict"])
	print(spatial_access.__file__)

	access_outputs = []
	# If any of the access metrics' checkboxes were checked,
	# create an AccessModel object and write output
	if options["access_1_checked"]:
		access_model = Models.AccessModel(network_type=options["travel_mode"],
						sources_filename=options["origin_filename"],
						destinations_filename=options["destination_filename"],
						source_column_names=options["model_origin_field_mapping"],
						dest_column_names=options["model_destination_field_mapping"],
						transit_matrix_filename=transit_matrix_filename,
						decay_function=options["decay_function"])
		access_model_df = access_model.calculate(upper_threshold=options["maximum_travel_time"], 
												category_weight_dict=options["category_weight_dict"])
		
		access_count = Models.AccessCount(network_type=options["travel_mode"],
						sources_filename=options["origin_filename"],
						source_column_names=options["model_origin_field_mapping"],
						destinations_filename=options["destination_filename"],
						dest_column_names=options["model_destination_field_mapping"],
						transit_matrix_filename=transit_matrix_filename,
						categories=options["categories"])
		access_count_df = access_count.calculate(upper_threshold=options["maximum_travel_time"])

		access_time = Models.AccessTime(network_type=options["travel_mode"],
						sources_filename=options["origin_filename"],
						source_column_names=options["model_origin_field_mapping"],
						destinations_filename=options["destination_filename"],
						dest_column_names=options["model_destination_field_mapping"],
						transit_matrix_filename=transit_matrix_filename,
						categories=options["categories"])
		access_time_df = access_time.calculate()

		access_outputs.append(access_model_df)
		access_outputs.append(access_count_df)
		access_outputs.append(access_time_df)

	if options["access_2_checked"]:
		access_sum = Models.AccessSum(network_type=options["travel_mode"],
						sources_filename=options["origin_filename"],
						source_column_names=options["model_origin_field_mapping"],
						destinations_filename=options["destination_filename"],
						dest_column_names=options["model_destination_field_mapping"],
						transit_matrix_filename=transit_matrix_filename,
						categories=options["categories"])
		access_sum_df = access_sum.calculate(upper_threshold=options["maximum_travel_time"])

		access_outputs.append(access_sum_df)

	if options["access_3_checked"]:
		tsfca_model = Models.TSFCA(network_type=options["travel_mode"],
						sources_filename=options["origin_filename"],
						source_column_names=options["model_origin_field_mapping"],
						destinations_filename=options["destination_filename"],
						dest_column_names=options["model_destination_field_mapping"],
						transit_matrix_filename=transit_matrix_filename,
						categories=options["categories"])

		tsfca_model_df = tsfca_model.calculate(upper_threshold=options["maximum_travel_time"])

		access_outputs.append(tsfca_model_df)
		
	if options["access_1_checked"] or options["access_2_checked"] or options["access_3_checked"]:
		print("len access outputs", len(access_outputs))
		print(access_outputs)
		access_df = access_outputs[0]
		if len(access_outputs) > 1:
			for i in range(1,len(access_outputs)):
				access_df = access_df.join(access_outputs[i])
		
		access_file_name = generate_file_name(OUTPUTS_FOLDER, "access", "csv")
		access_df.to_csv(access_file_name)
		output_files.append(access_file_name)

	# If any of the coverage metrics' checkboxes were checked,
	# create an AccessModel object and write output
	if options["coverage_checked"]:
		coverage_model = Models.Coverage(network_type=options["travel_mode"],
						sources_filename=options["origin_filename"],
						destinations_filename=options["destination_filename"],
						source_column_names=options["model_origin_field_mapping"],
						dest_column_names=options["model_destination_field_mapping"],
						transit_matrix_filename=transit_matrix_filename,
						categories=options["categories"])
		coverage_model.calculate(upper_threshold=options["maximum_travel_time"])
		coverage_file_name = generate_file_name(OUTPUTS_FOLDER, "coverage", "csv")
		coverage_model.model_results.to_csv(coverage_file_name)
		output_files.append(coverage_file_name)

	return output_files
	
if __name__ == "__main__":
	app.run(debug=True)
