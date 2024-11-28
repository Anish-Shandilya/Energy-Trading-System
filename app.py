from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use the Agg backend for non-GUI environments
import matplotlib.pyplot as plt
from datetime import datetime
import shutil

app = Flask(__name__)

# List to store user data (id, email, password)
users = []
next_id = 1  # User IDs start from 1

producers = []

load_values = {'A': 120, 'B': 2000, 'C': 300, 'D': 1000, 'Misc': 580}


class Producer:
    def __init__(self, user_id, date_of_transaction, duration, amount_of_power, price, time_slot):
        self.user_id = user_id
        self.date_of_transaction = date_of_transaction
        self.duration = duration
        self.amount_of_power = amount_of_power
        self.price = price
        self.time_slot = time_slot

class Consumer:
    def __init__(self, user_id, date_of_transaction, duration, amount_of_power, price, time_slot):
        self.user_id = user_id
        self.date_of_transaction = date_of_transaction
        self.duration = duration
        self.amount_of_power = amount_of_power
        self.price = price
        self.time_slot = time_slot

# Marketplace algorithm to find the best matching producer
def find_best_producer(consumer):
    matching_producers = producers
    # Sort producers based on the criteria (date, duration, etc.)
    matching_producers.sort(key=lambda p: (

        abs((p.date_of_transaction - consumer.date_of_transaction).days),  # Closest date

        abs(p.time_slot - consumer.time_slot),  # Closest time slot

        abs(p.price - consumer.price),  # Closest price

        abs(p.duration - consumer.duration),  # Closest duration

        
        abs(p.amount_of_power - consumer.amount_of_power)  # Closest power
       
       
    ))

    if matching_producers:
        return matching_producers[0]  # Best producer
    return None


if not os.path.exists('static/graphs'):
    os.makedirs('static/graphs')

user_data = {}  # Store the data for each user


appHasRunBefore: bool = False

