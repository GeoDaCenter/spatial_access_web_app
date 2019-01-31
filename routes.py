from flask import Flask, render_template, request, session, redirect, url_for, send_file, flash
from forms import InputForm
import pandas as pd
import wtforms

from decouple import config

from werkzeug.utils import secure_filename
from logging.config import dictConfig

# add folders to PATH so access/coverage modules can be accessed
import os, sys, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
community_analytics_dir = os.path.join(parentdir, "analytics")
sys.path.insert(0, community_analytics_dir) 

from spatial_access import p2p, CommunityAnalytics


app = Flask(__name__)

# to handle csrf 
app.secret_key = "development-key"
app.config["UPLOAD_FOLDER"] = config('upload_folder')
app.config["DATA_FOLDER"] = config('data_folder')


@app.route("/", methods=['GET', 'POST'])
def index():

	print("in index")
	form = InputForm()
	
	if request.method == 'POST':

		print("index POST")
		valid = True
		# parse custom_weight_dict
		custom_weight_dict = None
		if form.custom_weight_dict.data != "":
			try:
				custom_weight_dict = {}
				
				# If user has input more than just a single default list, it'll be separated by ;
				if form.custom_weight_dict.data.find(";") != -1:
					custom_lists = form.custom_weight_dict.data.split(";")
					for ls in custom_lists:
						list_name, values_string = ls.split(":")
						values_list_string = values_string.split(",")
						values_list = [float(value.strip()) for value in values_list_string]
						custom_weight_dict[list_name.strip()] = values_list
				# If a user has just input a default list
				else:
					list_name, values_string = form.custom_weight_dict.data.split(":")
					values_list_string = values_string.split(",")
					values_list = [float(value.strip()) for value in values_list_string]	
					custom_weight_dict["Default"] = values_list
			except:
				print("Error parsing custom weight dictionary")
				valid = False

		if form.validate():

			# retrieve file names and upload data to the server
			origin_file = request.files['origin_file']
			origin_filename = secure_filename(origin_file.filename)
			origin_file.save(os.path.join(app.config['UPLOAD_FOLDER'], origin_filename))
			destination_file = request.files['destination_file']
			destination_filename = secure_filename(destination_file.filename)
			destination_file.save(os.path.join(app.config['UPLOAD_FOLDER'], destination_filename))
			
			# create a dictionary associating field names used in the health code to the
			# fields in the data specified by the user
			origin_field_mapping = {"idx": form.origin_unique_id_field.data,
			"population": form.origin_population_field.data,
			"lat": form.origin_latitude_field.data,
			"lon": form.origin_longitude_field.data}
			
			destination_target_field = form.destination_target_field.data
			if form.coverage_measures_checkbox.data is False:
				destination_target_field = ""
			
			destination_field_mapping = {"idx": form.destination_unique_id_field.data,
			"target": destination_target_field,
			"category": form.destination_category_field.data,
			"lat": form.destination_latitude_field.data,
			"lon": form.destination_longitude_field.data}

			# update file paths to those on the server
			origin_filename = os.path.join(app.config["UPLOAD_FOLDER"], origin_filename)
			destination_filename = os.path.join(app.config["UPLOAD_FOLDER"], destination_filename)
			categories = form.destination_categories.data
			for x in form.destination_categories:
				print(x)
			maximum_travel_time = request.form["maximumTimeSlider"]
			
			# execute health code
			output_files = run_health_code(form.access_measures_checkbox.data,
				form.coverage_measures_checkbox.data,
				form.travel_mode.data,
				maximum_travel_time,
				origin_filename, 
				origin_field_mapping,
				destination_filename,
				destination_field_mapping,
				destination_category=categories,
				decay_function=form.decay_function.data,
				epsilon=float(request.form["epsilonValueSlider"]),
				walk_speed=float(request.form["walkSpeedSlider"]),
				custom_weight_dict=custom_weight_dict)
			
			return download_results(output_files)

		else:
			print(form.errors)
			return render_template('index.html', form=form)

	elif request.method == 'GET':
		
		print("index GET")
		
		if form.validate_on_submit:
			print('index GET validated')
			return render_template("index.html", form=form)
		else:
			print("index GET didn't validate")
			return render_template('about.html', form=form)

# @app.route('/data/<filename>')
@app.route("/return-file/<path:filename>")
def return_file(filename):
	
	if filename.startswith('app'):  # Flask is stripping of the leading slash
		filename = '/' + filename
	if (not (filename.startswith(app.config['DATA_FOLDER']) and filename.endswith('.csv'))) or '..' in filename:
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
	origin_field_mapping,
	destination_filename,
	destination_field_mapping,
	destination_category=None,
	decay_function=None,
	epsilon=None,
	walk_speed=None,
	custom_weight_dict=None):

	createTransitMatrix = True
	transit_matrix_file = "/Users/georgeyoliver/Documents/GitHub/CSDS/GeoDaCenter/contracts/analytics/data/walk_full_results_3.csv"
	output_files = []

	# Create a TransitMatrix if 
	if createTransitMatrix:
		transit_matrix = p2p.TransitMatrix(network_type=travel_mode,
							epsilon=epsilon,
							walk_speed=walk_speed,
	                    	primary_input=origin_filename,
							primary_input_field_mapping=origin_field_mapping,
							secondary_input=destination_filename,
							secondary_input_field_mapping=destination_field_mapping)

		transit_matrix.process()
		transit_matrix_filename = generate_file_name(app.config["DATA_FOLDER"], "travel_matrix", "csv")
		transit_matrix.write_to_file(transit_matrix_filename)
		
	# If any of the access metrics' checkboxes were checked,
	# create an AccessModel object and write output
	if access_measures_checkbox:

		access_model = CommunityAnalytics.AccessModel(network_type=travel_mode,
						source_filename=origin_filename,
	                    source_field_mapping=origin_field_mapping,
	                    dest_filename=destination_filename,
	                    dest_field_mapping=destination_field_mapping,
	                    sp_matrix_filename=transit_matrix_filename,
	                    decay_function=decay_function,
	                    limit_categories=destination_category,
	                    upper=int(maximum_travel_time))
		access_model.calculate(custom_weight_dict=custom_weight_dict)
		access_model.write_csv()
		output_files.append(access_model.output_filename)

	# If any of the coverage metrics' checkboxes were checked,
	# create an AccessModel object and write output
	if coverage_measures_checkbox:
		coverage_model = CommunityAnalytics.CoverageModel(network_type=travel_mode,
	                    source_filename=origin_filename,
	                    source_field_mapping=origin_field_mapping,
	                    dest_filename=destination_filename,
	                    dest_field_mapping=destination_field_mapping,
	                    sp_matrix_filename=transit_matrix_filename,
	                    limit_categories=destination_category,
	                    upper=int(maximum_travel_time))
		coverage_model.calculate()
		coverage_model.write_csv()
		output_files.append(coverage_model.output_filename)

	return output_files
    

if __name__ == "__main__":
	app.run(debug=True)
