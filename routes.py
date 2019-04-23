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
		# parse custom_weight_dict
		category_weight_dict = {"Hospitals": [3,2,1], "Federally Qualified Health Centers": [3,2,1]}
		weight_list = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
		category_weight_dict = {"Hospitals": weight_list, 
			"Federally Qualified Health Centers": weight_list,
			"All Free Health Clinics": weight_list,
			"Other Health Providers": weight_list,
			"School-Based Health Centers": weight_list}
		category_weight_dict = None

		if form.custom_weight_dict.data != "":
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
			except:
				print("Error parsing custom weight dictionary")
				valid = False

		if form.validate():

			# retrieve file names and upload data to the server
			origin_file = request.files['origin_file']
			origin_filename = secure_filename(origin_file.filename)
			origin_file.save(os.path.join(INPUTS_FOLDER, origin_filename))
			destination_file = request.files['destination_file']
			destination_filename = secure_filename(destination_file.filename)
			destination_file.save(os.path.join(INPUTS_FOLDER, destination_filename))
			
			# create a dictionary associating field names used in the health code to the
			# fields in the data specified by the user
			matrix_origin_field_mapping = {
			"idx": form.origin_unique_id_field.data,
			"lat": form.origin_latitude_field.data,
			"lon": form.origin_longitude_field.data}

			destination_target_field = form.destination_target_field.data
			if form.coverage_measures_checkbox.data is False:
				destination_target_field = ""
			
			matrix_destination_field_mapping = {
			"idx": form.destination_unique_id_field.data,
			"lat": form.destination_latitude_field.data,
			"lon": form.destination_longitude_field.data}

			model_origin_field_mapping = {
			"idx": form.origin_unique_id_field.data,
			"lat": form.origin_latitude_field.data,
			"lon": form.origin_longitude_field.data,
			"population": form.origin_population_field.data}

			model_destination_field_mapping = {
			"idx": form.destination_unique_id_field.data,
			"lat": form.destination_latitude_field.data,
			"lon": form.destination_longitude_field.data,
			"capacity": form.destination_target_field.data,
			"category": form.destination_category_field.data
			}
			
			if form.coverage_measures_checkbox.data is False:
				model_origin_field_mapping["population"] = "skip";
				model_destination_field_mapping["capacity"] = "skip";

			# update file paths to those on the server
			origin_filename = os.path.join(INPUTS_FOLDER, origin_filename)
			destination_filename = os.path.join(INPUTS_FOLDER, destination_filename)
			categories = form.destination_categories.data
			for x in form.destination_categories:
				print(x)
			maximum_travel_time = int(request.form["maximumTimeSlider"]) * 60
			print("yaaas")
			print(float(request.form["epsilonValueSlider"]))
			# execute health code
			output_files = run_health_code(form.access_measures_checkbox.data,
				form.coverage_measures_checkbox.data,
				form.travel_mode.data,
				maximum_travel_time,
				origin_filename, 
				matrix_origin_field_mapping,
				destination_filename,
				matrix_destination_field_mapping,
				model_origin_field_mapping,
				model_destination_field_mapping,
				decay_function=form.decay_function.data,
				epsilon=float(request.form["epsilonValueSlider"]),
				walk_speed=float(request.form["walkSpeedSlider"]),
				category_weight_dict=category_weight_dict, 
				categories=categories)
			
			return download_results(output_files)

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

@app.route("/download-results/")
def download_results(output_files):
	flash(output_files)
	return render_template("download_results.html")

def generate_file_name(directory, keyword, extension="csv"):

	filename = '{}/{}_0.{}'.format(directory, keyword, extension)
	counter = 1
	while os.path.isfile(filename):
		filename = '{}/{}_{}.{}'.format(directory, keyword, counter, extension)
		counter += 1
	return filename

def run_health_code(access_measures_checkbox, 
	coverage_measures_checkbox,
	travel_mode,
	maximum_travel_time,
	origin_filename,
	matrix_origin_field_mapping,
	destination_filename,
	matrix_destination_field_mapping,
	model_origin_field_mapping,
	model_destination_field_mapping,
	decay_function=None,
	epsilon=None,
	walk_speed=None,
	category_weight_dict=None,
	categories=None):

	create_transit_matrix = True
	transit_matrix_file = "/Users/georgeyoliver/Documents/GitHub/CSDS/GeoDaCenter/contracts/analytics/data/walk_full_results_3.csv"
	output_files = []

	print("transit matrix inputs")
	print(travel_mode)
	print(origin_filename)
	print(matrix_origin_field_mapping)
	print(destination_filename)
	print(matrix_destination_field_mapping)
	print(epsilon)
	print(walk_speed)
	
	# Create a TransitMatrix if 
	if create_transit_matrix:
		transit_matrix = p2p.TransitMatrix(network_type=travel_mode,
							epsilon=epsilon,
							walk_speed=walk_speed,
	                    	primary_input=origin_filename,
							primary_hints=matrix_origin_field_mapping,
							secondary_input=destination_filename,
							secondary_hints=matrix_destination_field_mapping)

		transit_matrix.process()
		transit_matrix_filename = generate_file_name(OUTPUTS_FOLDER, "travel_matrix", "tmx")
		transit_matrix.write_tmx(transit_matrix_filename)
	
	print("\naccess inputs")
	print(travel_mode)
	print(origin_filename)
	print(destination_filename)
	print(model_origin_field_mapping)
	print(model_destination_field_mapping)
	print(transit_matrix_filename)
	print(decay_function)
	print(maximum_travel_time)
	print(category_weight_dict)

	print(spatial_access.__file__)

	# If any of the access metrics' checkboxes were checked,
	# create an AccessModel object and write output
	if access_measures_checkbox:
		access_model = Models.AccessModel(network_type=travel_mode,
						sources_filename=origin_filename,
	                    destinations_filename=destination_filename,
	                    source_column_names=model_origin_field_mapping,
	                    dest_column_names=model_destination_field_mapping,
	                    transit_matrix_filename=transit_matrix_filename,
	                    decay_function=decay_function)
		access_model.calculate(upper_threshold=maximum_travel_time, category_weight_dict=category_weight_dict)
		access_file_name = generate_file_name(OUTPUTS_FOLDER, "access", "csv")
		access_model.model_results.to_csv(access_file_name)
		output_files.append(access_file_name)

	# If any of the coverage metrics' checkboxes were checked,
	# create an AccessModel object and write output
	if coverage_measures_checkbox:
		coverage_model = Models.Coverage(network_type=travel_mode,
	                    sources_filename=origin_filename,
	                    destinations_filename=destination_filename,
	                    source_column_names=model_origin_field_mapping,
	                    dest_column_names=model_destination_field_mapping,
	                    transit_matrix_filename=transit_matrix_filename,
	                    categories=categories)
		coverage_model.calculate(upper_threshold=maximum_travel_time)
		coverage_file_name = generate_file_name(OUTPUTS_FOLDER, "coverage", "csv")
		coverage_model.model_results.to_csv(coverage_file_name)
		output_files.append(coverage_file_name)

	return output_files
    

if __name__ == "__main__":
	app.run(debug=True)