def clear_upload_folder(upload_folder):
    """Remove all files from the upload folder."""
   
    if os.path.exists(upload_folder):
        # Remove all files and folders in the upload folder
        for filename in os.listdir(upload_folder):
            file_path = os.path.join(upload_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

@app.before_request
def initialize():
    """Initialize the app and clear the upload folder on startup."""
    global appHasRunBefore
    if not appHasRunBefore:
        clear_upload_folder('Battery_data')
        clear_upload_folder('Grid_data')
        clear_upload_folder('static/graphs')
        clear_upload_folder('Load_data')
        clear_upload_folder('uploads')
    
    appHasRunBefore = True




@app.route('/')
def home():
    return render_template('home.html')  # Home page with signup and login options

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_id = len(users) + 1
        users.append({'id': user_id, 'email': email, 'password': password})
        return redirect(url_for('data', user_id=user_id))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Initialize an error variable

    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        password = request.form['password']

        # Check if user ID and password match
        for user in users:
            if user['id'] == user_id and user['password'] == password:
                # Redirect to the dashboard if login is successful
                return redirect(url_for('dashboard', user_id=user_id))

        # If login fails, set an error message
        error = "Invalid ID or password"

    return render_template('login.html', error=error)

@app.route('/data/<int:user_id>', methods=['GET', 'POST'])
def data(user_id):
    if request.method == 'POST':
        load_profile_file = request.files['load_profile']
        power_generated_file = request.files['power_generated']
        utility_grid_file = request.files['utility_grid']

        # Read Excel files
        load_profile = pd.read_excel(load_profile_file)
        power_generated = pd.read_excel(power_generated_file)
        utility_grid = pd.read_excel(utility_grid_file)

        # Store data
        user_data[user_id] = {
            'load_profile': load_profile,
            'power_generated': power_generated,
            'utility_grid': utility_grid
        }

        # Generate graphs
        generate_graphs(user_id, load_profile, power_generated, utility_grid)

        return redirect(url_for('dashboard', user_id=user_id))

    return render_template('data.html', user_id=user_id)

# Function to generate all required graphs and save them as images
def generate_graphs(user_id, load_profile, power_generated, utility_grid):
    # First Graph: Load Profile (Stacked Bar Chart)
    plt.figure()
    a = load_profile['Total']
    load_profile = load_profile.drop(columns=['Total'])
    load_profile.plot(x='Time of Use in Hours', kind='bar', stacked=True)
    plt.title(f'Load Profile for User {user_id}')
    plt.savefig(f'static/graphs/user_{user_id}_load_profile.png')
    plt.close()

    # Second Graph: Power Generated (Bar Chart)
    plt.figure()
    power_generated.plot(x='Time of Use in Hours', y='Total Generation', kind='line', color='orange')
    plt.title(f'Power Generated for User {user_id}')
    plt.savefig(f'static/graphs/user_{user_id}_power_generated.png')
    plt.close()

    # Third Graph: Power Provided by Utility Grid (Bar Chart)
    plt.figure()
    utility_grid.plot(x='Time of Use in Hours', y='Total Generation', kind='bar', color='green')
    plt.title(f'Power Provided by Utility Grid for User {user_id}')
    plt.savefig(f'static/graphs/user_{user_id}_utility_grid.png')
    plt.close()

    # Fourth Graph: Net Load (Load Profile Total Usage - Power Generated)
    
    net_load = power_generated['Total Generation'] - a
    plt.figure()
    colors = ['blue' if val > 0 else 'red' for val in net_load]
    plt.bar(load_profile['Time of Use in Hours'], net_load, color=colors)
    plt.xticks(rotation=90)
    plt.title(f'Surplus/Deficit for User {user_id}')
    plt.savefig(f'static/graphs/user_{user_id}_net_load.png')
    plt.close()

@app.route('/stats/<int:user_id>')
def stats(user_id):
    graphs = {
        'load_profile': f'/static/graphs/user_{user_id}_load_profile.png',
        'power_generated': f'/static/graphs/user_{user_id}_power_generated.png',
        'utility_grid': f'/static/graphs/user_{user_id}_utility_grid.png',
        'net_load': f'/static/graphs/user_{user_id}_net_load.png'
    }
    return render_template('stats.html', user_id=user_id, graphs=graphs)

@app.route('/dashboard/<int:user_id>')
def dashboard(user_id):
    
    return render_template('dashboard.html', user_id=user_id)

@app.route('/marketplace', methods=['GET', 'POST'])
def marketplace():
    user_id = request.args.get('user_id')
    if request.method == 'POST':
        user_type = request.form['user_type']  # 'producer' or 'consumer'

        date_of_transaction = datetime.strptime(request.form['date'], "%Y-%m-%d")
        duration = int(request.form['duration'])
        amount_of_power = float(request.form['amount'])
        price = float(request.form['price'])
        time_slot = int(request.form['time_slot'])

        if user_type == 'producer':
            # Add user as a producer
            producer = Producer(user_id, date_of_transaction, duration, amount_of_power, price, time_slot)
            producers.append(producer)
            return redirect(url_for('dashboard', user_id=user_id))

        elif user_type == 'consumer':
            # Add user as a consumer and find best producer
            consumer = Consumer(user_id, date_of_transaction, duration, amount_of_power, price, time_slot)
            best_producer = find_best_producer(consumer)

            if best_producer:
                # Perform transaction and remove the producer
                producers.remove(best_producer)
                # Here you can handle the transaction logic

                return render_template('transaction_success.html', producer=best_producer, consumer=consumer)
            else:
                return render_template('no_producer_found.html', consumer=consumer)

    return render_template('marketplace.html', user_id=user_id)


@app.route('/battery/<int:user_id>', methods=['GET', 'POST'])
def battery(user_id):
    # Ensure the user_id exists
    user = next((user for user in users if user['id'] == user_id), None)
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    file_path = os.path.join('Battery_data', f'battery_schedule_{user_id}.xlsx')
    battery_data = None
    
   
    # Check if the file exists for backward compatibility
    if os.path.exists(file_path):
        battery_data = pd.read_excel(file_path)

    

    if request.method == 'POST':
       
        # Re-render the dashboard with the updated total loads
        return render_template('battery.html', user_id=user_id, battery_data=battery_data)
    
    # If no POST request, just render the dashboard with initial values
    return render_template('battery.html', user_id=user_id, battery_data=battery_data)

@app.route('/save_battery_data/<int:user_id>', methods=['POST'])
def save_battery_data(user_id, form_data=None):
    form_data = form_data or request.form
    
    switches_data = {"Charging":[]}
    capacity_data = []

    for hour in range(24):

        
        
        is_checked = form_data.get(f'{"Charging"}_{hour}')
        if is_checked:
            # total_consumption += load_values[load]
            switches_data["Charging"].append(1)
        else:
            switches_data["Charging"].append(0)
        
        cap = form_data.get(f'{"Capacity"}_{hour}')
        capacity_data.append(cap)



    # Create a DataFrame and save to an Excel file
    time_of_use = [f'{str(hour).zfill(2)}:00 - {str(hour+1).zfill(2)}:00' for hour in range(24)]
    df = pd.DataFrame(switches_data)
    df.insert(0, 'Time of Use in Hours', time_of_use)
    df.insert(2,'Capacity',capacity_data)
    # df.insert(6, 'Total', load_profile)

    # Save the Total Generation Excel file
    excel_path = os.path.join('Battery_data', f'battery_schedule_{user_id}.xlsx')
    df.to_excel(excel_path, index=False)
 
    
    return jsonify({'success': True})


@app.route('/grid/<int:user_id>', methods=['GET', 'POST'])
def grid(user_id):
    # Ensure the user_id exists
    user = next((user for user in users if user['id'] == user_id), None)
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    file_path = os.path.join('Grid_data', f'grid_schedule_{user_id}.xlsx')
    grid_data = None
    
   
    # Check if the file exists for backward compatibility
    if os.path.exists(file_path):
        grid_data = pd.read_excel(file_path)

    

    if request.method == 'POST':
       
        # Re-render the dashboard with the updated total loads
        return render_template('grid.html', user_id=user_id, grid_data=grid_data)
    
    # If no POST request, just render the dashboard with initial values
    return render_template('grid.html', user_id=user_id, grid_data=grid_data)

@app.route('/save_grid_data/<int:user_id>', methods=['POST'])
def save_grid_data(user_id, form_data=None):
    form_data = form_data or request.form
    
    
    capacity_data = []
    capacity_columns = {"Capacity": []}

    for hour in range(24):

        
        cap = form_data.get(f'{"Capacity"}_{hour}')
        capacity_data.append(cap)

    capacity_columns['Capacity'] = capacity_data

    # Create a DataFrame and save to an Excel file
    time_of_use = [f'{str(hour).zfill(2)}:00 - {str(hour+1).zfill(2)}:00' for hour in range(24)]
    df = pd.DataFrame(capacity_columns)
    df.insert(0, 'Time of Use in Hours', time_of_use)
    # df.insert(2,'Capacity',capacity_data)
    # df.insert(6, 'Total', load_profile)

    # Save the Total Generation Excel file
    excel_path = os.path.join('Grid_data', f'grid_schedule_{user_id}.xlsx')
    df.to_excel(excel_path, index=False)
 
    
    return jsonify({'success': True})

@app.route('/load/<int:user_id>', methods=['GET', 'POST'])
def load(user_id):
    # Ensure the user_id exists
    user = next((user for user in users if user['id'] == user_id), None)
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('login'))

    file_path = os.path.join('Load_data', f'load_profile_{user_id}.xlsx')
    load_data = None
    total_loads = [0] * 24  # Initialize total loads for each hour

    # Check if the file exists for backward compatibility
    if os.path.exists(file_path):
        load_data = pd.read_excel(file_path)

    if request.method == 'POST':
        # Calculate total loads based on form submission
        total_loads = save_load_data(user_id, request.form)
        # Re-render the dashboard with the updated total loads
        return render_template('load.html', user_id=user_id, load_data=load_data, total_loads=total_loads)
    
    # If no POST request, just render the dashboard with initial values
    return render_template('load.html', user_id=user_id, load_data=load_data, total_loads=total_loads)

@app.route('/save_load_data/<int:user_id>', methods=['POST'])
def save_load_data(user_id, form_data=None):
    form_data = form_data or request.form
    load_profile = []
    switches_data = {load: [] for load in ['A', 'B', 'C', 'D', 'Misc']}
    
    for hour in range(24):
        total_consumption = 0
        for load in ['A', 'B', 'C', 'D', 'Misc']:
            is_checked = form_data.get(f'{load}_{hour}')
            if is_checked:
                total_consumption += load_values[load]
                switches_data[load].append(load_values[load])
            else:
                switches_data[load].append(0)
        load_profile.append(total_consumption)

    # Create a DataFrame and save to an Excel file
    time_of_use = [f'{str(hour).zfill(2)}:00 - {str(hour+1).zfill(2)}:00' for hour in range(24)]
    df = pd.DataFrame(switches_data)
    df.insert(0, 'Time of Use in Hours', time_of_use)
    df.insert(6, 'Total', load_profile)

    # Save the Total Generation Excel file
    excel_path = os.path.join('Load_data', f'load_profile_{user_id}.xlsx')
    df.to_excel(excel_path, index=False)

    # Save the switches state Excel file for backward compatibility
    # switches_df = pd.DataFrame(switches_data)
    # switches_df.insert(0, 'Time of Use in Hours', time_of_use)
    # switches_file_path = os.path.join('Load_data', f'switches_{user_id}.xlsx')
    # switches_df.to_excel(switches_file_path, index=False)

    # Return the total loads as a JSON response
    return jsonify({'success': True, 'total_loads': load_profile})

# @app.route('/motion_detected', methods=['POST'])
# def motion_detected():
 
#     try:
        
        
#         data = request.get_json()
#         if data is None:
#             return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
#         motion_status = data.get('motion', False)
#         timestamp = data.get('time', 0)
        
        
#         print(f"Motion detected: {motion_status}, Time: {timestamp}")

#         # You can add additional logic here, such as saving the data to a database or triggering another process
        
       
#         # Return a success response
#         return jsonify({"status": "success", "message":f"{motion_status} {timestamp}"}), 200
#     except Exception as e:
#         print(f"Error processing request: {e}")
#         return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    if not os.path.exists('Battery_data'):
        os.makedirs('Battery_data')
    if not os.path.exists('Grid_data'):
        os.makedirs('Grid_data')
    if not os.path.exists('Load_data'):
        os.makedirs('Load_data')
    # app.run(debug=True,host='0.0.0.0')
    app.run(debug=True)
